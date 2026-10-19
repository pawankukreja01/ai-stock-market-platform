
from datetime import datetime

import torch
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from market_data.models import NewsArticle


MODEL_NAME = "ProsusAI/finbert"
MAX_SEQUENCE_LENGTH = 256
BATCH_SIZE = 8

# The FinBERT model card defines its output indices this way.
FALLBACK_LABELS = {
    0: "positive",
    1: "negative",
    2: "neutral",
}

SENTIMENT_FIELDS = [
    "sentiment_label",
    "sentiment_score",
    "sentiment_positive_prob",
    "sentiment_neutral_prob",
    "sentiment_negative_prob",
    "sentiment_model",
    "sentiment_analyzed_at",
]


class Command(BaseCommand):
    help = (
        "Analyze stock-news sentiment using FinBERT and "
        "save the results to the database."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--symbol",
            type=str,
            default="",
            help="Optional stock symbol, e.g. AAPL.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=500,
            help="Maximum number of articles to process (1-5000).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-analyze articles that already have sentiment results.",
        )

    def handle(self, *args, **options):
        symbol = options["symbol"].strip().upper()
        limit = options["limit"]
        force = options["force"]

        if not 1 <= limit <= 5000:
            raise CommandError("--limit must be between 1 and 5000.")

        articles_query = NewsArticle.objects.select_related("stock")

        if symbol:
            articles_query = articles_query.filter(stock__symbol=symbol)

        if not force:
            articles_query = articles_query.filter(
                Q(sentiment_analyzed_at__isnull=True)
                | Q(sentiment_label="")
            )

        articles = list(articles_query.order_by("id")[:limit])

        if not articles:
            self.stdout.write(
                self.style.WARNING(
                    "No articles need sentiment analysis for the "
                    "specified filters."
                )
            )
            return

        self.stdout.write(
            f"Preparing to analyze {len(articles)} article(s) "
            f"using {MODEL_NAME}..."
        )

        try:
            tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            model = AutoModelForSequenceClassification.from_pretrained(
                MODEL_NAME
            )
            # CPU is a reliable starting point across Mac hardware.
            device = torch.device("cpu")
            model.to(device)
            model.eval()
        except Exception as exc:
            raise CommandError(
                "Could not load FinBERT. Check your internet connection, "
                "package installation, and Hugging Face model access. "
                f"Details: {type(exc).__name__}: {exc}"
            ) from exc

        configured_labels = getattr(model.config, "id2label", {}) or {}
        label_map = {
            int(index): str(label).lower()
            for index, label in configured_labels.items()
        }

        valid_labels = {"positive", "negative", "neutral"}
        if not all(label_map.get(i) in valid_labels for i in range(3)):
            label_map = FALLBACK_LABELS

        processed = 0
        failed = 0

        for start in range(0, len(articles), BATCH_SIZE):
            batch = articles[start : start + BATCH_SIZE]
            texts = []

            for article in batch:
                title = (article.title or "").strip()
                summary = (article.summary or "").strip()

                # Yahoo Finance frequently provides a title but no summary.
                text = f"{title}. {summary}".strip() if summary else title
                texts.append(text[:12000])

            valid_positions = [
                index for index, text in enumerate(texts) if text.strip()
            ]

            for index, article in enumerate(batch):
                if index not in valid_positions:
                    failed += 1
                    self.stderr.write(
                        f"Skipped article {article.id}: no text available."
                    )

            if not valid_positions:
                continue

            valid_texts = [texts[index] for index in valid_positions]

            try:
                encoded = tokenizer(
                    valid_texts,
                    padding=True,
                    truncation=True,
                    max_length=MAX_SEQUENCE_LENGTH,
                    return_tensors="pt",
                )
                encoded = {
                    name: tensor.to(device)
                    for name, tensor in encoded.items()
                }

                with torch.inference_mode():
                    logits = model(**encoded).logits
                    probabilities = torch.softmax(
                        logits, dim=1
                    ).cpu().tolist()

                for local_index, row in enumerate(probabilities):
                    article = batch[valid_positions[local_index]]

                    probability_by_label = {
                        label_map[index]: float(row[index])
                        for index in range(len(row))
                    }

                    positive = probability_by_label["positive"]
                    neutral = probability_by_label["neutral"]
                    negative = probability_by_label["negative"]

                    label = max(
                        probability_by_label,
                        key=probability_by_label.get,
                    )

                    article.sentiment_label = label
                    article.sentiment_positive_prob = round(positive, 6)
                    article.sentiment_neutral_prob = round(neutral, 6)
                    article.sentiment_negative_prob = round(negative, 6)
                    article.sentiment_score = round(
                        positive - negative, 6
                    )
                    article.sentiment_model = MODEL_NAME
                    article.sentiment_analyzed_at = timezone.now()

                    article.save(update_fields=SENTIMENT_FIELDS)
                    processed += 1

                    self.stdout.write(
                        f"[{processed}/{len(articles)}] "
                        f"{article.stock.symbol}: {label} "
                        f"(score={article.sentiment_score:+.4f}) "
                        f"{article.title[:90]}"
                    )

            except Exception as exc:
                failed += len(valid_positions)
                self.stderr.write(
                    self.style.WARNING(
                        f"Batch starting at article {batch[0].id} failed: "
                        f"{type(exc).__name__}: {exc}"
                    )
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS("Sentiment analysis run finished.")
        )
        self.stdout.write(f"Successfully analyzed: {processed}")
        self.stdout.write(f"Skipped or failed: {failed}")
        self.stdout.write(
            "Stored sentiment results remain available in PostgreSQL."
        )
