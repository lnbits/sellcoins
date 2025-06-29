import asyncio

from lnbits.core.models import Payment
from lnbits.core.services import websocket_updater
from lnbits.tasks import register_invoice_listener
from lnbits.core.services.notifications import send_email
from lnbits.core.services import pay_invoice
from .crud import get_order, update_order, get_product, get_settings
from .models import Order
from .helpers import get_pr
from lnbits.settings import settings
from lnbits.lnurl import encode as lnurl_encode

async def wait_for_paid_invoices():
    invoice_queue = asyncio.Queue()
    register_invoice_listener(invoice_queue, "ext_sellcoins")
    while True:
        payment = await invoice_queue.get()
        await on_invoice_paid(payment)


async def on_invoice_paid(payment: Payment) -> None:
    if payment.extra.get("tag") != "SellCoins":
        return
    
    # Toggle through and get all the details we need
    checking_id = payment.extra.get("checking_id")
    assert checking_id, "Checking ID not set in invoice"
    order = await get_order(checking_id)
    assert order, "Order ID not set in invoice"
    product = await get_product(order.product_id)
    assert product, "Product not found"
    sellcoins_settings = await get_settings(product.settings_id)
    assert sellcoins_settings, "Settings not found"

    # Update the order as paid so if worse comes to worse, we can still see it and settle with the user
    order.status = "paid"
    await update_order(Order(**order.dict()))
    
    # Use WS to update the frontend
    await websocket_updater(order.id, "paid")
    
    # Pay the LNbits Inc tribute, if you remove this you remove part of your soul
    tribute = product.amount * 0.5 // 100  # 0.5% tribute
    await pay_tribute(tribute, sellcoins_settings.wallet_id)

    # If theres an email to send, send it
    # Create the lnurl
    lnurl = lnurl_encode(f"http://{settings.host}:{settings.port}/sellcoins/api/v1/lnurl/{order.id}")
    # Send the email
    if settings.email and order.email_to:
        try:
            message = sellcoins_settings.message + "\n\n" + f"<a href='lightning://{lnurl}'><img src='http://{settings.host}:{settings.port}/api/v1/qrcode/{lnurl}'></a>"
            await send_email(
                sellcoins_settings.email_server,
                sellcoins_settings.email_port,
                sellcoins_settings.email_username,
                sellcoins_settings.email_password,
                sellcoins_settings.email_from,
                order.email_to,
                sellcoins_settings.subject,
                message,
            )
        except Exception as e:
            assert f"Error sending email: {e}"


async def pay_tribute(haircut_amount: int, wallet_id: str) -> None:
    try:
        tribute = int(2 * (haircut_amount / 100))
        pr = await get_pr("lnbits@nostr.com", tribute)
        if not pr:
            return
        await pay_invoice(
            wallet_id=wallet_id,
            payment_request=pr,
            max_sat=tribute,
            description="Tribut to help support LNbits",
        )
    except Exception:
        pass
    return
