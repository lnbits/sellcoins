from http import HTTPStatus
from typing import Optional

import shortuuid
from fastapi import APIRouter, Request
from lnbits.core.services import pay_invoice

from .crud import get_order, get_product, get_settings

sellcoins_lnurl_router = APIRouter()


@sellcoins_lnurl_router.get(
    "/api/v1/lnurl/{order_id}",
    status_code=HTTPStatus.OK,
    name="sellcoins.api_lnurl_withdraw",
)
async def api_lnurl_withdraw(
    request: Request,
    order_id: str,
):
    order = await get_order(order_id)
    if not order:
        return {"status": "ERROR", "reason": "No sellcoins found"}
    product = await get_product(order.product_id)
    k1 = shortuuid.uuid(name=order_id)
    return {
        "tag": "withdrawRequest",
        "callback": str(
            request.url_for("sellcoins.api_lnurl_callback", order_id=order_id)
        ),
        "k1": k1,
        "defaultDescription": f"{product.name} (order: {order.id})",
        "maxWithdrawable": product.amount * 1000,
        "minWithdrawable": product.amount * 1000,
    }


@sellcoins_lnurl_router.get(
    "/api/v1/lnurl/callback/{order_id}",
    status_code=HTTPStatus.OK,
    name="sellcoins.api_lnurl_callback",
)
async def api_lnurl_withdraw_cb(
    order_id: str,
    pr: Optional[str] = None,
    k1: Optional[str] = None,
):
    # Do all the checks
    assert k1, "k1 is required"
    assert pr, "pr is required"
    order = await get_order(order_id)
    if not order:
        return {"status": "ERROR", "reason": "No sellcoins found"}
    product = await get_product(order_id)
    if not product:
        return {"status": "ERROR", "reason": "No sellcoins found, could not find product"}
    sellcoins_settings = await get_settings(product.settings_id)
    if not sellcoins_settings:
        return {"status": "ERROR", "reason": "No sellcoins found, could not find settings"}

    # Check the k1
    k1_check = shortuuid.uuid(name=order_id)
    if k1_check != k1:
        return {"status": "ERROR", "reason": "Wrong k1 check provided"}

    # Set as claimed and try to pay
    order.status = "claimed"
    await update_order(Order(**order.dict()))
    try:
        await pay_invoice(
            wallet_id=sellcoins.wallet,
            payment_request=pr,
            max_sat=product.amount * 1000,
            extra={
                "tag": f"SellCoins - {order_id}"
            },
        )
        return {"status": "OK"}
    except Exception as e:
        # If payment fails, revert the order status
        order.status = "paid"
        await update_order(Order(**order.dict()))
        return {"status": "ERROR", "reason": f"Error paying invoice: {e}"}
