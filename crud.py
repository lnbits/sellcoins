# Description: This file contains the CRUD operations for talking to the database.

from typing import List, Optional, Union

from lnbits.db import Database
from lnbits.helpers import urlsafe_short_hash

from .models import Orders, Product, Settings

db = Database("ext_sellcoins")

# SETTINGS


async def create_settings(data: Settings) -> Settings:
    data.id = urlsafe_short_hash()
    await db.insert("sellcoins.settings", data)
    return Settings(**data.dict())


async def get_settings(sellcoins_id: str) -> Optional[Settings]:
    return await db.fetchone(
        "SELECT * FROM sellcoins.settings WHERE id = :id",
        {"id": sellcoins_id},
        Settings,
    )


async def update_settings(data: Settings) -> Settings:
    await db.update("sellcoins.settings", data)
    return Settings(**data.dict())


# ORDERS


async def create_order(data: Orders) -> Orders:
    data.id = urlsafe_short_hash()
    await db.insert("sellcoins.orders", data)
    return Orders(**data.dict())


async def get_order(sellcoins_id: str) -> Optional[Orders]:
    return await db.fetchone(
        "SELECT * FROM sellcoins.orders WHERE id = :id",
        {"id": sellcoins_id},
        Orders,
    )


async def update_order(data: Orders) -> Orders:
    await db.update("sellcoins.orders", data)
    return Orders(**data.dict())


async def get_orders(wallet_ids: Union[str, List[str]]) -> List[Orders]:
    if isinstance(wallet_ids, str):
        wallet_ids = [wallet_ids]
    q = ",".join([f"'{w}'" for w in wallet_ids])
    return await db.fetchall(
        f"SELECT * FROM sellcoins.orders WHERE wallet IN ({q}) ORDER BY id",
        model=Orders,
    )


# PACKAGES


async def create_product(data: Product) -> Product:
    data.id = urlsafe_short_hash()
    await db.insert("sellcoins.products", data)
    return Product(**data.dict())


async def get_products(sellcoins_id: str) -> Optional[Product]:
    return await db.fetchone(
        "SELECT * FROM sellcoins.products WHERE id = :id",
        {"id": sellcoins_id},
        Product,
    )


async def delete_product(sellcoins_id: str) -> None:
    await db.execute(
        "DELETE FROM sellcoins.products WHERE id = :id", {"id": sellcoins_id}
    )
