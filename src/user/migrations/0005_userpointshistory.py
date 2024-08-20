# Generated by Django 5.0.1 on 2024-08-20 12:54

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("user", "0004_serviceuser_version"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserPointsHistory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("points_change", models.IntegerField(default=0)),
                ("reason", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="points_history",
                        to="user.serviceuser",
                    ),
                ),
            ],
            options={
                "db_table": "user_points_history",
            },
        ),
    ]
