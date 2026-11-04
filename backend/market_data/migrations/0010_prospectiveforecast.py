from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("market_data", "0009_backfill_historical_price_quality"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProspectiveForecast",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("model_key", models.CharField(max_length=40)),
                ("horizon", models.PositiveSmallIntegerField()),
                ("signal_date", models.DateField()),
                ("predicted_return", models.DecimalField(decimal_places=10, max_digits=16)),
                ("lower_return", models.DecimalField(blank=True, decimal_places=10, max_digits=16, null=True)),
                ("upper_return", models.DecimalField(blank=True, decimal_places=10, max_digits=16, null=True)),
                ("confidence", models.DecimalField(decimal_places=5, max_digits=6)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("scored_at", models.DateTimeField(blank=True, null=True)),
                ("entry_date", models.DateField(blank=True, null=True)),
                ("exit_date", models.DateField(blank=True, null=True)),
                ("entry_price", models.DecimalField(blank=True, decimal_places=4, max_digits=15, null=True)),
                ("exit_price", models.DecimalField(blank=True, decimal_places=4, max_digits=15, null=True)),
                ("realized_return", models.DecimalField(blank=True, decimal_places=10, max_digits=16, null=True)),
                ("stock", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="prospective_forecasts", to="stocks.stock")),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("stock", "model_key", "horizon", "signal_date"),
                        name="unique_prospective_stock_model_horizon_signal",
                    ),
                ],
            },
        ),
    ]
