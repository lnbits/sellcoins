from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timezone

class Settings(BaseModel):
    id: Optional[str] = ""
    denomination: Optional[str] = ""
    send_wallet_id: Optional[str] = ""
    receive_wallet_id: Optional[str] = ""
    title: Optional[str] = ""
    description: Optional[str] = ""
    header_image: Optional[str] = ""
    haircut: Optional[int] = ""
    auto_convert: Optional[bool]
    email: Optional[bool]
    nostr: Optional[bool]
    launch_page: Optional[bool]
    message: Optional[str] = ""

class Product(BaseModel):
    id: Optional[str] = ""
    settings_id: Optional[str] = ""
    title: Optional[str] = ""
    description: Optional[str] = ""
    amount: Optional[int]
    price: Optional[int]

class Order(BaseModel):
    id: Optional[str] = ""
    product_id: Optional[str] = ""
    settings_id: Optional[str] = ""
    email_to: Optional[str] = ""
    nostr_key: Optional[str] = ""
    status: Optional[str] = ""
    payment_request: Optional[str] = ""
    payment_hash: Optional[str] = ""
    created_at: datetime = datetime.now(timezone.utc)

class CreateOrder(BaseModel):
    payment_request: str
    order_id: str
    payment_hash: str
