from http import HTTPStatus

from fastapi import APIRouter, Depends
from lnbits.core.models import WalletTypeInfo
from lnbits.decorators import require_admin_key, require_invoice_key
from lnbits.utils.exchange_rates import btc_rates
from lnbits.core.services import create_invoice
from starlette.exceptions import HTTPException

from .crud import (
    create_order,
    create_product,
    delete_product,
    get_order,
    get_orders,
    get_product,
    get_products,
    get_settings,
    update_settings,
    create_settings,
)
from .models import Order, Product, Settings
from loguru import logger
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
    data.wallet_id = wallet.wallet.id
    return await update_settings(data)


## PRODUCTS

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


## Order


@sellcoins_api_router.post("/api/v1/order", status_code=HTTPStatus.CREATED)
async def api_create_order(data: Order) -> Order:
    product = await get_product(data.product_id)
    settings = await get_settings(product.settings_id)
    if settings.auto_convert:
        rate = await btc_rates(settings.denomination)
        sats = (100 / int(rate)) * 100_000_000
        amount = sats * (1 + settings.haircut_amount / 100)
    else:
        amount = product.price
        try:
            payment = await create_invoice(
                wallet_id=settings.wallet_id,
                amount=amount,
                memo=f"Sellcoins ransaction for {product.title}",
                extra={
                    "tag": "sellcoins"
                },
            )
        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Failed to create invoice.",
            )
    data.id = payment.checking_id
    data.product_id = product.id
    await create_order(data)
    return payment


@sellcoins_api_router.get("/api/v1/order/{order_id}")
async def api_get_order(order_id: str) -> Order:
    order = await get_order(order_id)
    if not order:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Order not found.")
    return order


@sellcoins_api_router.get("/api/v1/Order")
async def api_get_orders(
    wallet: WalletTypeInfo = Depends(require_invoice_key),
) -> list[Order]:
    return await get_orders(wallet.wallet.id)