# Description: Extensions that use LNURL usually have a few endpoints in views_lnurl.py.

from http import HTTPStatus
from typing import Optional

import shortuuid
from fastapi import APIRouter, Request
from lnbits.core.services import pay_invoice

from .crud import get_order

sellcoins_lnurl_router = APIRouter()


@sellcoins_lnurl_router.get(
    "/api/v1/lnurl/withdraw/{order_id}",
    status_code=HTTPStatus.OK,
    name="sellcoins.api_lnurl_withdraw",
)
async def api_lnurl_withdraw(
    request: Request,
    order_id: str,
):
    sellcoins = await get_order(order_id)
    if not sellcoins:
        return {"status": "ERROR", "reason": "No sellcoins found"}
    k1 = shortuuid.uuid(name=sellcoins.id)
    return {
        "tag": "withdrawRequest",
        "callback": str(
            request.url_for("sellcoins.api_lnurl_withdraw_callback", order_id=order_id)
        ),
        "k1": k1,
        "defaultDescription": sellcoins.name,
        "maxWithdrawable": sellcoins.lnurlwithdrawamount * 1000,
        "minWithdrawable": sellcoins.lnurlwithdrawamount * 1000,
    }


@sellcoins_lnurl_router.get(
    "/api/v1/lnurl/withdrawcb/{order_id}",
    status_code=HTTPStatus.OK,
    name="sellcoins.api_lnurl_withdraw_callback",
)
async def api_lnurl_withdraw_cb(
    order_id: str,
    pr: Optional[str] = None,
    k1: Optional[str] = None,
):
    assert k1, "k1 is required"
    assert pr, "pr is required"
    sellcoins = await get_order(order_id)
    if not sellcoins:
        return {"status": "ERROR", "reason": "No sellcoins found"}

    k1_check = shortuuid.uuid(name=sellcoins.id)
    if k1_check != k1:
        return {"status": "ERROR", "reason": "Wrong k1 check provided"}

    await pay_invoice(
        wallet_id=sellcoins.wallet,
        payment_request=pr,
        max_sat=int(sellcoins.lnurlwithdrawamount * 1000),
        extra={
            "tag": "SellCoins",
            "sellcoinsId": order_id,
            "lnurlwithdraw": True,
        },
    )
    return {"status": "OK"}
