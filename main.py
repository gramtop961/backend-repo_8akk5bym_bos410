import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime, timezone

from database import db
from schemas import Product as ProductSchema, Review as ReviewSchema, Order as OrderSchema

app = FastAPI(title="Artisan Marketplace API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helpers
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)


def serialize_doc(doc: dict):
    if not doc:
        return doc
    doc["id"] = str(doc.pop("_id"))
    # Convert datetimes to isoformat
    for k, v in list(doc.items()):
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


# Ensure indexes
if db is not None:
    db["product"].create_index("category")
    db["product"].create_index("price")
    db["product"].create_index("tags")
    db["product"].create_index("artist_name")
    db["product"].create_index([("title", "text"), ("description", "text"), ("tags", "text"), ("artist_name", "text")])
    db["review"].create_index([("product_id", 1), ("created_at", -1)])
    db["order"].create_index([("user_id", 1), ("created_at", -1)])


@app.get("/")
def read_root():
    return {"message": "Artisan Marketplace API running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Connected & Working"
            response["database_url"] = "✅ Set"
            response["database_name"] = db.name
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()
            except Exception as e:
                response["collections"] = [f"Error: {str(e)[:80]}"]
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response


# Seed a few sample products if empty (for demo)
SAMPLE_IMAGES = [
    {
        "url": "https://images.unsplash.com/photo-1561501900-3701fa6a0864?auto=format&fit=crop&w=800&q=60",
        "alt": "Handmade pottery bowl"
    },
    {
        "url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=800&q=60",
        "alt": "Jewelry bracelet"
    },
]


def seed_products_if_empty():
    if db is None:
        return
    if db["product"].count_documents({}) == 0:
        demo_products = [
            {
                "title": "Handcrafted Ceramic Bowl",
                "description": "Wheel-thrown stoneware bowl with matte glaze.",
                "category": "Pottery",
                "tags": ["ceramic", "bowl", "kitchen"],
                "artist_name": "Lena Park",
                "price": 48.0,
                "currency": "USD",
                "materials": ["Stoneware", "Glaze"],
                "dimensions": "18cm x 8cm",
                "weight_kg": 0.6,
                "images": [SAMPLE_IMAGES[0]],
                "rating_average": 4.8,
                "rating_count": 26,
                "inventory": 12,
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "title": "Sterling Silver Cuff",
                "description": "Minimalist silver cuff bracelet, adjustable.",
                "category": "Jewelry",
                "tags": ["silver", "bracelet"],
                "artist_name": "Omar Reyes",
                "price": 95.0,
                "currency": "USD",
                "materials": ["Sterling Silver"],
                "dimensions": "6mm width",
                "images": [SAMPLE_IMAGES[1]],
                "rating_average": 4.6,
                "rating_count": 14,
                "inventory": 20,
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
        ]
        db["product"].insert_many(demo_products)


seed_products_if_empty()


@app.get("/api/products")
def list_products(
    q: Optional[str] = None,
    category: Optional[str] = None,
    price_min: Optional[float] = Query(None, ge=0),
    price_max: Optional[float] = Query(None, ge=0),
    sort: Optional[str] = Query("new"),
    page: int = Query(1, ge=1),
    limit: int = Query(16, ge=1, le=60),
):
    if db is None:
        raise HTTPException(500, detail="Database not available")
    filter_q = {"is_active": True}
    if category:
        filter_q["category"] = category
    if price_min is not None or price_max is not None:
        price_filter = {}
        if price_min is not None:
            price_filter["$gte"] = price_min
        if price_max is not None:
            price_filter["$lte"] = price_max
        filter_q["price"] = price_filter
    if q:
        # search across title, description, tags, artist_name
        filter_q["$text"] = {"$search": q}

    sort_map = {
        "new": ("created_at", -1),
        "price_asc": ("price", 1),
        "price_desc": ("price", -1),
        "popular": ("rating_count", -1),
        "best": ("rating_average", -1),
    }
    sort_field, sort_dir = sort_map.get(sort, ("created_at", -1))

    skip = (page - 1) * limit
    cursor = db["product"].find(filter_q).sort(sort_field, sort_dir).skip(skip).limit(limit)
    items = [serialize_doc(d) for d in cursor]
    total = db["product"].count_documents(filter_q)
    return {"items": items, "page": page, "limit": limit, "total": total}


@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    if db is None:
        raise HTTPException(500, detail="Database not available")
    try:
        doc = db["product"].find_one({"_id": ObjectId(product_id)})
    except Exception:
        raise HTTPException(400, detail="Invalid product id")
    if not doc:
        raise HTTPException(404, detail="Product not found")
    return serialize_doc(doc)


@app.get("/api/search/suggest")
def search_suggest(q: str = Query(..., min_length=1), limit: int = Query(8, ge=1, le=20)):
    if db is None:
        raise HTTPException(500, detail="Database not available")
    regex = {"$regex": q, "$options": "i"}
    filter_q = {
        "$or": [
            {"title": regex},
            {"description": regex},
            {"tags": regex},
            {"artist_name": regex},
        ]
    }
    cursor = db["product"].find(filter_q, {"title": 1, "artist_name": 1}).limit(limit)
    items = [serialize_doc(d) for d in cursor]
    return {"suggestions": items}


class ReviewIn(ReviewSchema):
    pass


@app.get("/api/products/{product_id}/reviews")
def get_reviews(product_id: str, page: int = 1, limit: int = 10):
    if db is None:
        raise HTTPException(500, detail="Database not available")
    skip = (page - 1) * limit
    cursor = (
        db["review"].find({"product_id": product_id}).sort("created_at", -1).skip(skip).limit(limit)
    )
    items = [serialize_doc(d) for d in cursor]
    total = db["review"].count_documents({"product_id": product_id})
    return {"items": items, "page": page, "limit": limit, "total": total}


@app.post("/api/products/{product_id}/reviews")
def create_review(product_id: str, review: ReviewIn):
    if db is None:
        raise HTTPException(500, detail="Database not available")
    data = review.model_dump()
    data["product_id"] = product_id
    data["created_at"] = datetime.now(timezone.utc)
    data["updated_at"] = datetime.now(timezone.utc)
    res = db["review"].insert_one(data)
    # Update product rating simple aggregation
    pipeline = [
        {"$match": {"product_id": product_id}},
        {"$group": {"_id": "$product_id", "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}},
    ]
    agg = list(db["review"].aggregate(pipeline))
    if agg:
        db["product"].update_one(
            {"_id": ObjectId(product_id)},
            {"$set": {"rating_average": agg[0]["avg"], "rating_count": agg[0]["count"]}},
        )
    return {"id": str(res.inserted_id)}


class OrderIn(OrderSchema):
    pass


@app.post("/api/orders")
def create_order(order: OrderIn):
    if db is None:
        raise HTTPException(500, detail="Database not available")
    data = order.model_dump()
    data["created_at"] = datetime.now(timezone.utc)
    data["updated_at"] = datetime.now(timezone.utc)
    # naive inventory check
    for item in data.get("items", []):
        pid = item.get("product_id")
        pdoc = db["product"].find_one({"_id": ObjectId(pid)})
        if not pdoc:
            raise HTTPException(400, detail=f"Product {pid} not found")
        if pdoc.get("inventory", 0) < item.get("quantity", 1):
            raise HTTPException(400, detail=f"Insufficient inventory for {pdoc.get('title')}")
    # decrement inventory
    for item in data.get("items", []):
        pid = item.get("product_id")
        db["product"].update_one({"_id": ObjectId(pid)}, {"$inc": {"inventory": -item.get("quantity", 1)}})

    res = db["order"].insert_one(data)
    return {"id": str(res.inserted_id), "status": "created"}
