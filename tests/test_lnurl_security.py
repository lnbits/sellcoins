import json
from ipaddress import ip_address
from unittest.mock import AsyncMock

import pytest
from bolt11 import Bolt11, Tag, TagChar, Tags, encode
from lnbits.core.services import lnurl as core_lnurl
from lnbits.settings import settings

from .. import helpers, views_lnurl


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def lnurl_transport(monkeypatch):
    monkeypatch.setattr(settings, "lnbits_lnurl_allow_private_ips", False)
    monkeypatch.setattr(settings, "lnbits_baseurl", "https://instance.example")
    monkeypatch.setattr(settings, "lnbits_lnurl_redirect_url_rules", [r"https://.*"])
    resolve = AsyncMock(return_value=[ip_address("93.184.216.34")])
    send = AsyncMock()
    monkeypatch.setattr(core_lnurl, "_resolve_lnurl_host", resolve)
    monkeypatch.setattr(core_lnurl, "_send_lnurl_request", send)
    pay = AsyncMock()
    monkeypatch.setattr(views_lnurl, "pay_invoice", pay)
    return resolve, send, pay


@pytest.mark.anyio
@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1"])
async def test_private_metadata_never_connects(lnurl_transport, address):
    resolve, send, pay = lnurl_transport
    resolve.return_value = [ip_address(address)]
    await views_lnurl.pay_tribute(21, "wallet")
    send.assert_not_awaited()
    pay.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("redirect", [False, True])
async def test_private_callback_never_connects_or_pays(lnurl_transport, redirect):
    resolve, send, pay = lnurl_transport
    public = [ip_address("93.184.216.34")]
    private = [ip_address("127.0.0.1")]
    resolve.side_effect = [public, public, private] if redirect else [public, private]
    send.side_effect = [_metadata()]
    if redirect:
        send.side_effect = [
            _metadata(),
            (302, {"location": "https://internal.example/invoice"}, b""),
        ]
    await views_lnurl.pay_tribute(21, "wallet")
    assert send.await_count == (2 if redirect else 1)
    pay.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("invoice_amount", [21000, 22000])
async def test_public_lnurl_checks_amount_and_preserves_callback_query(
    lnurl_transport, invoice_amount
):
    _, send, _ = lnurl_transport
    invoice = _invoice(invoice_amount)
    send.side_effect = [_metadata(), (200, {}, json.dumps({"pr": invoice}).encode())]
    result = await helpers.get_pr("alice@pay.example", 21)
    assert result == (invoice if invoice_amount == 21000 else None)
    assert send.await_count == 2
    callback = send.await_args.args[0]
    assert callback.params["amount"] == "21000"
    assert callback.params["token"] == "preserved"


def _metadata():
    return (
        200,
        {},
        json.dumps(
            {
                "tag": "payRequest",
                "callback": "https://callback.example/invoice?token=preserved",
                "minSendable": 1000,
                "maxSendable": 100000,
                "metadata": '[["text/plain","Test payment"]]',
            }
        ).encode(),
    )


def _invoice(amount):
    return encode(
        Bolt11(
            currency="bc",
            date=1700000000,
            amount_msat=amount,
            tags=Tags(
                [
                    Tag(TagChar.payment_hash, "00" * 32),
                    Tag(TagChar.payment_secret, "11" * 32),
                    Tag(TagChar.description, "Test payment"),
                ]
            ),
        ),
        private_key="22" * 32,
    )
