from typing import Optional
from pydantic import BaseModel

class Settings(BaseModel):
    user_id: Optional[str] = ""
    denomination: Optional[str] = ""
    send_wallet_id: Optional[str] = ""
    receive_wallet_id: Optional[str] = ""
    title: Optional[str] = ""
    description: Optional[str] = ""
    header_mage: Optional[str] = ""
    haircut: Optional[int] = ""
    auto_convert: Optional[bool]
    email: Optional[bool]
    email_server: Optional[str] = ""
    email_port: Optional[int]
    email_username: Optional[str] = ""
    email_password: Optional[str] = ""
    email_from: Optional[str] = ""
    email_subject: Optional[str] = ""
    email_message: Optional[str] = ""

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
    email_to: Optional[str] = ""
    status: Optional[str] = "" # "pending", "completed", "cancelled"
    created: Optional[str] = ""