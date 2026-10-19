<template>
  <main class="screener-page">
    <header class="page-heading">
      <div>
        <div class="eyebrow">RESEARCH WORKSPACE</div>
        <h1>Stock Screener</h1>
        <p class="subtitle">
          Find stocks by valuation, fundamentals, technical signals, risk and news sentiment.
        </p>
      </div>
      <div class="data-status">
        <span class="status-dot"></span>
        Connected to screener API
      </div>
    </header>

    <section class="summary-grid" aria-label="Screener summary">
      <article class="summary-card">
        <span class="summary-label">Matching stocks</span>
        <strong>{{ formatInteger(result.count) }}</strong>
        <small>Stocks matching the current filters</small>
      </article>
      <article class="summary-card">
        <span class="summary-label">Current page</span>
        <strong>
          {{ result.total_pages ? result.page : 0 }}
          <span class="muted">/ {{ result.total_pages }}</span>
        </strong>
        <small>{{ result.page_size }} rows per page</small>
      </article>
      <article class="summary-card">
        <span class="summary-label">Sort order</span>
        <strong class="sort-summary">{{ sortLabel }}</strong>
        <small>{{ sortOrder === "asc" ? "Ascending" : "Descending" }}</small>
      </article>
    </section>

    <section class="filters-panel">
      <div class="panel-heading">
        <div>
          <h2>Screening criteria</h2>
          <p>Leave a field empty to ignore that criterion.</p>
        </div>
        <button
          class="text-button"
          type="button"
          :disabled="loading"
          @click="clearFilters"
        >
          Clear all
        </button>
      </div>

      <form @submit.prevent="applyFilters">
        <div class="filter-section">
          <h3>Company and market</h3>
          <div class="filter-grid">
            <label class="field field-wide">
              <span>Search</span>
              <input
                v-model.trim="filters.search"
                type="search"
                placeholder="Symbol, company, sector…"
              />
            </label>

            <label class="field">
              <span>Sector</span>
              <input
                v-model.trim="filters.sector"
                type="text"
                placeholder="e.g. Technology"
              />
            </label>

            <label class="field">
              <span>Exchange</span>
              <input
                v-model.trim="filters.exchange"
                type="text"
                placeholder="e.g. NASDAQ"
              />
            </label>

            <label class="field">
              <span>Fundamental period</span>
              <select v-model="filters.period_type">
                <option value="">Latest available</option>
                <option value="annual">Annual</option>
                <option value="quarterly">Quarterly</option>
              </select>
            </label>

            <label class="field">
              <span>Minimum price (USD)</span>
              <input
                v-model="filters.min_price"
                type="number"
                min="0"
                step="any"
                placeholder="0"
              />
            </label>

            <label class="field">
              <span>Maximum price (USD)</span>
              <input
                v-model="filters.max_price"
                type="number"
                min="0"
                step="any"
                placeholder="No limit"
              />
            </label>
          </div>
        </div>

        <div class="filter-section">
          <h3>Fundamentals and valuation</h3>
          <div class="filter-grid">
            <label class="field">
              <span>Minimum P/E</span>
              <input
                v-model="filters.min_pe_ratio"
                type="number"
                step="any"
                placeholder="No minimum"
              />
            </label>

            <label class="field">
              <span>Maximum P/E</span>
              <input
                v-model="filters.max_pe_ratio"
                type="number"
                step="any"
                placeholder="No maximum"
              />
            </label>

            <label class="field">
              <span>Minimum ROE (%)</span>
              <input
                v-model="filters.min_roe"
                type="number"
                step="any"
                placeholder="e.g. 10"
              />
            </label>

            <label class="field">
              <span>Maximum ROE (%)</span>
              <input
                v-model="filters.max_roe"
                type="number"
                step="any"
                placeholder="e.g. 30"
              />
            </label>

            <label class="field">
              <span>Minimum profit margin (%)</span>
              <input
                v-model="filters.min_profit_margin"
                type="number"
                step="any"
                placeholder="e.g. 10"
              />
            </label>

            <label class="field">
              <span>Maximum profit margin (%)</span>
              <input
                v-model="filters.max_profit_margin"
                type="number"
                step="any"
                placeholder="e.g. 30"
              />
            </label>

            <label class="field">
              <span>Maximum debt / equity</span>
              <input
                v-model="filters.max_debt_to_equity"
                type="number"
                min="0"
                step="any"
                placeholder="No maximum"
              />
            </label>

            <label class="field">
              <span>Minimum dividend yield (%)</span>
              <input
                v-model="filters.min_dividend_yield"
                type="number"
                min="0"
                step="any"
                placeholder="e.g. 1"
              />
            </label>

            <label class="field">
              <span>Maximum dividend yield (%)</span>
              <input
                v-model="filters.max_dividend_yield"
                type="number"
                min="0"
                step="any"
                placeholder="e.g. 5"
              />
            </label>
          </div>
        </div>

        <div class="filter-section">
          <h3>Technical signals, risk and sentiment</h3>
          <div class="filter-grid">
            <label class="field">
              <span>Minimum RSI (14)</span>
              <input
                v-model="filters.min_rsi_14"
                type="number"
                min="0"
                max="100"
                step="any"
                placeholder="0"
              />
            </label>

            <label class="field">
              <span>Maximum RSI (14)</span>
              <input
                v-model="filters.max_rsi_14"
                type="number"
                min="0"
                max="100"
                step="any"
                placeholder="100"
              />
            </label>

            <label class="field">
              <span>Minimum 20-day return (%)</span>
              <input
                v-model="filters.min_return_20d"
                type="number"
                step="any"
                placeholder="e.g. 0"
              />
            </label>

            <label class="field">
              <span>Maximum 20-day return (%)</span>
              <input
                v-model="filters.max_return_20d"
                type="number"
                step="any"
                placeholder="e.g. 10"
              />
            </label>

            <label class="field">
              <span>Maximum 20-day volatility (%)</span>
              <input
                v-model="filters.max_volatility_20d"
                type="number"
                min="0"
                step="any"
                placeholder="e.g. 30"
              />
            </label>

            <label class="field">
              <span>Maximum 60-day volatility (%)</span>
              <input
                v-model="filters.max_volatility_60d"
                type="number"
                min="0"
                step="any"
                placeholder="e.g. 40"
              />
            </label>

            <label class="field">
              <span>Maximum 252-day drawdown (%)</span>
              <input
                v-model="filters.max_drawdown_252d"
                type="number"
                min="0"
                step="any"
                placeholder="e.g. 25"
              />
            </label>

            <label class="field">
              <span>Minimum sentiment score</span>
              <input
                v-model="filters.min_sentiment_score"
                type="number"
                min="-1"
                max="1"
                step="any"
                placeholder="-1 to 1"
              />
            </label>

            <label class="field">
              <span>Maximum sentiment score</span>
              <input
                v-model="filters.max_sentiment_score"
                type="number"
                min="-1"
                max="1"
                step="any"
                placeholder="-1 to 1"
              />
            </label>
          </div>

          <p class="field-hint">
            Returns, volatility, drawdown, ROE and profit margin are entered
            as percentages. Sentiment uses a score from -1 to 1.
            ROE, price and sentiment filters need data to be available.
          </p>
        </div>

        <div class="filter-footer">
          <div class="sort-controls">
            <label class="field compact-field">
              <span>Sort by</span>
              <select v-model="sortBy">
                <option value="symbol">Symbol</option>
                <option value="company_name">Company</option>
                <option value="price">Price</option>
                <option value="pe_ratio">P/E ratio</option>
                <option value="roe">ROE</option>
                <option value="profit_margin">Profit margin</option>
                <option value="dividend_yield">Dividend yield</option>
                <option value="rsi_14">RSI (14)</option>
                <option value="return_20d">20-day return</option>
                <option value="volatility_20d">20-day volatility</option>
                <option value="volatility_60d">60-day volatility</option>
                <option value="max_drawdown_252d">252-day drawdown</option>
                <option value="sentiment_score">Sentiment</option>
              </select>
            </label>

            <label class="field compact-field">
              <span>Order</span>
              <select v-model="sortOrder">
                <option value="asc">Ascending</option>
                <option value="desc">Descending</option>
              </select>
            </label>

            <label class="field compact-field page-size-field">
              <span>Rows per page</span>
              <select v-model.number="pageSize">
                <option :value="10">10</option>
                <option :value="20">20</option>
                <option :value="50">50</option>
                <option :value="100">100</option>
              </select>
            </label>
          </div>

          <button
            class="primary-button"
            type="submit"
            :disabled="loading"
          >
            {{ loading ? "Screening…" : "Apply filters" }}
          </button>
        </div>
      </form>
    </section>

    <section class="results-panel">
      <div class="panel-heading results-heading">
        <div>
          <h2>Screening results</h2>
          <p v-if="result.count">
            Showing {{ firstResult }}–{{ lastResult }}
            of {{ result.count }} matching stocks
          </p>
          <p v-else>Stocks matching your criteria will appear here.</p>
        </div>

        <button
          class="secondary-button"
          type="button"
          :disabled="loading"
          @click="fetchResults"
        >
          {{ loading ? "Refreshing…" : "Refresh results" }}
        </button>
      </div>

      <div v-if="loading" class="state-message">
        <span class="loader"></span>
        <span>Loading screened stocks…</span>
      </div>

      <div v-else-if="error" class="state-message state-error">
        <div>
          <strong>Could not load screener results</strong>
          <p>{{ error }}</p>
        </div>
        <button
          class="secondary-button"
          type="button"
          @click="fetchResults"
        >
          Try again
        </button>
      </div>

      <div
        v-else-if="!result.results.length"
        class="state-message empty-state"
      >
        <div class="empty-icon">⌕</div>
        <strong>No stocks match these filters</strong>
        <p>Try relaxing one or more criteria, or clear all filters.</p>
        <button
          class="secondary-button"
          type="button"
          @click="clearFilters"
        >
          Clear filters
        </button>
      </div>

      <div v-else class="table-scroll">
        <table class="results-table">
          <thead>
            <tr>
              <th
                v-for="column in tableColumns"
                :key="column.key"
                class="sortable-header"
                :aria-sort="ariaSortFor(column.key)"
                :class="{ 'stock-header': column.key === 'symbol' }"
              >
                <button
                  type="button"
                  class="sort-header-button"
                  @click="setSort(column.key)"
                  :title="`Sort by ${column.label}`"
                >
                  <span>{{ column.label }}</span>
                  <span class="sort-indicator" aria-hidden="true">
                    {{ sortIndicator(column.key) }}
                  </span>
                </button>
              </th>
            </tr>
          </thead>

          <tbody>
            <tr
              v-for="stock in result.results"
              :key="stock.symbol"
            >
              <td class="stock-cell">
                <strong>{{ stock.symbol }}</strong>
                <span>{{ stock.company_name || "Company name unavailable" }}</span>
                <small>
                  {{ stock.sector || "Sector unavailable" }}
                  <template v-if="stock.exchange">
                    · {{ stock.exchange }}
                  </template>
                </small>
              </td>

              <td class="numeric-cell">
                <strong>{{ formatPrice(stock.price) }}</strong>
                <small>{{ stock.price_date || "Date unavailable" }}</small>
              </td>

              <td>{{ formatMultiple(stock.pe_ratio) }}</td>
              <td>{{ formatRatioPercent(stock.roe) }}</td>
              <td>{{ formatRatioPercent(stock.profit_margin) }}</td>
              <td>{{ formatDividendYield(stock.dividend_yield) }}</td>

              <td :class="toneClass(stock.return_20d)">
                {{ formatDecimalPercent(stock.return_20d) }}
              </td>

              <td>{{ formatFixed(stock.rsi_14, 1) }}</td>
              <td>{{ formatDecimalPercent(stock.volatility_20d) }}</td>
              <td>{{ formatDecimalPercent(stock.max_drawdown_252d) }}</td>

              <td :class="toneClass(stock.sentiment_score)">
                <span>{{ formatFixed(stock.sentiment_score, 3) }}</span>
                <small>{{ stock.sentiment_articles }} articles</small>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <footer
        class="pagination-row"
        v-if="!loading && !error"
      >
        <span>
          Page {{ result.total_pages ? result.page : 0 }}
          of {{ result.total_pages }}
        </span>

        <div class="pagination-buttons">
          <button
            class="secondary-button"
            type="button"
            :disabled="result.page <= 1 || loading || !result.total_pages"
            @click="changePage(result.page - 1)"
          >
            Previous
          </button>

          <button
            class="secondary-button"
            type="button"
            :disabled="
              result.page >= result.total_pages ||
              loading ||
              !result.total_pages
            "
            @click="changePage(result.page + 1)"
          >
            Next
          </button>
        </div>
      </footer>
    </section>

    <p class="disclaimer">
      Screener results are based on data currently stored in this platform.
      Missing metrics are shown as unavailable. Screening criteria are
      research tools, not personalised investment advice.
    </p>
  </main>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { getStockScreener } from "../services/api";

const defaultFilters = () => ({
  search: "",
  sector: "",
  exchange: "",
  period_type: "",
  min_price: "",
  max_price: "",
  min_pe_ratio: "",
  max_pe_ratio: "",
  min_roe: "",
  max_roe: "",
  min_profit_margin: "",
  max_profit_margin: "",
  max_debt_to_equity: "",
  min_dividend_yield: "",
  max_dividend_yield: "",
  min_rsi_14: "",
  max_rsi_14: "",
  min_return_20d: "",
  max_return_20d: "",
  max_volatility_20d: "",
  max_volatility_60d: "",
  max_drawdown_252d: "",
  min_sentiment_score: "",
  max_sentiment_score: "",
});

const filters = reactive(defaultFilters());

const sortBy = ref("symbol");
const sortOrder = ref("asc");
const page = ref(1);
const pageSize = ref(20);
const loading = ref(false);
const error = ref("");

const result = ref({
  count: 0,
  page: 1,
  page_size: 20,
  total_pages: 0,
  results: [],
});

const sortLabels = {
  symbol: "Symbol",
  company_name: "Company",
  price: "Price",
  pe_ratio: "P/E ratio",
  roe: "ROE",
  profit_margin: "Profit margin",
  dividend_yield: "Dividend yield",
  rsi_14: "RSI (14)",
  return_20d: "20-day return",
  volatility_20d: "20-day volatility",
  volatility_60d: "60-day volatility",
  max_drawdown_252d: "252-day drawdown",
  sentiment_score: "Sentiment",
};

const tableColumns = [
  { key: "symbol", label: "Stock" },
  { key: "price", label: "Price" },
  { key: "pe_ratio", label: "P/E" },
  { key: "roe", label: "ROE" },
  { key: "profit_margin", label: "Profit margin" },
  { key: "dividend_yield", label: "Dividend yield" },
  { key: "return_20d", label: "20D return" },
  { key: "rsi_14", label: "RSI" },
  { key: "volatility_20d", label: "20D volatility" },
  { key: "max_drawdown_252d", label: "252D drawdown" },
  { key: "sentiment_score", label: "Sentiment" },
];

const sortLabel = computed(
  () => sortLabels[sortBy.value] || sortBy.value
);

const firstResult = computed(() =>
  result.value.count
    ? (result.value.page - 1) * result.value.page_size + 1
    : 0
);

const lastResult = computed(() =>
  Math.min(
    result.value.page * result.value.page_size,
    result.value.count
  )
);

const percentageInputFields = new Set([
  "min_roe",
  "max_roe",
  "min_profit_margin",
  "max_profit_margin",
  "min_return_20d",
  "max_return_20d",
  "max_volatility_20d",
  "max_volatility_60d",
  "max_drawdown_252d",
]);

async function fetchResults() {
  loading.value = true;
  error.value = "";

  const params = {
    page: page.value,
    page_size: pageSize.value,
    sort_by: sortBy.value,
    sort_order: sortOrder.value,
  };

  for (const [key, rawValue] of Object.entries(filters)) {
    if (typeof rawValue !== "string" || rawValue.trim() === "") {
      continue;
    }

    if (
      key === "search" ||
      key === "sector" ||
      key === "exchange" ||
      key === "period_type"
    ) {
      params[key] = rawValue.trim();
      continue;
    }

    const numericValue = Number(rawValue);

    if (!Number.isFinite(numericValue)) {
      continue;
    }

    // The API stores ratio metrics as decimals.
    // Convert percentage inputs such as 12.5 to 0.125.
    params[key] = percentageInputFields.has(key)
      ? numericValue / 100
      : numericValue;
  }

  try {
    result.value = await getStockScreener(params);
  } catch (requestError) {
    error.value =
      requestError?.response?.data?.error ||
      requestError?.response?.data?.detail ||
      requestError?.message ||
      "An unexpected error occurred while contacting the API.";

    result.value = {
      count: 0,
      page: page.value,
      page_size: pageSize.value,
      total_pages: 0,
      results: [],
    };
  } finally {
    loading.value = false;
  }
}

function applyFilters() {
  page.value = 1;
  fetchResults();
}

function clearFilters() {
  Object.assign(filters, defaultFilters());

  sortBy.value = "symbol";
  sortOrder.value = "asc";
  page.value = 1;
  pageSize.value = 20;

  fetchResults();
}

function changePage(nextPage) {
  if (
    nextPage < 1 ||
    (result.value.total_pages && nextPage > result.value.total_pages)
  ) {
    return;
  }

  page.value = nextPage;
  fetchResults();
}

function setSort(field) {
  if (sortBy.value === field) {
    sortOrder.value = sortOrder.value === "asc" ? "desc" : "asc";
  } else {
    sortBy.value = field;
    sortOrder.value = "asc";
  }

  page.value = 1;
  fetchResults();
}

function sortIndicator(field) {
  if (sortBy.value !== field) return "↕";
  return sortOrder.value === "asc" ? "↑" : "↓";
}

function ariaSortFor(field) {
  if (sortBy.value !== field) return "none";
  return sortOrder.value === "asc" ? "ascending" : "descending";
}

function formatInteger(value) {
  return Number(value || 0).toLocaleString();
}

function formatPrice(value) {
  if (value == null) return "—";

  return Number(value).toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatFixed(value, digits = 2) {
  if (value == null || !Number.isFinite(Number(value))) {
    return "—";
  }

  return Number(value).toFixed(digits);
}

function formatMultiple(value) {
  return value == null ? "—" : `${formatFixed(value, 2)}×`;
}

function formatDecimalPercent(value) {
  return value == null
    ? "—"
    : `${(Number(value) * 100).toFixed(2)}%`;
}

function formatRatioPercent(value) {
  if (value == null) return "—";

  const numeric = Number(value);
  const percent = Math.abs(numeric) <= 1
    ? numeric * 100
    : numeric;

  return `${percent.toFixed(2)}%`;
}

function formatDividendYield(value) {
  return value == null ? "—" : `${Number(value).toFixed(2)}%`;
}

function toneClass(value) {
  if (value == null || !Number.isFinite(Number(value))) {
    return "";
  }

  if (Number(value) > 0) return "positive-value";
  if (Number(value) < 0) return "negative-value";

  return "neutral-value";
}

onMounted(fetchResults);
</script>

<style scoped>
.screener-page {
  display: flex;
  flex-direction: column;
  gap: 22px;
  max-width: 1600px;
  margin: 0 auto;
  padding: 28px clamp(16px, 3vw, 36px) 40px;
  color: #111827;
}

.page-heading,
.panel-heading,
.filter-footer,
.sort-controls,
.pagination-row,
.pagination-buttons {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.page-heading {
  align-items: flex-start;
}

.eyebrow {
  margin-bottom: 7px;
  color: #64748b;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .13em;
}

h1 {
  margin: 0;
  font-size: clamp(27px, 3vw, 36px);
  letter-spacing: -.04em;
}

.subtitle,
.panel-heading p {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 14px;
  line-height: 1.5;
}

.data-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  border: 1px solid #dbe4ee;
  border-radius: 999px;
  padding: 9px 12px;
  background: #fff;
  color: #475569;
  font-size: 12px;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #16a34a;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.summary-card,
.filters-panel,
.results-panel {
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 3px 12px rgb(15 23 42 / 3%);
}

.summary-card {
  display: flex;
  flex-direction: column;
  min-height: 122px;
  padding: 18px 20px;
  gap: 9px;
}

.summary-label {
  color: #64748b;
  font-size: 12px;
  font-weight: 650;
}

.summary-card strong {
  font-size: 26px;
  letter-spacing: -.03em;
}

.summary-card small,
.muted {
  color: #94a3b8;
  font-size: 12px;
  font-weight: 500;
}

.sort-summary {
  font-size: 21px !important;
}

.filters-panel,
.results-panel {
  overflow: hidden;
}

.panel-heading {
  align-items: flex-start;
  padding: 20px 22px;
  border-bottom: 1px solid #eef2f7;
}

h2 {
  margin: 0;
  font-size: 18px;
  letter-spacing: -.02em;
}

.text-button {
  border: 0;
  background: transparent;
  padding: 7px 2px;
  color: #475569;
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 650;
}

.text-button:hover {
  color: #0f172a;
}

.text-button:disabled,
button:disabled {
  cursor: not-allowed;
  opacity: .48;
}

.filter-section {
  padding: 20px 22px;
  border-bottom: 1px solid #eef2f7;
}

.filter-section h3 {
  margin: 0 0 15px;
  color: #334155;
  font-size: 13px;
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
}

.field span {
  color: #475569;
  font-size: 12px;
  font-weight: 650;
}

.field input,
.field select {
  width: 100%;
  min-width: 0;
  height: 39px;
  border: 1px solid #dbe3ed;
  border-radius: 8px;
  outline: none;
  padding: 0 10px;
  background: #fff;
  color: #0f172a;
  font: inherit;
  font-size: 13px;
}

.field input:focus,
.field select:focus {
  border-color: #64748b;
  box-shadow: 0 0 0 3px rgb(100 116 139 / 12%);
}

.field input::placeholder {
  color: #a0aab8;
}

.field-wide {
  grid-column: span 2;
}

.field-hint {
  margin: 14px 0 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.filter-footer {
  flex-wrap: wrap;
  padding: 18px 22px;
}

.sort-controls {
  justify-content: flex-start;
  flex-wrap: wrap;
}

.compact-field {
  min-width: 140px;
}

.page-size-field {
  min-width: 120px;
}

.primary-button,
.secondary-button {
  min-height: 38px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 0 13px;
  background: #fff;
  color: #334155;
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

.primary-button {
  min-height: 41px;
  border-color: #172554;
  padding: 0 18px;
  background: #172554;
  color: #fff;
}

.primary-button:hover:not(:disabled) {
  background: #1e3a8a;
}

.secondary-button:hover:not(:disabled) {
  background: #f8fafc;
}

.results-heading {
  align-items: center;
}

.results-heading .secondary-button {
  flex-shrink: 0;
}

.table-scroll {
  width: 100%;
  overflow-x: auto;
}

.results-table {
  width: 100%;
  border-collapse: collapse;
  white-space: nowrap;
  font-size: 13px;
}

.results-table th {
  padding: 0;
  background: #f8fafc;
  color: #64748b;
  font-size: 11px;
  font-weight: 750;
  text-align: right;
}

.results-table th.stock-header {
  min-width: 240px;
  text-align: left;
}

.sort-header-button {
  width: 100%;
  min-height: 42px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 7px;
  border: 0;
  padding: 12px 14px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font: inherit;
  font-size: inherit;
  font-weight: inherit;
  text-align: right;
  white-space: nowrap;
}

.stock-header .sort-header-button {
  justify-content: flex-start;
  padding-left: 22px;
  text-align: left;
}

.sort-header-button:hover {
  background: #eef2f7;
  color: #0f172a;
}

.sort-header-button:focus-visible {
  outline: 2px solid #64748b;
  outline-offset: -3px;
}

.sort-indicator {
  width: 12px;
  color: #94a3b8;
  font-size: 13px;
}

.results-table td {
  border-top: 1px solid #eef2f7;
  padding: 14px;
  color: #334155;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.results-table td:first-child {
  padding-left: 22px;
  text-align: left;
}

.results-table tbody tr:hover {
  background: #fbfdff;
}

.stock-cell {
  min-width: 250px;
  white-space: normal;
}

.stock-cell strong,
.stock-cell span,
.stock-cell small {
  display: block;
}

.stock-cell strong {
  color: #0f172a;
  font-size: 13px;
}

.stock-cell span {
  margin-top: 3px;
  color: #475569;
  font-size: 12px;
}

.stock-cell small,
.numeric-cell small,
.results-table td small {
  display: block;
  margin-top: 5px;
  color: #94a3b8;
  font-size: 11px;
}

.numeric-cell strong {
  color: #0f172a;
}

.positive-value {
  color: #15803d !important;
  font-weight: 700;
}

.negative-value {
  color: #b91c1c !important;
  font-weight: 700;
}

.neutral-value {
  color: #475569 !important;
}

.state-message {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-height: 155px;
  padding: 28px;
  color: #64748b;
  font-size: 13px;
}

.state-error {
  justify-content: space-between;
  color: #b91c1c;
}

.state-error p {
  margin: 6px 0 0;
  color: #64748b;
}

.empty-state {
  flex-direction: column;
  text-align: center;
  gap: 8px;
}

.empty-state strong {
  color: #334155;
  font-size: 15px;
}

.empty-state p {
  margin: 0 0 8px;
}

.empty-icon {
  color: #94a3b8;
  font-size: 34px;
}

.loader {
  width: 17px;
  height: 17px;
  border: 2px solid #cbd5e1;
  border-top-color: #334155;
  border-radius: 50%;
  animation: spin .7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.pagination-row {
  padding: 16px 22px;
  border-top: 1px solid #eef2f7;
  color: #64748b;
  font-size: 12px;
}

.pagination-buttons {
  gap: 8px;
}

.disclaimer {
  margin: -5px 0 0;
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 1050px) {
  .filter-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .screener-page {
    padding: 20px 12px 30px;
    gap: 16px;
  }

  .page-heading {
    flex-direction: column;
  }

  .data-status {
    align-self: flex-start;
  }

  .summary-grid {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .summary-card {
    min-height: 100px;
  }

  .filter-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .field-wide {
    grid-column: span 2;
  }

  .panel-heading,
  .filter-section,
  .filter-footer {
    padding-left: 15px;
    padding-right: 15px;
  }

  .panel-heading {
    gap: 10px;
  }

  .results-heading {
    align-items: flex-start;
  }

  .filter-footer {
    align-items: stretch;
  }

  .sort-controls {
    width: 100%;
  }

  .compact-field {
    flex: 1;
    min-width: 110px;
  }

  .primary-button {
    width: 100%;
  }

  .pagination-row {
    padding: 14px 15px;
  }
}

@media (max-width: 420px) {
  .filter-grid {
    grid-template-columns: 1fr;
  }

  .field-wide {
    grid-column: auto;
  }

  .panel-heading {
    flex-direction: column;
  }

  .results-heading {
    flex-direction: row;
  }
}
</style>