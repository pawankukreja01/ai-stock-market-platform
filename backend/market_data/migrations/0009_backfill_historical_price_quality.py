
from django.db import migrations


def classify_historical_prices(apps, schema_editor):
    HistoricalPrice = apps.get_model(
        "market_data",
        "HistoricalPrice",
    )

    batch = []

    for record in HistoricalPrice.objects.select_related(
        "stock"
    ).iterator(chunk_size=500):

        stock = record.stock
        symbol = stock.symbol.upper()
        storage_currency = (stock.currency or "").upper()

        # Legacy currency provenance:
        # The London currency audit confirmed GBp for GBP-denominated
        # London listings, and USD for CPG.L and IHG.L.
        if symbol.endswith(".L") and storage_currency == "GBP":
            provider_currency = "GBp"
        elif symbol.endswith(".L") and storage_currency == "USD":
            provider_currency = "USD"
        else:
            # Original provider currency was not retained for these
            # older records. An empty value honestly represents unknown.
            provider_currency = ""

        flags = []
        ohlc_flags = []

        prices = {
            "OPEN": record.open_price,
            "HIGH": record.high_price,
            "LOW": record.low_price,
            "CLOSE": record.close_price,
        }

        for name, value in prices.items():
            if value is None:
                flag = f"MISSING_{name}"
                flags.append(flag)
                ohlc_flags.append(flag)
            elif value <= 0:
                flag = f"{name}_NON_POSITIVE"
                flags.append(flag)
                ohlc_flags.append(flag)

        open_price = record.open_price
        high_price = record.high_price
        low_price = record.low_price
        close_price = record.close_price

        if high_price is not None and low_price is not None:
            if high_price < low_price:
                flags.append("HIGH_BELOW_LOW")
                ohlc_flags.append("HIGH_BELOW_LOW")

        if high_price is not None and open_price is not None:
            if high_price < open_price:
                flags.append("HIGH_BELOW_OPEN")
                ohlc_flags.append("HIGH_BELOW_OPEN")

        if high_price is not None and close_price is not None:
            if high_price < close_price:
                flags.append("HIGH_BELOW_CLOSE")
                ohlc_flags.append("HIGH_BELOW_CLOSE")

        if low_price is not None and open_price is not None:
            if low_price > open_price:
                flags.append("LOW_ABOVE_OPEN")
                ohlc_flags.append("LOW_ABOVE_OPEN")

        if low_price is not None and close_price is not None:
            if low_price > close_price:
                flags.append("LOW_ABOVE_CLOSE")
                ohlc_flags.append("LOW_ABOVE_CLOSE")

        volume_valid = (
            record.volume is not None
            and record.volume >= 0
        )

        if not volume_valid:
            flags.append("INVALID_VOLUME")

        record.provider_currency = provider_currency
        record.storage_currency = storage_currency
        record.is_ohlc_valid = not bool(ohlc_flags)
        record.is_volume_valid = volume_valid
        record.quality_flags = flags

        batch.append(record)

        if len(batch) >= 500:
            HistoricalPrice.objects.bulk_update(
                batch,
                [
                    "provider_currency",
                    "storage_currency",
                    "is_ohlc_valid",
                    "is_volume_valid",
                    "quality_flags",
                ],
                batch_size=500,
            )
            batch.clear()

    if batch:
        HistoricalPrice.objects.bulk_update(
            batch,
            [
                "provider_currency",
                "storage_currency",
                "is_ohlc_valid",
                "is_volume_valid",
                "quality_flags",
            ],
            batch_size=500,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("market_data", "0008_historicalprice_is_ohlc_valid_and_more"),
    ]

    operations = [
        migrations.RunPython(
            classify_historical_prices,
            migrations.RunPython.noop,
        ),
    ]
