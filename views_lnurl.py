from http import HTTPStatus
from secrets import compare_digest
from typing import Optional

from bolt11 import decode as bolt11_decode
from fastapi import APIRouter, Request
from lnbits.core.services import pay_invoice
from lnbits.core.services.websockets import websocket_updater
from lnbits.exceptions import PaymentError
from lnbits.settings import settings as lnbits_settings
from lnbits.utils.exchange_rates import get_fiat_rate_and_price_satoshis
from loguru import logger

from .crud import (
    claim_order,
    get_order,
    get_product,
    get_settings,
    prepare_order_withdrawal,
    set_order_status,
)
from .helpers import get_pr

sellcoins_lnurl_router = APIRouter()


@sellcoins_lnurl_router.get(
    "/api/v1/lnurl/{order_id}",
    status_code=HTTPStatus.OK,
    name="sellcoins.api_lnurl_withdraw",
    openapi_extra={"x-lnbits-local-lnurl": True},
)
async def api_lnurl_withdraw(
    request: Request,
    order_id: str,
):
    order = await get_order(order_id)
    if not order:
        return {"status": "ERROR", "reason": "No sellcoins found"}
    if order.status != "paid":
        return {"status": "ERROR", "reason": "Order claimed or not paid for"}
    product = await get_product(order.product_id)
    if not product:
        return {"status": "ERROR", "reason": "No product found"}
    sellcoins_settings = await get_settings(product.settings_id)
    if not sellcoins_settings:
        return {"status": "ERROR", "reason": "No settings found"}
    if (
        product.amount is None
        or sellcoins_settings.haircut is None
        or not sellcoins_settings.denomination
    ):
        return {
            "status": "ERROR",
            "reason": "Product or payment settings are incomplete",
        }
    if order.k1:
        sats_amount = order.sats_amount
    else:
        sats_amount = await _calculate_sats_amount(
            product.amount,
            sellcoins_settings.denomination,
            sellcoins_settings.haircut,
            sellcoins_settings.auto_convert,
        )
    if sats_amount is None or sats_amount <= 0:
        return {"status": "ERROR", "reason": "Order amount must be positive"}
    order = await prepare_order_withdrawal(order_id, sats_amount)
    if not order or order.status != "paid" or not order.k1:
        return {"status": "ERROR", "reason": "Order is no longer available"}
    sats_amount = order.sats_amount
    if sats_amount is None or sats_amount <= 0:
        return {"status": "ERROR", "reason": "Order amount must be positive"}
    return {
        "tag": "withdrawRequest",
        "callback": str(
            request.url_for("sellcoins.api_lnurl_callback", order_id=order_id)
        ),
        "k1": order.k1,
        "defaultDescription": f"{product.title} (order: {order.id})",
        "maxWithdrawable": sats_amount * 1000,
        "minWithdrawable": sats_amount * 1000,
    }


@sellcoins_lnurl_router.get(
    "/api/v1/lnurl/callback/{order_id}",
    status_code=HTTPStatus.OK,
    name="sellcoins.api_lnurl_callback",
    openapi_extra={"x-lnbits-local-lnurl": True},
)
async def api_lnurl_withdraw_cb(
    order_id: str,
    pr: Optional[str] = None,
    k1: Optional[str] = None,
):
    # Do all the checks
    if not k1 or not pr:
        return {"status": "ERROR", "reason": "Invoice and k1 are required"}
    order = await get_order(order_id)
    if not order:
        return {"status": "ERROR", "reason": "No sellcoins found"}

    # Check the order status
    if order.status != "paid":
        return {"status": "ERROR", "reason": "Order claimed or not paid for"}

    product = await get_product(order.product_id)
    if not product:
        return {
            "status": "ERROR",
            "reason": "No sellcoins found, could not find product",
        }
    sellcoins_settings = await get_settings(product.settings_id)
    if not sellcoins_settings:
        return {
            "status": "ERROR",
            "reason": "No sellcoins found, could not find settings",
        }

    if (
        order.sats_amount is None
        or order.sats_amount <= 0
        or not sellcoins_settings.send_wallet_id
    ):
        return {
            "status": "ERROR",
            "reason": "Product or payment settings are incomplete",
        }

    # Check the k1
    if not order.k1 or not compare_digest(order.k1.encode(), k1.encode()):
        return {"status": "ERROR", "reason": "Wrong k1 check provided"}

    if not _invoice_matches_order(pr, order.sats_amount):
        return {"status": "ERROR", "reason": "Invoice amount does not match order"}
    if not await claim_order(
        order_id, k1, order.sats_amount
    ) or not await _pay_order_invoice(
        order_id, sellcoins_settings.send_wallet_id, pr, order.sats_amount
    ):
        return {"status": "ERROR", "reason": "Unable to pay invoice"}

    await _complete_order(
        order_id,
        sellcoins_settings.send_wallet_id,
        order.sats_amount,
        sellcoins_settings.live_mode,
    )
    return {"status": "OK"}


async def pay_tribute(tribute: int, wallet_id: str) -> None:
    try:
        pr = await get_pr("lnbits@nostr.com", tribute)
        if not pr:
            return
        await pay_invoice(
            wallet_id=wallet_id,
            payment_request=pr,
            max_sat=tribute,
            description="Tribute to help support LNbits",
        )
    except Exception as exc:
        logger.warning(exc)


async def _calculate_sats_amount(
    amount: int, denomination: str, haircut: int, auto_convert: bool | None
) -> int:
    if auto_convert:
        exchange_rate, _ = await get_fiat_rate_and_price_satoshis(denomination)
        return int(exchange_rate * amount - (exchange_rate * amount / 100 * haircut))
    # fake wallet hack
    return amount if lnbits_settings.lnbits_denomination == "sats" else amount * 100


def _invoice_matches_order(pr: str, sats_amount: int) -> bool:
    try:
        invoice = bolt11_decode(pr)
    except Exception:
        return False
    return invoice.amount_msat == sats_amount * 1000


async def _pay_order_invoice(
    order_id: str, wallet_id: str, pr: str, sats_amount: int
) -> bool:
    try:
        await pay_invoice(
            wallet_id=wallet_id,
            payment_request=pr,
            max_sat=sats_amount,
            extra={"tag": f"SellCoins - {order_id}"},
        )
    except PaymentError as exc:
        # Only a definite failure permits another withdrawal attempt.
        if exc.status == "failed":
            await set_order_status(order_id, "paid", "claimed")
        return False
    except Exception:
        logger.warning("Could not confirm order payment outcome")
        return False
    return True


async def _complete_order(
    order_id: str, wallet_id: str, sats_amount: int, live_mode: bool | None
) -> None:
    try:
        await websocket_updater(order_id, order_id)
    except Exception:
        logger.warning("Could not notify client of completed order")

    # Tribute to the developers.
    # Removing this will break the license for this extension.
    # But more importantly it would just be mean,
    # these small tributes help keep developement going.
    if live_mode:
        try:
            tribute = int(sats_amount * 0.5 // 100)  # 0.5% tribute
            await pay_tribute(tribute, wallet_id)
        except Exception:
            logger.warning("Error paying tribute")
