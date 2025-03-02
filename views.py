# Description: Add your page endpoints here.

from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from lnbits.core.models import User
from lnbits.decorators import check_user_exists
from lnbits.helpers import template_renderer

from .crud import get_order, get_products, get_settings

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


@sellcoins_generic_router.get("/order/{order_id}")
async def get_order_page(req: Request, order_id: str):
    order = await get_order(order_id)
    if not order:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Order does not exist."
        )
    return sellcoins_renderer().TemplateResponse(
        "sellcoins/order.html",
        {"request": req, "order": order},
    )


@sellcoins_generic_router.get("/products")
async def get_products_page(req: Request, user: User = Depends(check_user_exists)):
    products = await get_products(user.wallet_ids)
    return sellcoins_renderer().TemplateResponse(
        "sellcoins/products.html", {"request": req, "products": products}
    )


# Manifest for public page


@sellcoins_generic_router.get("/manifest/{settings_id}.webmanifest")
async def manifest(settings_id: str):
    settings = await get_settings(settings_id)
    if not settings:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Settings do not exist."
        )
    return {
        "short_name": settings.lnbits_site_title,
        "name": settings.title + " - " + settings.lnbits_site_title,
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
                "name": settings.title + " - " + settings.lnbits_site_title,
                "short_name": settings.title,
                "description": settings.title + " - " + settings.lnbits_site_title,
                "url": "/sellcoins/" + settings_id,
            }
        ],
    }
