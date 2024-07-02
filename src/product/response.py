from typing import List

from ninja import Schema


class ProductDetailResponse(Schema):
    id: int
    name: str
    price: int


class ProductListResponse(Schema):
    products: List[ProductDetailResponse]
