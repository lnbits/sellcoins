from typing import List, Optional, Union

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
    await db.insert("sellcoins.Order", data)
    return Order(**data.dict())


async def get_order(checking_id: str) -> Optional[Order]:
    return await db.fetchone(
        "SELECT * FROM sellcoins.Order WHERE id = :id",
        {"id": checking_id},
        Order,
    )


async def update_order(data: Order) -> Order:
    await db.update("sellcoins.Order", data)
    return Order(**data.dict())


async def get_orders(wallet_ids: Union[str, List[str]]) -> List[Order]:
    if isinstance(wallet_ids, str):
        wallet_ids = [wallet_ids]
    q = ",".join([f"'{w}'" for w in wallet_ids])
    return await db.fetchall(
        f"SELECT * FROM sellcoins.Order WHERE wallet IN ({q}) ORDER BY id",
        model=Order,
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

async def get_products(setting_id: Union[str, List[str]]) -> List[Product]:
    return await db.fetchall(
        "SELECT * FROM sellcoins.products WHERE id = :id",
        {"id": setting_id},
        Product,
    )

async def delete_product(product_id: str) -> None:
    await db.execute(
        "DELETE FROM sellcoins.products WHERE id = :id", {"id": product_id}
    )
