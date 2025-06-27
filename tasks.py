import asyncio

from lnbits.core.models import Payment
from lnbits.core.services import websocket_updater
from lnbits.tasks import register_invoice_listener

from .crud import get_order, update_order
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

    order_id = payment.extra.get("order_id")
    assert order_id, "Order ID not set in invoice"
    order = await get_order(order_id)
    assert order, "Order does not exist"

    order.status = "paid"
    await update_order(Order(**order.dict()))

    await websocket_updater(order_id, "paid")
