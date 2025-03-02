# Description: Pydantic data models dictate what is passed between frontend and backend.

from typing import Optional

from pydantic import BaseModel

class Settings(BaseModel):
    user_id: Optional[str] = ""
    fiat: Optional[str] = ""
    wallet_id: Optional[str] = ""
    title: Optional[str] = ""
    description: Optional[str] = ""
    stripe_key: Optional[str] = ""

class Product(BaseModel):
    id: Optional[str] = ""
    title: Optional[str] = ""
    description: Optional[str] = ""
    price: Optional[int]
    auto_convert: Optional[bool]
    amount: Optional[int]
    cut_percentage: Optional[int]

class Orders(BaseModel):
    id: Optional[str] = ""
    product_id: Optional[str] = ""
    status: Optional[str] = ""
    stripe_purchase_id: Optional[str] = ""
    created: Optional[str] = ""
