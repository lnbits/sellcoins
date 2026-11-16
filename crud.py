from secrets import token_hex
from typing import Optional

from lnbits.db import Database
from lnbits.helpers import urlsafe_short_hash

from .models import Order, Product, Settings

db = Database("ext_sellcoins")

# SETTINGS


async def create_settings(data: Settings) -> Settings:
    await db.insert("sellcoins.settings", data)
    return Settings(**data.model_dump())


async def get_settings(user_id: Optional[str]) -> Optional[Settings]:
    return await db.fetchone(
        "SELECT * FROM sellcoins.settings WHERE id = :id",
        {"id": user_id},
        Settings,
    )


async def update_settings(data: Settings) -> Settings:
    await db.update("sellcoins.settings", data)
    return Settings(**data.model_dump())


# Order


async def create_order(data: Order) -> Order:
    data.id = urlsafe_short_hash()
    await db.insert("sellcoins.orders", data)
    return Order(**data.model_dump())


async def get_order(checking_id: str) -> Optional[Order]:
    return await db.fetchone(
        "SELECT * FROM sellcoins.orders WHERE id = :id",
        {"id": checking_id},
        Order,
    )


async def update_order(data: Order) -> Order:
    await db.update("sellcoins.orders", data)
    return Order(**data.model_dump())


async def prepare_order_withdrawal(order_id: str, sats_amount: int) -> Optional[Order]:
    await db.execute(
        """
        UPDATE sellcoins.orders SET sats_amount = :sats_amount, k1 = :k1
        WHERE id = :id AND status = 'paid' AND k1 IS NULL
        """,
        {"id": order_id, "sats_amount": sats_amount, "k1": token_hex(32)},
    )
    return await get_order(order_id)


async def claim_order(order_id: str, k1: str, sats_amount: int) -> bool:
    result = await db.execute(
        """
        UPDATE sellcoins.orders SET status = 'claimed'
        WHERE id = :id AND status = 'paid' AND k1 = :k1
          AND sats_amount = :sats_amount
        """,
        {"id": order_id, "k1": k1, "sats_amount": sats_amount},
    )
    return result.rowcount == 1


async def set_order_status(order_id: str, status: str, expected_status: str) -> bool:
    result = await db.execute(
        """
        UPDATE sellcoins.orders SET status = :status
        WHERE id = :id AND status = :expected_status
        """,
        {"id": order_id, "status": status, "expected_status": expected_status},
    )
    return result.rowcount == 1


async def get_orders(settings_id: str) -> list[Order]:
    return await db.fetchall(
        "SELECT * FROM sellcoins.orders WHERE settings_id = :settings_id",
        {"settings_id": settings_id},
        Order,
    )


# PRODUCTS


async def create_product(data: Product) -> Product:
    data.id = urlsafe_short_hash()
    await db.insert("sellcoins.products", data)
    return Product(**data.model_dump())


async def get_product(product_id: Optional[str]) -> Optional[Product]:
    return await db.fetchone(
        "SELECT * FROM sellcoins.products WHERE id = :id",
        {"id": product_id},
        Product,
    )


async def get_products(settings_id: Optional[str]) -> list[Product]:
    return await db.fetchall(
        "SELECT * FROM sellcoins.products WHERE settings_id = :settings_id",
        {"settings_id": settings_id},
        Product,
    )


async def delete_product(product_id: str) -> None:
    await db.execute(
        "DELETE FROM sellcoins.products WHERE id = :id", {"id": product_id}
    )
