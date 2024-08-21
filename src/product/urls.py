from typing import Dict, List

from django.contrib.postgres.search import SearchQuery
from django.db import transaction
from django.http import HttpRequest
from django.db.models import F
from ninja import Router

from config.response import (
    ErrorResponse,
    ObjectResponse,
    OkResponse,
    error_response,
    response,
)
from product.exceptions import (
    OrderAlreadyPaidException,
    OrderInvalidProductException,
    OrderNotFoundException,
)
from product.models import (
    Category,
    Order,
    OrderLine,
    OrderStatus,
    Product,
    ProductStatus,
)
from product.request import OrderRequestBody
from product.response import (
    CategoryListResponse,
    OrderDetailResponse,
    ProductListResponse,
)
from user.authentication import bearer_auth, AuthRequest
from user.exceptions import UserPointsNotEnoughException, UserVersionConflictException
from user.models import ServiceUser, UserPoints, UserPointsHistory


router = Router(tags=["Products"])


@router.get(
    "",
    response={
        200: ObjectResponse[ProductListResponse],
    },
)
def product_list_handler(
    request: HttpRequest, category_id: int | None = None, query: str | None = None
):
    if query:
        products = Product.objects.filter(
            search_vector=SearchQuery(query), status=ProductStatus.ACTIVE
        )
    elif category_id:
        category: Category | None = Category.objects.filter(id=category_id).first()
        if not category:
            products = []
        else:
            category_ids: List[int] = [category.id] + list(
                category.children.values_list("id", flat=True)
            )
            products = Product.objects.filter(
                category_id__in=category_ids, status=ProductStatus.ACTIVE
            ).values("id", "name", "price")
    else:
        products = Product.objects.filter(status=ProductStatus.ACTIVE).values(
            "id", "name", "price"
        )

    return 200, response(ProductListResponse(products=products))


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


@router.post(
    "/orders",
    response={
        201: ObjectResponse[OrderDetailResponse],
        400: ObjectResponse[ErrorResponse],
    },
    auth=bearer_auth,
)
def order_products_handler(request: AuthRequest, body: OrderRequestBody):
    product_id_to_quantity: Dict[int, int] = body.product_id_to_quantity

    products: List[Product] = list(
        Product.objects.filter(
            id__in=product_id_to_quantity, status=ProductStatus.ACTIVE
        )
    )
    if len(products) != len(product_id_to_quantity):
        return 400, error_response(msg=OrderInvalidProductException.message)

    with transaction.atomic():
        total_price: int = 0
        order = Order.objects.create(user=request.user)

        order_lines_to_create: List[OrderLine] = []
        for product in products:
            price: int = product.price
            discount_ratio: float = 0.9  # 10%
            quantity: int = product_id_to_quantity[product.id]

            order_lines_to_create.append(
                OrderLine(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=price,
                    discount_ratio=discount_ratio,
                )
            )

            total_price += price * quantity * discount_ratio

        order.total_price = int(total_price)
        order.save()
        OrderLine.objects.bulk_create(objs=order_lines_to_create)

    return 201, response({"id": order.id, "total_price": order.total_price})


@router.post(
    "/orders/{order_id}/confirm",
    response={
        200: ObjectResponse[OkResponse],
        400: ObjectResponse[ErrorResponse],
        404: ObjectResponse[ErrorResponse],
    },
    auth=bearer_auth,
)
def confirm_order_payment_handler(request: AuthRequest, order_id: int):
    if not (order := Order.objects.filter(id=order_id, user=request.user).first()):
        return 404, error_response(msg=OrderNotFoundException.message)

    # # 결제 시스템
    # if not payment_service.confirm_payment(
    #     payment_key=body.payment_key, amount=order.total_price
    # ):
    #     return 400, error_response(msg=OrderPaymentConfirmFailedException.message)

    with transaction.atomic():
        success: int = Order.objects.filter(
            id=order_id, status=OrderStatus.PENDING
        ).update(status=OrderStatus.PAID)
        if not success:
            return 400, error_response(msg=OrderAlreadyPaidException.message)

        # # pessimistic lock
        # user = ServiceUser.objects.select_for_update().get(id=request.user.id)  # lock
        # if user.points < order.total_price:
        #     return 409, error_response(msg=UserPointsNotEnoughException.message)

        # ServiceUser.objects.filter(id=request.user.id).update(
        #     points=F("points") - order.total_price,
        #     order_count=F("order_count") + 1,
        # )

        # optimistic lock
        user = ServiceUser.objects.get(id=request.user.id)
        if user.points < order.total_price:
            return 409, error_response(msg=UserPointsNotEnoughException.message)

        success: int = ServiceUser.objects.filter(
            id=request.user.id, version=user.version
        ).update(
            points=F("points") - order.total_price,
            order_count=F("order_count") + 1,
            version=user.version + 1,
        )
        if not success:
            return 409, error_response(msg=UserVersionConflictException.message)

        UserPointsHistory.objects.create(
            user=user,
            points_change=-order.total_price,
            reason=f"orders:{order.id}:confirm",
        )

        # 트랜잭션 실패로 인한 rollback시 retry로직이나 프론트에서 재요청 하는 정책 수립 필요

    return 200, response(OkResponse())


@router.post(
    "/orders/{order_id}/confirm-v2",
    response={
        200: ObjectResponse[OkResponse],
        400: ObjectResponse[ErrorResponse],
        404: ObjectResponse[ErrorResponse],
        409: ObjectResponse[ErrorResponse],
    },
    auth=bearer_auth,
)
def confirm_order_payment_handler_v2(request: AuthRequest, order_id: int):
    if not (order := Order.objects.filter(id=order_id, user=request.user).first()):
        return 404, error_response(msg=OrderNotFoundException.message)

    with transaction.atomic():
        success: int = Order.objects.filter(
            id=order_id, status=OrderStatus.PENDING
        ).update(status=OrderStatus.PAID)
        if not success:
            return 400, error_response(msg=OrderAlreadyPaidException.message)

        last_points = (
            UserPoints.objects.filter(user_id=request.user.id)
            .order_by("-version")
            .first()
        )
        if last_points.points_sum < order.total_price:
            return 409, error_response(msg=UserPointsNotEnoughException.message)

        UserPoints.objects.create(
            user_id=request.user.id,
            version=last_points.version + 1,
            points_change=-order.total_price,
            points_sum=last_points.points_sum - order.total_price,
            reason=f"orders:{order.id}:confirm",
        )

        if not success:
            return 409, error_response(msg=UserVersionConflictException.message)

        ServiceUser.objects.filter(id=request.user.id).update(
            order_count=F("order_count") + 1
        )

    return 200, response(OkResponse())
