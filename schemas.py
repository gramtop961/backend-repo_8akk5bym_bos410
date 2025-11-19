"""
Database Schemas for Artisan Marketplace

Each Pydantic model represents a MongoDB collection. The collection name
is the lowercase of the class name (e.g., User -> "user").
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, EmailStr, HttpUrl
from datetime import datetime


class Address(BaseModel):
    full_name: str
    line1: str
    line2: Optional[str] = None
    city: str
    state: Optional[str] = None
    postal_code: str
    country: str
    phone: Optional[str] = None


class SocialLinks(BaseModel):
    website: Optional[HttpUrl] = None
    instagram: Optional[HttpUrl] = None
    facebook: Optional[HttpUrl] = None
    twitter: Optional[HttpUrl] = None
    pinterest: Optional[HttpUrl] = None


class Artist(BaseModel):
    name: str
    bio: Optional[str] = None
    location: Optional[str] = None
    avatar_url: Optional[HttpUrl] = None
    social: Optional[SocialLinks] = None


class ProductImage(BaseModel):
    url: HttpUrl
    alt: Optional[str] = None


class Variant(BaseModel):
    sku: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None
    material: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    stock: int = Field(0, ge=0)


class Product(BaseModel):
    title: str
    description: Optional[str] = None
    category: Literal[
        "Jewelry","Pottery","Textiles","Woodwork","Metalcraft","Glasswork","Paintings","Sculptures"
    ]
    tags: List[str] = []
    artist_id: Optional[str] = None  # ObjectId as str
    artist_name: Optional[str] = None
    price: float = Field(..., ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    materials: List[str] = []
    dimensions: Optional[str] = None
    weight_kg: Optional[float] = Field(None, ge=0)
    care_instructions: Optional[str] = None
    customization_options: Optional[str] = None
    images: List[ProductImage] = []
    variants: List[Variant] = []
    rating_average: float = 0
    rating_count: int = 0
    inventory: int = Field(0, ge=0)
    is_active: bool = True


class Review(BaseModel):
    product_id: str
    user_id: str
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = None
    content: Optional[str] = None
    photos: List[HttpUrl] = []
    verified_purchase: bool = False
    helpful_count: int = 0


class CartItem(BaseModel):
    product_id: str
    title: str
    price: float
    quantity: int = Field(1, ge=1)
    image: Optional[HttpUrl] = None
    variant: Optional[str] = None


class User(BaseModel):
    name: Optional[str] = None
    email: EmailStr
    password_hash: Optional[str] = None
    avatar_url: Optional[HttpUrl] = None
    is_active: bool = True
    is_admin: bool = False
    addresses: List[Address] = []
    wishlist: List[str] = []  # product ids
    cart: List[CartItem] = []
    provider: Literal["email","google","facebook"] = "email"


class OrderItem(BaseModel):
    product_id: str
    title: str
    unit_price: float
    quantity: int
    image: Optional[HttpUrl] = None
    variant: Optional[str] = None


class PaymentInfo(BaseModel):
    method: Literal["card","paypal","apple_pay","google_pay","bank_transfer"] = "card"
    status: Literal["pending","authorized","paid","failed","refunded"] = "pending"
    transaction_id: Optional[str] = None
    currency: str = "USD"
    marketplace_fee_pct: float = 0.1


class Shipment(BaseModel):
    carrier: Optional[str] = None
    service: Optional[str] = None
    cost: Optional[float] = None
    tracking_number: Optional[str] = None
    status: Literal["pending","label_created","in_transit","delivered","exception"] = "pending"
    estimated_delivery: Optional[datetime] = None


class Order(BaseModel):
    user_id: str
    items: List[OrderItem]
    subtotal: float
    shipping_cost: float = 0
    tax: float = 0
    discount: float = 0
    total: float
    currency: str = "USD"
    shipping_address: Address
    billing_address: Optional[Address] = None
    payment: PaymentInfo = PaymentInfo()
    shipment: Shipment = Shipment()
    status: Literal["created","processing","shipped","delivered","cancelled","refunded"] = "created"
