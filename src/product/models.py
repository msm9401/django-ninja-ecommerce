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

    class Meta:
        app_label = "product"
        db_table = "product"
        indexes = [
            models.Index(fields=["status", "price"]),
        ]
