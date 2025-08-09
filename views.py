from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from lnbits.core.models import User
from lnbits.decorators import check_user_exists
from lnbits.helpers import template_renderer
from lnbits.settings import settings
from .crud import get_order, get_product, get_products, get_settings
from loguru import logger
from lnbits.utils.exchange_rates import get_fiat_rate_and_price_satoshis
from lnurl import encode as url_encode

sellcoins_generic_router = APIRouter()


def sellcoins_renderer():
    return template_renderer(["sellcoins/templates"])


# Backend admin page


@sellcoins_generic_router.get("/", response_class=HTMLResponse)
async def index(req: Request, user: User = Depends(check_user_exists)):
    return sellcoins_renderer().TemplateResponse(
        "sellcoins/index.html", {"request": req, "user": user.json()}
    )


# Frontend shareable page


@sellcoins_generic_router.get("/{product_id}")
async def get_products_page(req: Request, product_id: str):
    product = await get_product(product_id)
    if not product:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Failed to launch product page."
        )
    products = await get_products(product.settings_id)
    if not products:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Failed to launch product page."
        )
    settings = await get_settings(product.settings_id)
    if not settings:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Failed to launch product page."
        )
    products_dicts = [p.dict(exclude={"settings_id"}) for p in products]
    exchange_rate = 1
    if settings.auto_convert:
        exchange_rate, _ = await get_fiat_rate_and_price_satoshis(settings.denomination)
    return sellcoins_renderer().TemplateResponse(
        "sellcoins/products.html",
        {
            "request": req,
            "products": products_dicts,
            "denomination": settings.denomination,
            "auto_convert": settings.auto_convert,
            "exchange_rate": exchange_rate,
            "haircut": settings.haircut,
            "title": settings.title,
            "description": settings.description,
            "header_image": settings.header_image,
        },
    )


@sellcoins_generic_router.get("/order/{order_id}")
async def get_order_page(req: Request, order_id: str):
    order = await get_order(order_id)
    if not order:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Order does not exist."
        )
    encoded_lnurl = url_encode(
        f"http://{settings.host}:{settings.port}/sellcoins/api/v1/lnurl/{order.id}"
    )
    return sellcoins_renderer().TemplateResponse(
        "sellcoins/order.html",
        {
            "request": req,
            "lnurl": encoded_lnurl,
            "order_id": order.id,
            "order_status": order.status,
            "payment_request": order.payment_request,
            "payment_hash": order.payment_hash,
        },
    )


# Manifest for public page


@sellcoins_generic_router.get("/manifest/{settings_id}.webmanifest")
async def manifest(settings_id: str):
    sellcoins_settings = await get_settings(settings_id)
    if not sellcoins_settings:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Settings do not exist."
        )
    return {
        "short_name": settings.lnbits_site_title,
        "name": sellcoins_settings.name + " - " + settings.lnbits_site_title,
        "icons": [
            {
                "src": (
                    settings.lnbits_custom_logo
                    if settings.lnbits_custom_logo
                    else "https://cdn.jsdelivr.net/gh/lnbits/lnbits@0.3.0/docs/logos/lnbits.png"
                ),
                "type": "image/png",
                "sizes": "900x900",
            }
        ],
        "start_url": "/sellcoins/" + settings_id,
        "background_color": "#1F2234",
        "description": "SellCoins extension",
        "display": "standalone",
        "scope": "/sellcoins/" + settings_id,
        "theme_color": "#1F2234",
        "shortcuts": [
            {
                "name": sellcoins_settings.name + " - " + settings.lnbits_site_title,
                "short_name": sellcoins_settings.name,
                "description": sellcoins_settings.name
                + " - "
                + settings.lnbits_site_title,
                "url": "/sellcoins/" + settings_id,
            }
        ],
    }
