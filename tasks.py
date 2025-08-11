import asyncio

from loguru import logger

from lnbits.core.models import Payment
from lnbits.core.services import websocket_updater
from lnbits.tasks import register_invoice_listener
# from lnbits.core.services.notifications import send_notification
from lnbits.core.services import pay_invoice
from .crud import get_order, update_order, get_product, get_settings
from .models import Order


async def wait_for_paid_invoices():
    invoice_queue = asyncio.Queue()
    register_invoice_listener(invoice_queue, "ext_sellcoins")
    while True:
        payment = await invoice_queue.get()
        await on_invoice_paid(payment)


async def on_invoice_paid(payment: Payment) -> None:
    if payment.extra.get("tag") != "SellCoins":
        return
    logger.debug(payment)

    # Toggle through and get all the details we need
    order_id = payment.extra.get("order_id")
    assert order_id, "order_id not set in invoice"
    order = await get_order(order_id)
    assert order, "Order ID not set in invoice"
    product = await get_product(order.product_id)
    assert product, "Product not found"
    sellcoins_settings = await get_settings(product.settings_id)
    assert sellcoins_settings, "Settings not found"
    if order.status == "claimed" or order.status == "paid":
        await websocket_updater(order_id, "claimed")
        logger.warning(f"Order {order.id} already claimed, skipping")
        return
    # Update the order as paid so if worse comes to worse, we can still see it and settle with the user
    order.status = "paid"
    await update_order(Order(**order.dict()))

    # Use WS to update the frontend
    await websocket_updater(order_id, "paid")

    # Send the notification
    # encoded_lnurl = url_encode(f"http://{settings.host}:{settings.port}/sellcoins/api/v1/lnurl/{order.id}")
    # if settings.notification:
    #    try:
    #        message = sellcoins_settings.message + "\n\n" + f"<a href='lightning://{encoded_lnurl}'><img src='http://{settings.host}:{settings.port}/api/v1/qrcode/{encoded_lnurl}'></a>"
    #        await send_notification(
    #            nostr_identifiers = [order.email_to] if product.email else None,
    #            email_addresses = [order.nostr_key] if product.nostr else None,
    #            message = message,
    #        )
    #    except Exception as e:
    #        assert f"Error sending email: {e}"

