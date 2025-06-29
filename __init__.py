import asyncio

from fastapi import APIRouter
from lnbits.tasks import create_permanent_unique_task
from loguru import logger

from .crud import db
from .tasks import wait_for_paid_invoices
from .views import sellcoins_generic_router
from .views_api import sellcoins_api_router
from .views_lnurl import sellcoins_lnurl_router

logger.debug(
    "Sellcoins running and ready to sell coins!"
)


sellcoins_ext: APIRouter = APIRouter(prefix="/sellcoins", tags=["SellCoins"])
sellcoins_ext.include_router(sellcoins_generic_router)
sellcoins_ext.include_router(sellcoins_api_router)
sellcoins_ext.include_router(sellcoins_lnurl_router)

sellcoins_static_files = [
    {
        "path": "/sellcoins/static",
        "name": "sellcoins_static",
    }
]

scheduled_tasks: list[asyncio.Task] = []


def sellcoins_stop():
    for task in scheduled_tasks:
        try:
            task.cancel()
        except Exception as ex:
            logger.warning(ex)


def sellcoins_start():
    task = create_permanent_unique_task("ext_sellcoins", wait_for_paid_invoices)
    scheduled_tasks.append(task)


__all__ = [
    "db",
    "sellcoins_ext",
    "sellcoins_static_files",
    "sellcoins_start",
    "sellcoins_stop",
]
