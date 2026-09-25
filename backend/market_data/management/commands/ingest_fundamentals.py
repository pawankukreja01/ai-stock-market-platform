from decimal import Decimal, InvalidOperation

import yfinance as yf

from django.core.management.base import BaseCommand, CommandError

from market_data.models import Fundamental
from stocks.models import Stock


class Command(BaseCommand):
    help = (
        "Download annual and quarterly fundamental data "
        "from Yahoo Finance and store it in PostgreSQL."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "symbol",
            type=str,
            help="Stock symbol, e.g. AAPL",
        )

    def handle(self, *args, **options):
        symbol = options["symbol"].upper().strip()

        if not symbol:
            raise CommandError(
                "A stock symbol is required."
            )

        self.stdout.write(
            self.style.NOTICE(
                f"Downloading fundamentals for {symbol}..."
            )
        )

        # --------------------------------------------------
        # Find stock in our database
        # --------------------------------------------------

        try:
            stock = Stock.objects.get(
                symbol=symbol
            )
        except Stock.DoesNotExist:
            raise CommandError(
                f"{symbol} does not exist in the Stock database."
            )

        # --------------------------------------------------
        # Create Yahoo Finance ticker
        # --------------------------------------------------

        try:
            ticker = yf.Ticker(symbol)

            income_statement = ticker.income_stmt
            quarterly_income = ticker.quarterly_income_stmt

            balance_sheet = ticker.balance_sheet
            quarterly_balance = ticker.quarterly_balance_sheet

            cash_flow = ticker.cashflow
            quarterly_cash_flow = ticker.quarterly_cashflow

            info = ticker.info

        except Exception as exc:
            raise CommandError(
                f"Unable to download fundamentals for "
                f"{symbol}: {exc}"
            )

        annual_count = self.process_periods(
            stock=stock,
            period_type="annual",
            income_statement=income_statement,
            balance_sheet=balance_sheet,
            cash_flow=cash_flow,
            info=info,
        )

        quarterly_count = self.process_periods(
            stock=stock,
            period_type="quarterly",
            income_statement=quarterly_income,
            balance_sheet=quarterly_balance,
            cash_flow=quarterly_cash_flow,
            info=info,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Fundamental ingestion completed for {symbol}."
            )
        )

        self.stdout.write(
            f"Annual records processed: {annual_count}"
        )

        self.stdout.write(
            f"Quarterly records processed: {quarterly_count}"
        )

    # ======================================================
    # PROCESS PERIODS
    # ======================================================

    def process_periods(
        self,
        stock,
        period_type,
        income_statement,
        balance_sheet,
        cash_flow,
        info,
    ):
        if income_statement is None:
            return 0

        if income_statement.empty:
            return 0

        processed = 0

        for period in income_statement.columns:
            try:
                period_end = period.date()
            except AttributeError:
                continue

            # --------------------------------------------------
            # Income statement
            # --------------------------------------------------

            revenue = self.get_value(
                income_statement,
                "Total Revenue",
                period,
            )

            gross_profit = self.get_value(
                income_statement,
                "Gross Profit",
                period,
            )

            operating_income = self.get_value(
                income_statement,
                "Operating Income",
                period,
            )

            net_income = self.get_value(
                income_statement,
                "Net Income",
                period,
            )

            eps = self.get_value(
                income_statement,
                "Diluted EPS",
                period,
            )

            if eps is None:
                eps = self.get_value(
                    income_statement,
                    "Basic EPS",
                    period,
                )

            # --------------------------------------------------
            # Cash flow
            # --------------------------------------------------

            free_cash_flow = self.get_value(
                cash_flow,
                "Free Cash Flow",
                period,
            )

            if free_cash_flow is None:
                operating_cash_flow = self.get_value(
                    cash_flow,
                    "Operating Cash Flow",
                    period,
                )

                capital_expenditure = self.get_value(
                    cash_flow,
                    "Capital Expenditure",
                    period,
                )

                if (
                    operating_cash_flow is not None
                    and capital_expenditure is not None
                ):
                    free_cash_flow = (
                        operating_cash_flow
                        + capital_expenditure
                    )

            # --------------------------------------------------
            # Balance sheet
            # --------------------------------------------------

            total_assets = self.get_value(
                balance_sheet,
                "Total Assets",
                period,
            )

            stockholders_equity = self.get_value(
                balance_sheet,
                "Stockholders Equity",
                period,
            )

            total_debt = self.get_value(
                balance_sheet,
                "Total Debt",
                period,
            )

            current_assets = self.get_value(
                balance_sheet,
                "Current Assets",
                period,
            )

            current_liabilities = self.get_value(
                balance_sheet,
                "Current Liabilities",
                period,
            )

            # --------------------------------------------------
            # Calculate profitability ratios
            # --------------------------------------------------

            roe = None

            if (
                net_income is not None
                and stockholders_equity
                and stockholders_equity != 0
            ):
                roe = (
                    net_income
                    / stockholders_equity
                )

            roa = None

            if (
                net_income is not None
                and total_assets
                and total_assets != 0
            ):
                roa = (
                    net_income
                    / total_assets
                )

            gross_margin = None

            if (
                gross_profit is not None
                and revenue
                and revenue != 0
            ):
                gross_margin = (
                    gross_profit
                    / revenue
                )

            operating_margin = None

            if (
                operating_income is not None
                and revenue
                and revenue != 0
            ):
                operating_margin = (
                    operating_income
                    / revenue
                )

            profit_margin = None

            if (
                net_income is not None
                and revenue
                and revenue != 0
            ):
                profit_margin = (
                    net_income
                    / revenue
                )

            # --------------------------------------------------
            # Financial health
            # --------------------------------------------------

            debt_to_equity = None

            if (
                total_debt is not None
                and stockholders_equity
                and stockholders_equity != 0
            ):
                debt_to_equity = (
                    total_debt
                    / stockholders_equity
                )

            current_ratio = None

            if (
                current_assets is not None
                and current_liabilities
                and current_liabilities != 0
            ):
                current_ratio = (
                    current_assets
                    / current_liabilities
                )

            # --------------------------------------------------
            # Valuation metrics
            #
            # These are generally current-market metrics,
            # so they are stored with the latest available
            # fundamental period rather than pretending they
            # are historical valuation observations.
            # --------------------------------------------------

            pe_ratio = self.safe_info_value(
                info,
                "trailingPE",
            )

            forward_pe = self.safe_info_value(
                info,
                "forwardPE",
            )

            peg_ratio = self.safe_info_value(
                info,
                "pegRatio",
            )

            price_to_sales = self.safe_info_value(
                info,
                "priceToSalesTrailing12Months",
            )

            price_to_book = self.safe_info_value(
                info,
                "priceToBook",
            )

            dividend_per_share = self.safe_info_value(
                info,
                "dividendRate",
            )

            dividend_yield = self.safe_info_value(
                info,
                "dividendYield",
            )

            # --------------------------------------------------
            # Save / update database record
            # --------------------------------------------------

            Fundamental.objects.update_or_create(
                stock=stock,
                period_end=period_end,
                period_type=period_type,
                defaults={
                    "revenue": self.to_decimal(revenue),
                    "gross_profit": self.to_decimal(
                        gross_profit
                    ),
                    "operating_income": self.to_decimal(
                        operating_income
                    ),
                    "net_income": self.to_decimal(
                        net_income
                    ),
                    "eps": self.to_decimal(eps),
                    "free_cash_flow": self.to_decimal(
                        free_cash_flow
                    ),
                    "roe": self.to_decimal(roe),
                    "roa": self.to_decimal(roa),
                    "gross_margin": self.to_decimal(
                        gross_margin
                    ),
                    "operating_margin": self.to_decimal(
                        operating_margin
                    ),
                    "profit_margin": self.to_decimal(
                        profit_margin
                    ),
                    "debt_to_equity": self.to_decimal(
                        debt_to_equity
                    ),
                    "current_ratio": self.to_decimal(
                        current_ratio
                    ),
                    "pe_ratio": self.to_decimal(
                        pe_ratio
                    ),
                    "forward_pe": self.to_decimal(
                        forward_pe
                    ),
                    "peg_ratio": self.to_decimal(
                        peg_ratio
                    ),
                    "price_to_sales": self.to_decimal(
                        price_to_sales
                    ),
                    "price_to_book": self.to_decimal(
                        price_to_book
                    ),
                    "dividend_per_share": self.to_decimal(
                        dividend_per_share
                    ),
                    "dividend_yield": self.to_decimal(
                        dividend_yield
                    ),
                },
            )

            processed += 1

        return processed

    # ======================================================
    # DATA EXTRACTION HELPERS
    # ======================================================

    @staticmethod
    def get_value(dataframe, row_name, period):
        if dataframe is None:
            return None

        if dataframe.empty:
            return None

        if row_name not in dataframe.index:
            return None

        try:
            value = dataframe.loc[
                row_name,
                period,
            ]
        except Exception:
            return None

        if value is None:
            return None

        try:
            if value != value:
                return None
        except Exception:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def safe_info_value(info, key):
        try:
            value = info.get(key)

            if value is None:
                return None

            if isinstance(value, float):
                if value != value:
                    return None

            return float(value)

        except (
            TypeError,
            ValueError,
            AttributeError,
        ):
            return None

    @staticmethod
    def to_decimal(value):
        if value is None:
            return None

        try:
            return Decimal(
                str(value)
            )
        except (
            InvalidOperation,
            ValueError,
            TypeError,
        ):
            return None