from typing import List, Optional, Union
from datetime import datetime
from lnbits.db import Database
from lnbits.helpers import urlsafe_short_hash

from .models import Order, Product, Settings

db = Database("ext_sellcoins")

# SETTINGS


async def create_settings(data: Settings) -> Settings:
    await db.insert("sellcoins.settings", data)
    return Settings(**data.dict())


async def get_settings(user_id: str) -> Optional[Settings]:
    return await db.fetchone(
        "SELECT * FROM sellcoins.settings WHERE id = :id",
        {"id": user_id},
        Settings,
    )


async def update_settings(data: Settings) -> Settings:
    await db.update("sellcoins.settings", data)
    return Settings(**data.dict())


# Order


async def create_order(data: Order) -> Order:
    data.id = urlsafe_short_hash()
    await db.insert("sellcoins.orders", data)
    return Order(**data.dict())


async def get_order(checking_id: str) -> Optional[Order]:
    return await db.fetchone(
        "SELECT * FROM sellcoins.orders WHERE id = :id",
        {"id": checking_id},
        Order,
    )

async def update_order(data: Order) -> Order:
    await db.update("sellcoins.orders", data)
    return Order(**data.dict())


async def get_orders(settings_id: str) -> Optional[Order]:
    return await db.fetchall(
        "SELECT * FROM sellcoins.orders WHERE settings_id = :settings_id",
        {"settings_id": settings_id},
        Order,
    )


# PRODUCTS


async def create_product(data: Product) -> Product:
    data.id = urlsafe_short_hash()
    await db.insert("sellcoins.products", data)
    return Product(**data.dict())


async def get_product(product_id: str) -> Optional[Product]:
    return await db.fetchone(
        "SELECT * FROM sellcoins.products WHERE id = :id",
        {"id": product_id},
        Product,
    )


async def get_products(settings_id: str) -> List[Product]:
    return await db.fetchall(
        "SELECT * FROM sellcoins.products WHERE settings_id = :settings_id",
        {"settings_id": settings_id},
        Product,
    )


async def delete_product(product_id: str) -> None:
    await db.execute(
        "DELETE FROM sellcoins.products WHERE id = :id", {"id": product_id}
    )
