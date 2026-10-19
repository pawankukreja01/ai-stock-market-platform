
<template>
  <div class="portfolio-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">INVESTMENT WORKSPACE</p>
        <h1>Portfolio Analysis</h1>
        <p class="subtitle">
          Track holdings, analyse performance and understand historical risk.
        </p>
      </div>

      <button
        class="button secondary"
        type="button"
        :disabled="loadingPortfolios || loadingPortfolio"
        @click="loadSelectedPortfolio"
      >
        Refresh
      </button>
    </header>

    <div v-if="pageError" class="alert error-alert">
      <strong>Something went wrong</strong>
      <p>{{ pageError }}</p>
    </div>

    <section class="panel portfolio-toolbar">
      <div class="toolbar-title">
        <div>
          <h2>Your portfolios</h2>
          <p>Select a portfolio or create a new one.</p>
        </div>

        <button
          v-if="currentPortfolio"
          class="button danger-outline"
          type="button"
          :disabled="savingPortfolio"
          @click="removePortfolio"
        >
          Delete portfolio
        </button>
      </div>

      <div class="toolbar-grid">
        <label class="field">
          <span>Selected portfolio</span>
          <select
            v-model="selectedPortfolioId"
            :disabled="loadingPortfolios || !portfolios.length"
            @change="loadSelectedPortfolio"
          >
            <option value="" disabled>Select a portfolio</option>
            <option
              v-for="portfolio in portfolios"
              :key="portfolio.id"
              :value="String(portfolio.id)"
            >
              {{ portfolio.name }}
            </option>
          </select>
        </label>

        <form class="create-form" @submit.prevent="createNewPortfolio">
          <label class="field">
            <span>New portfolio name</span>
            <input
              v-model.trim="portfolioForm.name"
              type="text"
              maxlength="120"
              placeholder="e.g. Long-term investments"
              required
            />
          </label>

          <label class="field">
            <span>Description (optional)</span>
            <input
              v-model.trim="portfolioForm.description"
              type="text"
              placeholder="Investment strategy"
            />
          </label>

          <button
            class="button primary"
            type="submit"
            :disabled="savingPortfolio || !portfolioForm.name"
          >
            {{ savingPortfolio ? "Creating…" : "Create portfolio" }}
          </button>
        </form>
      </div>
    </section>

    <div v-if="loadingPortfolios || loadingPortfolio" class="loading-state">
      Loading portfolio data…
    </div>

    <template v-else-if="currentPortfolio">
      <section class="summary-grid">
        <article class="summary-card">
          <span class="summary-label">Market value</span>
          <strong>{{ money(summary.market_value) }}</strong>
          <small>
            {{ summary.priced_holdings }} priced holdings
          </small>
        </article>

        <article class="summary-card">
          <span class="summary-label">Cost basis</span>
          <strong>{{ money(summary.total_cost_basis) }}</strong>
          <small>
            {{ summary.holdings_count }} total holdings
          </small>
        </article>

        <article class="summary-card">
          <span class="summary-label">Unrealised profit / loss</span>
          <strong :class="toneClass(summary.unrealized_profit_loss)">
            {{ signedMoney(summary.unrealized_profit_loss) }}
          </strong>
          <small :class="toneClass(summary.unrealized_return_pct)">
            {{ signedPercent(summary.unrealized_return_pct) }}
          </small>
        </article>

        <article class="summary-card">
          <span class="summary-label">Data as of</span>
          <strong class="date-value">
            {{ formatDate(summary.data_as_of) }}
          </strong>
          <small>
            {{ summary.unpriced_holdings }} holdings without prices
          </small>
        </article>
      </section>

      <section class="panel holdings-panel">
        <div class="panel-heading">
          <div>
            <h2>Holdings</h2>
            <p>
              Add investments or edit the quantity and purchase price
              you entered.
            </p>
          </div>
        </div>

        <form class="add-holding-form" @submit.prevent="addHolding">
          <label class="field">
            <span>Stock</span>
            <select v-model="holdingForm.stock_symbol" required>
              <option value="" disabled>Select stock</option>
              <option
                v-for="stock in stocks"
                :key="stock.id"
                :value="stock.symbol"
              >
                {{ stock.symbol }} — {{ stock.company_name }}
              </option>
            </select>
          </label>

          <label class="field">
            <span>Quantity</span>
            <input
              v-model="holdingForm.quantity"
              type="number"
              min="0.000001"
              step="any"
              placeholder="10"
              required
            />
          </label>

          <label class="field">
            <span>Purchase price (USD)</span>
            <input
              v-model="holdingForm.purchase_price"
              type="number"
              min="0.0001"
              step="any"
              placeholder="200.00"
              required
            />
          </label>

          <label class="field">
            <span>Purchase date</span>
            <input
              v-model="holdingForm.purchase_date"
              type="date"
            />
          </label>

          <button
            class="button primary add-button"
            type="submit"
            :disabled="savingHolding || !holdingForm.stock_symbol"
          >
            {{ savingHolding ? "Adding…" : "Add holding" }}
          </button>
        </form>

        <p class="helper-text">
          Values use USD. Prices come from your latest stored market data.
          A purchase price is the price you enter, not a verified brokerage transaction.
        </p>

        <div v-if="holdingError" class="inline-error">
          {{ holdingError }}
        </div>

        <div v-if="!currentPortfolio.holdings.length" class="empty-state">
          <h3>No holdings yet</h3>
          <p>Add a stock using the form above to start tracking your portfolio.</p>
        </div>

        <div v-else class="table-scroll">
          <table class="holdings-table">
            <thead>
              <tr>
                <th>Stock</th>
                <th>Quantity</th>
                <th>Purchase price</th>
                <th>Current price</th>
                <th>Market value</th>
                <th>Cost basis</th>
                <th>Profit / loss</th>
                <th>Return</th>
                <th>Weight</th>
                <th>Actions</th>
              </tr>
            </thead>

            <tbody>
              <tr
                v-for="holding in currentPortfolio.holdings"
                :key="holding.id"
              >
                <td class="stock-cell">
                  <strong>{{ holding.stock_symbol }}</strong>
                  <small>{{ holding.company_name }}</small>
                </td>

                <td>
                  <input
                    v-if="editingHoldingId === holding.id"
                    v-model="editForm.quantity"
                    class="edit-input"
                    type="number"
                    min="0.000001"
                    step="any"
                    aria-label="Edit quantity"
                  />
                  <span v-else>{{ number(holding.quantity, 4) }}</span>
                </td>

                <td>
                  <input
                    v-if="editingHoldingId === holding.id"
                    v-model="editForm.purchase_price"
                    class="edit-input"
                    type="number"
                    min="0.0001"
                    step="any"
                    aria-label="Edit purchase price"
                  />
                  <span v-else>{{ money(holding.purchase_price) }}</span>
                </td>

                <td>
                  <span>{{ moneyOrDash(holding.current_price) }}</span>
                  <small class="date-note">
                    {{ holding.current_price_date || "No price date" }}
                  </small>
                </td>

                <td>{{ moneyOrDash(holding.current_value) }}</td>
                <td>{{ money(holding.cost_basis) }}</td>

                <td :class="toneClass(holding.unrealized_profit_loss)">
                  {{ signedMoney(holding.unrealized_profit_loss) }}
                </td>

                <td :class="toneClass(holding.unrealized_return_pct)">
                  {{ signedPercent(holding.unrealized_return_pct) }}
                </td>

                <td>{{ plainPercent(holding.weight_pct) }}</td>

                <td class="actions-cell">
                  <template v-if="editingHoldingId === holding.id">
                    <button
                      class="mini-button save-button"
                      type="button"
                      :disabled="savingHolding"
                      @click="saveHolding(holding)"
                    >
                      Save
                    </button>
                    <button
                      class="mini-button"
                      type="button"
                      @click="cancelEdit"
                    >
                      Cancel
                    </button>
                  </template>

                  <template v-else>
                    <button
                      class="mini-button"
                      type="button"
                      @click="startEdit(holding)"
                    >
                      Edit
                    </button>
                    <button
                      class="mini-button delete-button"
                      type="button"
                      :disabled="savingHolding"
                      @click="removeHolding(holding)"
                    >
                      Remove
                    </button>
                  </template>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="panel risk-panel">
        <div class="panel-heading">
          <div>
            <h2>Historical portfolio risk</h2>
            <p>
              Estimates based on stored adjusted closing prices and
              your current share quantities.
            </p>
          </div>
        </div>

        <div v-if="loadingRisk" class="loading-state">
          Calculating historical risk…
        </div>

        <div v-else-if="riskError" class="inline-error">
          {{ riskError }}
        </div>

        <div v-else-if="risk && risk.available">
          <div class="risk-grid">
            <article class="risk-card">
              <span>Annualised volatility</span>
              <strong>
                {{ plainPercent(risk.annualized_volatility_pct) }}
              </strong>
              <small>Based on daily portfolio returns</small>
            </article>

            <article class="risk-card">
              <span>Maximum drawdown</span>
              <strong class="negative">
                {{ plainPercent(risk.max_drawdown_pct) }}
              </strong>
              <small>Largest historical peak-to-trough decline</small>
            </article>

            <article class="risk-card">
              <span>Historical period return</span>
              <strong :class="toneClass(risk.period_return_pct)">
                {{ signedPercent(risk.period_return_pct) }}
              </strong>
              <small>{{ risk.observations }} daily observations</small>
            </article>

            <article class="risk-card">
              <span>Annualised historical return</span>
              <strong :class="toneClass(risk.annualized_return_pct)">
                {{ signedPercent(risk.annualized_return_pct) }}
              </strong>
              <small>Historical estimate, not a forecast</small>
            </article>
          </div>

          <div class="risk-footnote">
            <p>
              Historical window: {{ risk.start_date }} to {{ risk.end_date }}.
            </p>
            <p>
              Included stocks: {{ risk.included_symbols.join(", ") || "None" }}.
            </p>
            <p v-if="risk.excluded_symbols?.length">
              Stocks excluded due to insufficient history:
              {{ risk.excluded_symbols.join(", ") }}.
            </p>
            <p>{{ risk.method }}</p>
          </div>
        </div>

        <div v-else class="empty-state">
          <h3>Risk estimate unavailable</h3>
          <p>
            {{ risk?.reason || "Add holdings with sufficient price history to calculate portfolio risk." }}
          </p>
        </div>
      </section>

      <p class="disclaimer">
        This page is an investment-tracking and analysis tool, not
        personalised investment advice. Unrealised profit and loss excludes
        taxes, transaction fees, dividends, currency conversion and any
        actual brokerage adjustments.
      </p>
    </template>

    <section v-else-if="!loadingPortfolios" class="panel empty-portfolio">
      <h2>Create your first portfolio</h2>
      <p>
        Give your portfolio a name above, then add holdings to begin analysis.
      </p>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";

import {
  getStocks,
  getPortfolios,
  createPortfolio,
  getPortfolio,
  updatePortfolio,
  deletePortfolio,
  createPortfolioHolding,
  updatePortfolioHolding,
  deletePortfolioHolding,
  getPortfolioAnalysis,
} from "../services/api";

const portfolios = ref([]);
const stocks = ref([]);
const selectedPortfolioId = ref("");
const currentPortfolio = ref(null);
const risk = ref(null);

const loadingPortfolios = ref(false);
const loadingPortfolio = ref(false);
const loadingRisk = ref(false);
const savingPortfolio = ref(false);
const savingHolding = ref(false);

const pageError = ref("");
const holdingError = ref("");
const riskError = ref("");

const portfolioForm = reactive({
  name: "",
  description: "",
});

const holdingForm = reactive({
  stock_symbol: "",
  quantity: "",
  purchase_price: "",
  purchase_date: "",
});

const editingHoldingId = ref(null);
const editForm = reactive({
  quantity: "",
  purchase_price: "",
  purchase_date: "",
});

const summary = computed(() => (
  currentPortfolio.value?.summary || {
    holdings_count: 0,
    priced_holdings: 0,
    unpriced_holdings: 0,
    total_cost_basis: 0,
    priced_cost_basis: 0,
    market_value: 0,
    unrealized_profit_loss: 0,
    unrealized_return_pct: null,
    data_as_of: null,
  }
));

function toList(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
}

function errorMessage(error) {
  const data = error?.response?.data;

  if (typeof data === "string") return data;
  if (data?.detail) return String(data.detail);
  if (data?.error) return String(data.error);

  if (data && typeof data === "object") {
    return Object.entries(data)
      .map(([field, messages]) => {
        const value = Array.isArray(messages)
          ? messages.join(", ")
          : String(messages);

        return `${field}: ${value}`;
      })
      .join(" | ");
  }

  return error?.message || "An unexpected error occurred.";
}

function money(value) {
  if (value == null || !Number.isFinite(Number(value))) {
    return "—";
  }

  return Number(value).toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function moneyOrDash(value) {
  return value == null ? "—" : money(value);
}

function signedMoney(value) {
  if (value == null || !Number.isFinite(Number(value))) {
    return "—";
  }

  const numeric = Number(value);
  const prefix = numeric > 0 ? "+" : numeric < 0 ? "−" : "";

  return `${prefix}${money(Math.abs(numeric))}`;
}

function plainPercent(value) {
  if (value == null || !Number.isFinite(Number(value))) {
    return "—";
  }

  return `${Number(value).toFixed(2)}%`;
}

function signedPercent(value) {
  if (value == null || !Number.isFinite(Number(value))) {
    return "—";
  }

  const numeric = Number(value);
  const prefix = numeric > 0 ? "+" : numeric < 0 ? "−" : "";

  return `${prefix}${Math.abs(numeric).toFixed(2)}%`;
}

function number(value, decimals = 2) {
  if (value == null || !Number.isFinite(Number(value))) {
    return "—";
  }

  return Number(value).toLocaleString(undefined, {
    maximumFractionDigits: decimals,
  });
}

function formatDate(value) {
  if (!value) return "Unavailable";
  return value;
}

function toneClass(value) {
  if (value == null || !Number.isFinite(Number(value))) return "";
  if (Number(value) > 0) return "positive";
  if (Number(value) < 0) return "negative";
  return "neutral";
}

async function loadInitial() {
  loadingPortfolios.value = true;
  pageError.value = "";

  try {
    const [portfolioData, stockData] = await Promise.all([
      getPortfolios(),
      getStocks(),
    ]);

    portfolios.value = toList(portfolioData);
    stocks.value = toList(stockData).filter(
      (stock) => stock.is_active !== false
    );

    if (!holdingForm.stock_symbol && stocks.value.length) {
      holdingForm.stock_symbol = stocks.value[0].symbol;
    }

    const initialPortfolio =
      portfolios.value.find(
        (item) => String(item.id) === selectedPortfolioId.value
      ) || portfolios.value[0];

    if (initialPortfolio) {
      selectedPortfolioId.value = String(initialPortfolio.id);
      await loadSelectedPortfolio();
    } else {
      currentPortfolio.value = null;
      risk.value = null;
    }
  } catch (error) {
    pageError.value = errorMessage(error);
  } finally {
    loadingPortfolios.value = false;
  }
}

async function refreshPortfolioList(preferredId = null) {
  const portfolioData = await getPortfolios();
  portfolios.value = toList(portfolioData);

  const chosen = (
    preferredId != null
      ? portfolios.value.find((item) => String(item.id) === String(preferredId))
      : null
  ) || portfolios.value.find(
    (item) => String(item.id) === selectedPortfolioId.value
  ) || portfolios.value[0];

  if (!chosen) {
    selectedPortfolioId.value = "";
    currentPortfolio.value = null;
    risk.value = null;
    return;
  }

  selectedPortfolioId.value = String(chosen.id);
  await loadSelectedPortfolio();
}

async function loadSelectedPortfolio() {
  pageError.value = "";
  holdingError.value = "";
  riskError.value = "";

  if (!selectedPortfolioId.value) {
    currentPortfolio.value = null;
    risk.value = null;
    return;
  }

  const portfolioId = selectedPortfolioId.value;

  loadingPortfolio.value = true;
  loadingRisk.value = true;
  risk.value = null;

  try {
    currentPortfolio.value = await getPortfolio(portfolioId);

    // Keep portfolio-list labels and summaries up to date.
    portfolios.value = portfolios.value.map((portfolio) => (
      String(portfolio.id) === String(currentPortfolio.value.id)
        ? { ...portfolio, ...currentPortfolio.value }
        : portfolio
    ));
  } catch (error) {
    pageError.value = errorMessage(error);
    currentPortfolio.value = null;
  } finally {
    loadingPortfolio.value = false;
  }

  try {
    const analysis = await getPortfolioAnalysis(portfolioId);
    risk.value = analysis?.risk || null;
  } catch (error) {
    riskError.value = errorMessage(error);
  } finally {
    loadingRisk.value = false;
  }
}

async function createNewPortfolio() {
  if (!portfolioForm.name.trim()) return;

  pageError.value = "";
  savingPortfolio.value = true;

  try {
    const created = await createPortfolio({
      name: portfolioForm.name.trim(),
      description: portfolioForm.description.trim(),
    });

    portfolioForm.name = "";
    portfolioForm.description = "";

    await refreshPortfolioList(created.id);
  } catch (error) {
    pageError.value = errorMessage(error);
  } finally {
    savingPortfolio.value = false;
  }
}

async function removePortfolio() {
  if (!currentPortfolio.value) return;

  const portfolio = currentPortfolio.value;

  const confirmed = window.confirm(
    `Delete "${portfolio.name}" and all its holdings? This cannot be undone.`
  );

  if (!confirmed) return;

  pageError.value = "";
  savingPortfolio.value = true;

  try {
    await deletePortfolio(portfolio.id);

    currentPortfolio.value = null;
    selectedPortfolioId.value = "";
    await refreshPortfolioList();
  } catch (error) {
    pageError.value = errorMessage(error);
  } finally {
    savingPortfolio.value = false;
  }
}

async function addHolding() {
  if (!currentPortfolio.value) return;

  holdingError.value = "";
  savingHolding.value = true;

  const payload = {
    stock_symbol: holdingForm.stock_symbol,
    quantity: holdingForm.quantity,
    purchase_price: holdingForm.purchase_price,
    purchase_date: holdingForm.purchase_date || null,
  };

  try {
    await createPortfolioHolding(
      currentPortfolio.value.id,
      payload
    );

    holdingForm.quantity = "";
    holdingForm.purchase_price = "";
    holdingForm.purchase_date = "";

    await loadSelectedPortfolio();
  } catch (error) {
    holdingError.value = errorMessage(error);
  } finally {
    savingHolding.value = false;
  }
}

function startEdit(holding) {
  holdingError.value = "";
  editingHoldingId.value = holding.id;

  editForm.quantity = String(holding.quantity);
  editForm.purchase_price = String(holding.purchase_price);
  editForm.purchase_date = holding.purchase_date || "";
}

function cancelEdit() {
  editingHoldingId.value = null;
  editForm.quantity = "";
  editForm.purchase_price = "";
  editForm.purchase_date = "";
}

async function saveHolding(holding) {
  const quantity = Number(editForm.quantity);
  const purchasePrice = Number(editForm.purchase_price);

  if (!Number.isFinite(quantity) || quantity <= 0) {
    holdingError.value = "Quantity must be greater than zero.";
    return;
  }

  if (!Number.isFinite(purchasePrice) || purchasePrice <= 0) {
    holdingError.value = "Purchase price must be greater than zero.";
    return;
  }

  holdingError.value = "";
  savingHolding.value = true;

  try {
    await updatePortfolioHolding(
      currentPortfolio.value.id,
      holding.id,
      {
        quantity: String(quantity),
        purchase_price: String(purchasePrice),
        purchase_date: editForm.purchase_date || null,
      }
    );

    cancelEdit();
    await loadSelectedPortfolio();
  } catch (error) {
    holdingError.value = errorMessage(error);
  } finally {
    savingHolding.value = false;
  }
}

async function removeHolding(holding) {
  const confirmed = window.confirm(
    `Remove ${holding.stock_symbol} from this portfolio?`
  );

  if (!confirmed) return;

  holdingError.value = "";
  savingHolding.value = true;

  try {
    await deletePortfolioHolding(
      currentPortfolio.value.id,
      holding.id
    );

    if (editingHoldingId.value === holding.id) {
      cancelEdit();
    }

    await loadSelectedPortfolio();
  } catch (error) {
    holdingError.value = errorMessage(error);
  } finally {
    savingHolding.value = false;
  }
}

onMounted(loadInitial);
</script>

<style scoped>
.portfolio-page {
  max-width: 1600px;
  margin: 0 auto;
  padding: 28px clamp(16px, 3vw, 36px) 40px;
  display: flex;
  flex-direction: column;
  gap: 22px;
  color: #111827;
}

.page-header,
.toolbar-title,
.panel-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.page-header {
  align-items: center;
}

.eyebrow {
  margin: 0 0 7px;
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

h2 {
  margin: 0;
  font-size: 18px;
  letter-spacing: -.02em;
}

.subtitle,
.panel-heading p,
.toolbar-title p {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 14px;
  line-height: 1.5;
}

.panel,
.summary-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  box-shadow: 0 3px 12px rgb(15 23 42 / 3%);
}

.panel {
  overflow: hidden;
}

.portfolio-toolbar {
  padding: 20px 22px;
}

.toolbar-title {
  align-items: center;
  margin-bottom: 20px;
}

.toolbar-grid {
  display: grid;
  grid-template-columns: minmax(210px, .8fr) minmax(0, 2fr);
  gap: 22px;
}

.create-form {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  align-items: end;
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 7px;
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
  height: 40px;
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

.button {
  min-height: 39px;
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

.button:disabled,
.mini-button:disabled {
  cursor: not-allowed;
  opacity: .5;
}

.primary {
  border-color: #172554;
  background: #172554;
  color: white;
}

.primary:hover:not(:disabled) {
  background: #1e3a8a;
}

.secondary:hover:not(:disabled) {
  background: #f8fafc;
}

.danger-outline {
  border-color: #fecaca;
  color: #b91c1c;
}

.danger-outline:hover:not(:disabled) {
  background: #fef2f2;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.summary-card {
  display: flex;
  flex-direction: column;
  gap: 9px;
  min-width: 0;
  min-height: 125px;
  padding: 18px 20px;
}

.summary-label {
  color: #64748b;
  font-size: 12px;
  font-weight: 650;
}

.summary-card strong {
  font-size: clamp(20px, 2vw, 26px);
  letter-spacing: -.03em;
  overflow-wrap: anywhere;
}

.summary-card small {
  color: #94a3b8;
  font-size: 12px;
}

.date-value {
  font-size: 19px !important;
}

.panel-heading {
  padding: 20px 22px;
  border-bottom: 1px solid #eef2f7;
}

.add-holding-form {
  display: grid;
  grid-template-columns: 1.5fr .8fr 1fr 1fr auto;
  align-items: end;
  gap: 12px;
  padding: 20px 22px 14px;
}

.add-button {
  min-height: 40px;
}

.helper-text {
  margin: 0;
  padding: 0 22px 16px;
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.6;
}

.table-scroll {
  width: 100%;
  overflow-x: auto;
}

.holdings-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  white-space: nowrap;
}

.holdings-table th {
  padding: 13px 12px;
  background: #f8fafc;
  color: #64748b;
  font-size: 11px;
  font-weight: 750;
  text-align: right;
}

.holdings-table th:first-child,
.holdings-table td:first-child {
  padding-left: 22px;
  text-align: left;
}

.holdings-table td {
  padding: 14px 12px;
  border-top: 1px solid #eef2f7;
  color: #334155;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.holdings-table tbody tr:hover {
  background: #fbfdff;
}

.stock-cell strong,
.stock-cell small {
  display: block;
  text-align: left;
}

.stock-cell strong {
  color: #0f172a;
}

.stock-cell small,
.date-note {
  margin-top: 5px;
  color: #94a3b8;
  font-size: 11px;
}

.edit-input {
  width: 100px;
  height: 34px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 5px 7px;
  font: inherit;
}

.actions-cell {
  min-width: 145px;
}

.mini-button {
  margin: 2px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 6px 8px;
  background: #fff;
  color: #334155;
  cursor: pointer;
  font: inherit;
  font-size: 11px;
  font-weight: 650;
}

.save-button {
  border-color: #bbf7d0;
  color: #166534;
}

.delete-button {
  border-color: #fecaca;
  color: #b91c1c;
}

.positive {
  color: #15803d !important;
  font-weight: 700;
}

.negative {
  color: #b91c1c !important;
  font-weight: 700;
}

.neutral {
  color: #475569 !important;
}

.risk-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  padding: 20px 22px;
}

.risk-card {
  display: flex;
  flex-direction: column;
  gap: 9px;
  min-width: 0;
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fbfdff;
}

.risk-card span {
  color: #64748b;
  font-size: 12px;
  font-weight: 650;
}

.risk-card strong {
  font-size: 23px;
  letter-spacing: -.02em;
  overflow-wrap: anywhere;
}

.risk-card small {
  color: #94a3b8;
  font-size: 11px;
  line-height: 1.5;
}

.risk-footnote {
  padding: 0 22px 20px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}

.risk-footnote p {
  margin: 6px 0;
}

.empty-state,
.empty-portfolio {
  padding: 28px;
  text-align: center;
  color: #64748b;
}

.empty-state h3,
.empty-portfolio h2 {
  margin: 0 0 8px;
  color: #334155;
}

.empty-state p,
.empty-portfolio p {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
}

.loading-state {
  padding: 24px;
  text-align: center;
  color: #64748b;
  font-size: 13px;
}

.alert {
  border-radius: 10px;
  padding: 14px 16px;
  font-size: 13px;
}

.alert p {
  margin: 5px 0 0;
  line-height: 1.5;
}

.error-alert,
.inline-error {
  border: 1px solid #fecaca;
  background: #fef2f2;
  color: #b91c1c;
}

.inline-error {
  margin: 0 22px 16px;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 12px;
  line-height: 1.5;
}

.disclaimer {
  margin: -5px 0 0;
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 1200px) {
  .toolbar-grid {
    grid-template-columns: 1fr;
  }

  .add-holding-form {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .summary-grid,
  .risk-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .portfolio-page {
    padding: 20px 12px 30px;
    gap: 16px;
  }

  .page-header {
    align-items: flex-start;
  }

  .toolbar-title {
    align-items: flex-start;
    flex-direction: column;
  }

  .create-form,
  .add-holding-form {
    grid-template-columns: 1fr 1fr;
  }

  .create-form .button,
  .add-button {
    width: 100%;
  }

  .summary-grid,
  .risk-grid {
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }

  .summary-card {
    padding: 15px;
  }

  .summary-card strong {
    font-size: 20px;
  }

  .panel-heading {
    padding: 16px;
  }

  .helper-text {
    padding: 0 16px 16px;
  }

  .add-holding-form {
    padding: 16px;
  }

  .risk-grid {
    padding: 16px;
  }

  .risk-footnote {
    padding: 0 16px 16px;
  }
}

@media (max-width: 420px) {
  .create-form,
  .add-holding-form,
  .summary-grid,
  .risk-grid {
    grid-template-columns: 1fr;
  }
}
</style>
