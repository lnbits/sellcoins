from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import shortuuid
from lnbits.core.models import Payment, PaymentState

from .. import tasks, views_lnurl
from ..models import Order, Product, Settings


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def order_payment(monkeypatch):
    order = Order(
        id="order-id",
        product_id="product-id",
        settings_id="seller-id",
        status="unpaid",
        payment_hash="invoice-checking-id",
        k1="11" * 32,
    )
    product = Product(id=order.product_id, settings_id=order.settings_id, amount=100000)
    settings = Settings(
        id=order.settings_id,
        receive_wallet_id="seller-receive-wallet",
        send_wallet_id="seller-send-wallet",
        live_mode=False,
    )
    payment = Payment(
        checking_id=order.payment_hash,
        payment_hash="00" * 32,
        wallet_id=settings.receive_wallet_id,
        amount=100000000,
        fee=0,
        bolt11="invoice",
        status=PaymentState.SUCCESS,
        extra={"tag": "SellCoins", "order_id": order.id},
    )

    async def transition(order_id, status, expected_status):
        if order.status != expected_status:
            return False
        order.status = status
        return True

    async def claim(order_id, k1, sats_amount):
        return await transition(order_id, "claimed", "paid")

    set_order_status = AsyncMock(side_effect=transition)
    monkeypatch.setattr(tasks, "set_order_status", set_order_status)
    monkeypatch.setattr(views_lnurl, "claim_order", AsyncMock(side_effect=claim))
    websocket_updater = AsyncMock()
    for module in (tasks, views_lnurl):
        monkeypatch.setattr(module, "get_order", AsyncMock(return_value=order))
        monkeypatch.setattr(module, "get_product", AsyncMock(return_value=product))
        monkeypatch.setattr(module, "get_settings", AsyncMock(return_value=settings))
        monkeypatch.setattr(module, "websocket_updater", websocket_updater)
    return SimpleNamespace(
        order=order,
        payment=payment,
        set_order_status=set_order_status,
        websocket_updater=websocket_updater,
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "overrides",
    [
        {"checking_id": "unrelated-invoice"},
        {"wallet_id": "attacker-wallet"},
        {
            "checking_id": "attacker-invoice",
            "wallet_id": "attacker-wallet",
            "amount": 1000,
        },
        {"status": PaymentState.PENDING},
        {"status": PaymentState.FAILED},
        {"amount": -100000000},
    ],
    ids=[
        "wrong-invoice",
        "wrong-wallet",
        "forged-self-payment",
        "pending",
        "failed",
        "outgoing",
    ],
)
async def test_unrelated_or_unsettled_payment_does_not_pay_order(
    order_payment, overrides
):
    payment = order_payment.payment.model_copy(update=overrides)

    await tasks.on_invoice_paid(payment)

    assert order_payment.order.status == "unpaid"
    order_payment.set_order_status.assert_not_awaited()
    order_payment.websocket_updater.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "checking_id", ["invoice-checking-id", "fiat_stripe_session-id"]
)
async def test_original_payment_marks_order_paid(order_payment, checking_id):
    order_payment.order.payment_hash = checking_id
    order_payment.payment.checking_id = checking_id

    await tasks.on_invoice_paid(order_payment.payment)

    assert order_payment.order.status == "paid"
    order_payment.set_order_status.assert_awaited_once()
    order_payment.websocket_updater.assert_awaited_once_with("order-id", "paid")


@pytest.mark.anyio
@pytest.mark.parametrize("status", ["paid", "claimed"])
async def test_settled_order_is_not_updated_again(order_payment, status):
    order_payment.order.status = status

    await tasks.on_invoice_paid(order_payment.payment)

    assert order_payment.order.status == status
    order_payment.set_order_status.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("status", ["unpaid", "claimed", ""])
async def test_withdraw_requires_paid_order(order_payment, monkeypatch, status):
    order_payment.order.status = status
    order_payment.order.sats_amount = 100000
    pay_invoice = AsyncMock()
    monkeypatch.setattr(views_lnurl, "pay_invoice", pay_invoice)

    result = await views_lnurl.api_lnurl_withdraw_cb(
        "order-id", pr="invoice", k1=shortuuid.uuid(name="order-id")
    )

    assert result["status"] == "ERROR"
    assert order_payment.order.status == status
    order_payment.set_order_status.assert_not_awaited()
    pay_invoice.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("sats_amount", [None, 0, -1])
async def test_withdraw_requires_positive_amount(
    order_payment, monkeypatch, sats_amount
):
    order_payment.order.status = "paid"
    order_payment.order.sats_amount = sats_amount
    pay_invoice = AsyncMock()
    monkeypatch.setattr(views_lnurl, "pay_invoice", pay_invoice)

    result = await views_lnurl.api_lnurl_withdraw_cb(
        "order-id", pr="invoice", k1=shortuuid.uuid(name="order-id")
    )

    assert result["status"] == "ERROR"
    assert order_payment.order.status == "paid"
    order_payment.set_order_status.assert_not_awaited()
    pay_invoice.assert_not_awaited()


@pytest.mark.anyio
async def test_paid_order_withdrawal_uses_satoshi_limit(order_payment, monkeypatch):
    order_payment.order.status = "paid"
    order_payment.order.sats_amount = 100000
    pay_invoice = AsyncMock()
    monkeypatch.setattr(views_lnurl, "pay_invoice", pay_invoice)

    monkeypatch.setattr(
        views_lnurl,
        "bolt11_decode",
        lambda _: SimpleNamespace(amount_msat=100000000),
    )
    result = await views_lnurl.api_lnurl_withdraw_cb(
        "order-id", pr="invoice", k1=order_payment.order.k1
    )

    assert result == {"status": "OK"}
    assert order_payment.order.status == "claimed"
    pay_invoice.assert_awaited_once_with(
        wallet_id="seller-send-wallet",
        payment_request="invoice",
        max_sat=100000,
        extra={"tag": "SellCoins - order-id"},
    )
