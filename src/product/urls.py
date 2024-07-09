from django.http import HttpRequest
from ninja import Router

from config.response import ObjectResponse, response
from product.models import Category, Product, ProductStatus
from product.response import CategoryListResponse, ProductListResponse


router = Router(tags=["Products"])


@router.get(
    "",
    response={
        200: ObjectResponse[ProductListResponse],
    },
)
def product_list_handler(request: HttpRequest):
    return 200, response(
        ProductListResponse(
            products=Product.objects.filter(status=ProductStatus.ACTIVE).values(
                "id", "name", "price"
            )
        )
    )


@router.get(
    "/categories",
    response={
        200: ObjectResponse[CategoryListResponse],
    },
)
def categories_list_handler(request: HttpRequest):
    return 200, response(
        CategoryListResponse.build(
            categories=Category.objects.filter(parent=None).prefetch_related("children")
        )
    )
