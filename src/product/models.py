from enum import Enum

from django.db import models


class ProductStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"


class Product(models.Model):
    name = models.CharField(max_length=128)
    price = models.PositiveIntegerField()
    status = models.CharField(max_length=8)  # active | inactive | paused
    category = models.ForeignKey("Category", on_delete=models.SET_NULL, null=True)

    class Meta:
        app_label = "product"
        db_table = "product"
        indexes = [
            models.Index(fields=["status", "price"]),
        ]


class Category(models.Model):
    name = models.CharField(max_length=32)
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, related_name="children"
    )

    class Meta:
        app_label = "product"
        db_table = "category"


class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"


class Order(models.Model):
    user = models.ForeignKey(
        "user.ServiceUser", on_delete=models.CASCADE, related_name="orders"
    )
    total_price = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=8, default=OrderStatus.PENDING
    )  # pending | paid | cancelled
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "product"
        db_table = "order"
        indexes = [
            models.Index(fields=["user", "status"]),
        ]


class OrderLine(models.Model):
    product = models.ForeignKey("Product", on_delete=models.CASCADE)
    order = models.ForeignKey("Order", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.PositiveIntegerField()
    discount_ratio = models.FloatField(default=1)

    class Meta:
        app_label = "product"
        db_table = "order_line"
