# Description: This file contains the extensions API endpoints.

from http import HTTPStatus

from fastapi import APIRouter, Depends, Request
from lnbits.core.models import WalletTypeInfo
from lnbits.decorators import require_admin_key, require_invoice_key
from starlette.exceptions import HTTPException

from .crud import (
    create_order,
    create_product,
    delete_product,
    get_order,
    get_orders,
    get_products,
    get_settings,
    update_settings,
)
from .models import Orders, Product, Settings

sellcoins_api_router = APIRouter()

## SETTINGS


@sellcoins_api_router.get("/api/v1/settings")
async def api_get_settings(
    wallet: WalletTypeInfo = Depends(require_invoice_key),
) -> Settings:
    settings = await get_settings(wallet.wallet.id)
    if not settings:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Settings not found."
        )
    return settings


@sellcoins_api_router.put("/api/v1/settings")
async def api_update_settings(
    data: Settings, wallet: WalletTypeInfo = Depends(require_admin_key)
) -> Settings:
    settings = await get_settings(wallet.wallet.id)
    if not settings:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Settings not found."
        )
    data.wallet_id = wallet.wallet.id
    return await update_settings(data)


## PACKAGES


@sellcoins_api_router.post("/api/v1/product", status_code=HTTPStatus.CREATED)
async def api_create_product(
    data: Product, wallet: WalletTypeInfo = Depends(require_admin_key)
) -> Product:
    data.wallet_id = wallet.wallet.id
    return await create_product(data)


@sellcoins_api_router.get("/api/v1/products")
async def api_get_products(
    wallet: WalletTypeInfo = Depends(require_invoice_key),
) -> list[Product]:
    return await get_products(wallet.wallet.id)


@sellcoins_api_router.delete("/api/v1/product/{product_id}")
async def api_delete_product(
    product_id: str, wallet: WalletTypeInfo = Depends(require_admin_key)
):
    await delete_product(product_id)
    return {"message": "Product deleted successfully"}


## ORDERS


@sellcoins_api_router.post("/api/v1/order", status_code=HTTPStatus.CREATED)
async def api_create_order(data: Orders) -> Orders:
    return await create_order(data)


@sellcoins_api_router.get("/api/v1/order/{order_id}")
async def api_get_order(order_id: str) -> Orders:
    order = await get_order(order_id)
    if not order:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Order not found.")
    return order


@sellcoins_api_router.get("/api/v1/orders")
async def api_get_orders(
    wallet: WalletTypeInfo = Depends(require_invoice_key),
) -> list[Orders]:
    return await get_orders(wallet.wallet.id)


## STRIPE WEBHOOK


@sellcoins_api_router.post("/api/v1/stripe/webhook")
async def api_stripe_webhook(request: Request):
    payload = await request.json()
    event_type = payload.get("type")

    if event_type == "payment_intent.succeeded":
        stripe_purchase_id = payload["data"]["object"]["id"]
        order = await get_order_by_stripe_id(stripe_purchase_id)
        if order:
            order.status = "paid"
            await update_order(order)

    return {"message": "Webhook received"}
