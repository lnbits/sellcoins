from http import HTTPStatus

from fastapi import APIRouter, Depends
from lnbits.core.models import CreateInvoice, WalletTypeInfo
from lnbits.core.services import create_payment_request
from lnbits.decorators import require_admin_key, require_invoice_key
from lnbits.settings import settings as lnbits_settings
from loguru import logger
from starlette.exceptions import HTTPException

from .crud import (
    create_order,
    create_product,
    create_settings,
    delete_product,
    get_orders,
    get_product,
    get_products,
    get_settings,
    update_order,
    update_settings,
)
from .models import CreateOrder, Order, Product, Settings

sellcoins_api_router = APIRouter()

## SETTINGS


@sellcoins_api_router.get("/api/v1/settings")
async def api_get_settings(
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> Settings:
    settings = await get_settings(wallet.wallet.user)
    if not settings:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Settings not found."
        )
    return settings


@sellcoins_api_router.put("/api/v1/settings")
async def api_update_settings(
    data: Settings, wallet: WalletTypeInfo = Depends(require_admin_key)
) -> Settings:
    settings = await get_settings(wallet.wallet.user)
    if not settings:
        data.id = wallet.wallet.user
        return await create_settings(data)
    data.id = wallet.wallet.user
    return await update_settings(data)


## PRODUCTS


@sellcoins_api_router.post("/api/v1/product", status_code=HTTPStatus.CREATED)
async def api_create_product(
    data: Product, wallet: WalletTypeInfo = Depends(require_admin_key)
) -> Product:
    return await create_product(data)


@sellcoins_api_router.get("/api/v1/products")
async def api_get_products(
    wallet: WalletTypeInfo = Depends(require_invoice_key),
) -> list[Product]:
    return await get_products(wallet.wallet.user)


@sellcoins_api_router.delete("/api/v1/product/{product_id}")
async def api_delete_product(
    product_id: str, wallet: WalletTypeInfo = Depends(require_admin_key)
):
    await delete_product(product_id)
    return {"message": "Product deleted successfully"}


## Order


@sellcoins_api_router.get("/api/v1/order/{product_id}", status_code=HTTPStatus.CREATED)
async def api_create_order(product_id: str) -> CreateOrder:
    product = await get_product(product_id)
    if not product:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Product not found."
        )
    settings = await get_settings(product.settings_id)
    if not settings:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Settings not found."
        )
    if not settings.denomination or not settings.receive_wallet_id:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Payment settings are incomplete.",
        )
    amount: int | None
    if product.price:
        if lnbits_settings.lnbits_denomination == "sats":
            amount = product.price
        else:
            amount = product.price * 100
    else:
        amount = product.amount
    if amount is None:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Product amount is not configured.",
        )
    order_data = Order(product_id=product_id, settings_id=settings.id, status="unpaid")
    order = await create_order(order_data)
    try:
        invoice_data = CreateInvoice(
            out=False,
            amount=amount,
            fiat_provider="stripe" if settings.live_mode else None,
            unit=settings.denomination if settings.live_mode else "sat",
            memo=f"Order ID:{order.id}",
            extra={
                "tag": "SellCoins",
                "order_id": order.id,
                "amount": product.amount,
                "haircut": f"{settings.haircut}%",
                "product_id": product.id,
            },
        )

        payment = await create_payment_request(settings.receive_wallet_id, invoice_data)
        if settings.live_mode:
            payment_request = payment.extra["fiat_payment_request"]
        else:
            payment_request = payment.bolt11
        order.payment_request = payment_request
        order.payment_hash = payment.checking_id
        await update_order(order)
        create_order_response = CreateOrder(
            payment_request=payment_request,
            order_id=order.id or "",
            payment_hash=payment.checking_id,
        )
        return create_order_response

    except Exception as exc:
        logger.warning(exc)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc


@sellcoins_api_router.get("/api/v1/orders/{settings_id}")
async def api_get_orders(
    settings_id: str,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> list[Order]:
    return await get_orders(settings_id)
