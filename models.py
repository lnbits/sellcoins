from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel


class Settings(BaseModel):
    id: Optional[str] = ""
    denomination: Optional[str] = ""
    send_wallet_id: Optional[str] = ""
    receive_wallet_id: Optional[str] = ""
    title: Optional[str] = ""
    description: Optional[str] = ""
    header_image: Optional[str] = ""
    haircut: Optional[int] = None
    auto_convert: Optional[bool] = None
    email: Optional[bool] = None
    nostr: Optional[bool] = None
    launch_page: Optional[bool] = None
    live_mode: Optional[bool] = None
    message: Optional[str] = ""


class Product(BaseModel):
    id: Optional[str] = ""
    settings_id: Optional[str] = ""
    title: Optional[str] = ""
    description: Optional[str] = ""
    amount: Optional[int] = None
    price: Optional[int] = None


class Order(BaseModel):
    id: Optional[str] = ""
    product_id: Optional[str] = ""
    settings_id: Optional[str] = ""
    email_to: Optional[str] = ""
    nostr_key: Optional[str] = ""
    status: Optional[str] = ""
    payment_request: Optional[str] = ""
    payment_hash: Optional[str] = ""
    sats_amount: Optional[int] = 0
    created_at: datetime = datetime.now(timezone.utc)


class CreateOrder(BaseModel):
    payment_request: str
    order_id: str
    payment_hash: str
