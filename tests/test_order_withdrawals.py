import asyncio
from secrets import token_hex
from time import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
import shortuuid
from bolt11 import Bolt11, Tag, TagChar, Tags, encode
from fastapi import Request
from lnbits.db import Database
from lnbits.exceptions import PaymentError
from lnbits.settings import settings as core_settings

from .. import crud, migrations, views_lnurl
from ..models import Order, Product, Settings


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def shop(monkeypatch, tmp_path):
    monkeypatch.setattr(core_settings, "lnbits_data_folder", str(tmp_path))
    monkeypatch.setattr(core_settings, "lnbits_denomination", "sats")
    db = Database("ext_sellcoins")
    monkeypatch.setattr(crud, "db", db)
    for name, migration in vars(migrations).items():
        if name.startswith("m00"):
            await migration(db)
    shop_settings = await crud.create_settings(
        Settings(
            id="seller",
            denomination="sat",
            send_wallet_id="send-wallet",
            receive_wallet_id="receive-wallet",
            haircut=0,
            auto_convert=False,
            live_mode=False,
        )
    )
    product = await crud.create_product(
        Product(settings_id=shop_settings.id, title="Coins", amount=1000)
    )
    order = await crud.create_order(
        Order(product_id=product.id, settings_id=shop_settings.id, status="paid")
    )
    pay = AsyncMock()
    notify = AsyncMock()
    monkeypatch.setattr(views_lnurl, "pay_invoice", pay)
    monkeypatch.setattr(views_lnurl, "websocket_updater", notify)
    yield SimpleNamespace(order=order, product=product, db=db, pay=pay, notify=notify)
    await db.engine.dispose()


@pytest.mark.anyio
async def test_existing_order_migration(monkeypatch, tmp_path):
    monkeypatch.setattr(core_settings, "lnbits_data_folder", str(tmp_path))
    db = Database("ext_sellcoins")
    monkeypatch.setattr(crud, "db", db)
    try:
        for name, migration in vars(migrations).items():
            if name.startswith("m00") and not name.startswith("m007"):
                await migration(db)
        await db.execute(
            """
            INSERT INTO sellcoins.orders
                (id, product_id, settings_id, status, sats_amount)
            VALUES ('existing', 'product', 'seller', 'paid', 1000)
            """
        )
        await migrations.m007_add_order_k1(db)
        order = await crud.get_order("existing")
        assert order and order.status == "paid" and order.k1 is None
        prepared = await crud.prepare_order_withdrawal("existing", 1000)
        assert prepared and prepared.k1 and len(bytes.fromhex(prepared.k1)) == 32
        assert prepared.status == "paid" and prepared.sats_amount == 1000
    finally:
        await db.engine.dispose()


@pytest.mark.anyio
async def test_withdrawal_details_stay_stable(shop):
    first = await views_lnurl.api_lnurl_withdraw(_request(), shop.order.id)
    shop.product.amount = 2000
    await shop.db.update("sellcoins.products", shop.product)
    second = await views_lnurl.api_lnurl_withdraw(_request(), shop.order.id)

    assert first == second
    assert first["maxWithdrawable"] == first["minWithdrawable"] == 1000000
    assert len(bytes.fromhex(first["k1"])) == 32
    assert first["k1"] != shortuuid.uuid(name=shop.order.id)


@pytest.mark.anyio
async def test_preparing_and_paying_another_order_cannot_reopen_claim(shop):
    prepared = await crud.prepare_order_withdrawal(shop.order.id, 1000)
    assert prepared and prepared.k1 and prepared.id
    results = await asyncio.gather(
        crud.claim_order(prepared.id, prepared.k1, 1000),
        crud.claim_order(prepared.id, prepared.k1, 1000),
    )
    assert sum(results) == 1
    refreshed = await crud.prepare_order_withdrawal(prepared.id, 2000)
    assert refreshed and refreshed.status == "claimed"
    assert refreshed.sats_amount == 1000 and refreshed.k1 == prepared.k1
    assert not await crud.set_order_status(prepared.id, "paid", "unpaid")


@pytest.mark.anyio
@pytest.mark.parametrize("amount_msat", [None, 999999, 1000001, 2000000])
async def test_callback_requires_exact_invoice_amount(shop, amount_msat):
    details = await views_lnurl.api_lnurl_withdraw(_request(), shop.order.id)
    result = await views_lnurl.api_lnurl_withdraw_cb(
        shop.order.id, pr=_invoice(amount_msat), k1=details["k1"]
    )

    assert result["status"] == "ERROR"
    order = await crud.get_order(shop.order.id)
    assert order and order.status == "paid"
    shop.pay.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("invoice", [None, "", "invalid-invoice"])
async def test_callback_requires_valid_invoice(shop, invoice):
    details = await views_lnurl.api_lnurl_withdraw(_request(), shop.order.id)
    result = await views_lnurl.api_lnurl_withdraw_cb(
        shop.order.id, pr=invoice, k1=details["k1"]
    )

    assert result["status"] == "ERROR"
    order = await crud.get_order(shop.order.id)
    assert order and order.status == "paid"
    shop.pay.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("challenge", [None, "", "wrong", "非ASCII", "derived"])
async def test_callback_requires_stored_challenge(shop, challenge):
    await views_lnurl.api_lnurl_withdraw(_request(), shop.order.id)
    if challenge == "derived":
        challenge = shortuuid.uuid(name=shop.order.id)
    result = await views_lnurl.api_lnurl_withdraw_cb(
        shop.order.id, pr=_invoice(1000000), k1=challenge
    )

    assert result["status"] == "ERROR"
    order = await crud.get_order(shop.order.id)
    assert order and order.status == "paid"
    shop.pay.assert_not_awaited()


@pytest.mark.anyio
async def test_concurrent_callbacks_pay_once(shop, monkeypatch):
    details = await views_lnurl.api_lnurl_withdraw(_request(), shop.order.id)
    ready = asyncio.Event()
    reads = 0

    async def read_paid_order(order_id):
        nonlocal reads
        order = await crud.get_order(order_id)
        reads += 1
        if reads == 2:
            ready.set()
        await ready.wait()
        return order

    monkeypatch.setattr(views_lnurl, "get_order", read_paid_order)
    invoices = [_invoice(1000000), _invoice(1000000)]
    results = await asyncio.wait_for(
        asyncio.gather(
            *[
                views_lnurl.api_lnurl_withdraw_cb(
                    shop.order.id, pr=invoice, k1=details["k1"]
                )
                for invoice in invoices
            ]
        ),
        timeout=5,
    )

    assert sorted(result["status"] for result in results) == ["ERROR", "OK"]
    shop.pay.assert_awaited_once()
    assert shop.pay.await_args.kwargs["max_sat"] == 1000
    order = await crud.get_order(shop.order.id)
    assert order and order.status == "claimed"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "error, expected_status",
    [
        (PaymentError("declined", status="failed"), "paid"),
        (PaymentError("pending", status="pending"), "claimed"),
        (PaymentError("settled", status="success"), "claimed"),
        (RuntimeError("unknown outcome"), "claimed"),
    ],
)
async def test_payment_outcome_controls_retry(shop, error, expected_status):
    details = await views_lnurl.api_lnurl_withdraw(_request(), shop.order.id)
    shop.pay.side_effect = error
    result = await views_lnurl.api_lnurl_withdraw_cb(
        shop.order.id, pr=_invoice(1000000), k1=details["k1"]
    )

    assert result == {"status": "ERROR", "reason": "Unable to pay invoice"}
    order = await crud.get_order(shop.order.id)
    assert order and order.status == expected_status
    shop.notify.assert_not_awaited()


@pytest.mark.anyio
async def test_notification_failure_keeps_completed_order_claimed(shop):
    details = await views_lnurl.api_lnurl_withdraw(_request(), shop.order.id)
    shop.notify.side_effect = RuntimeError("notification unavailable")

    result = await views_lnurl.api_lnurl_withdraw_cb(
        shop.order.id, pr=_invoice(1000000), k1=details["k1"]
    )
    repeated = await views_lnurl.api_lnurl_withdraw_cb(
        shop.order.id, pr=_invoice(1000000), k1=details["k1"]
    )

    assert result == {"status": "OK"}
    assert repeated["status"] == "ERROR"
    order = await crud.get_order(shop.order.id)
    assert order and order.status == "claimed"
    shop.pay.assert_awaited_once()


@pytest.mark.anyio
async def test_concurrent_preparation_keeps_one_challenge(shop):
    first, second = await asyncio.gather(
        crud.prepare_order_withdrawal(shop.order.id, 1000),
        crud.prepare_order_withdrawal(shop.order.id, 2000),
    )
    assert first and second and first.k1 == second.k1
    assert first.sats_amount == second.sats_amount


@pytest.mark.anyio
@pytest.mark.parametrize("status", ["unpaid", "claimed", ""])
async def test_unavailable_order_cannot_prepare_withdrawal(shop, status):
    await crud.set_order_status(shop.order.id, status, "paid")
    result = await views_lnurl.api_lnurl_withdraw(_request(), shop.order.id)

    assert result["status"] == "ERROR"
    order = await crud.get_order(shop.order.id)
    assert order and order.k1 is None


def _request():
    request = Mock(spec=Request)
    request.url_for.return_value = "https://shop.example/callback"
    return request


def _invoice(amount_msat):
    return encode(
        Bolt11(
            currency="bc",
            date=int(time()),
            amount_msat=amount_msat,
            tags=Tags(
                [
                    Tag(TagChar.payment_hash, token_hex(32)),
                    Tag(TagChar.payment_secret, token_hex(32)),
                    Tag(TagChar.description, "Order withdrawal"),
                ]
            ),
        ),
        private_key="22" * 32,
    )
