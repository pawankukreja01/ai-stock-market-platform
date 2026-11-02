<template>
  <main class="portfolio-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">PORTFOLIO INTELLIGENCE</p>
        <h1>Portfolio overview</h1>
        <p class="subtitle">
          Track your holdings, understand allocation and review historical portfolio risk.
        </p>
      </div>
      <button
        class="button secondary"
        type="button"
        :disabled="loadingPortfolios || loadingPortfolio || !selectedPortfolioId"
        @click="loadSelectedPortfolio"
      >
        {{ loadingPortfolio ? "Refreshing…" : "Refresh portfolio" }}
      </button>
    </header>

    <div v-if="pageError" class="alert error-alert" role="alert">
      <strong>Something went wrong</strong>
      <p>{{ pageError }}</p>
    </div>

    <section class="panel portfolio-toolbar">
      <div class="toolbar-title">
        <div>
          <h2>Your portfolios</h2>
          <p>Select an existing portfolio or create a new one.</p>
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
      <span class="loader"></span>
      Loading portfolio data…
    </div>

    <section v-else-if="!currentPortfolio" class="panel empty-portfolio">
      <div class="empty-icon">＋</div>
      <h2>Create your first portfolio</h2>
      <p>Give it a name above, then add stocks to begin tracking your investments.</p>
    </section>

    <template v-else>
      <section class="portfolio-summary-grid" aria-label="Portfolio summary">
        <article class="summary-card overview-card">
          <span class="summary-label">Holdings</span>
          <strong>{{ summary.holdings_count }}</strong>
          <small>{{ summary.priced_holdings }} priced · {{ summary.unpriced_holdings }} awaiting price data</small>
        </article>

        <article
          v-for="group in currencyGroups"
          :key="`summary-${group.currency}`"
          class="summary-card currency-summary-card"
        >
          <div class="card-kicker">{{ currencyLabel(group.currency) }} portfolio value</div>
          <strong>{{ money(group.marketValue, group.currency) }}</strong>
          <div class="currency-summary-details">
            <span>Cost basis <b>{{ money(group.totalCostBasis, group.currency) }}</b></span>
            <span :class="toneClass(group.profitLoss)">P/L <b>{{ signedMoney(group.profitLoss, group.currency) }}</b></span>
          </div>
          <small :class="toneClass(group.returnPct)">{{ signedPercent(group.returnPct) }} return · {{ group.pricedHoldings }} priced holdings</small>
        </article>

        <article class="summary-card freshness-card">
          <span class="summary-label">Latest stored price date</span>
          <strong class="date-value">{{ formatDate(summary.data_as_of) }}</strong>
          <small>Historical closing prices · not live brokerage valuations</small>
        </article>
      </section>

      <div v-if="summary.mixed_currencies" class="currency-notice">
        <span class="notice-icon">i</span>
        <p>
          This portfolio contains multiple currencies. Values and allocations are shown separately by currency;
          <strong>no FX conversion or combined portfolio total is calculated.</strong>
        </p>
      </div>

      <section v-if="currentPortfolio.holdings.length" class="insights-grid">
        <article class="panel insight-panel">
          <div class="panel-heading">
            <div>
              <p class="eyebrow">WEIGHTED BY CURRENT VALUE</p>
              <h2>Holdings allocation</h2>
              <p>Position weights are calculated within each currency group.</p>
            </div>
          </div>

          <div v-if="currencyGroups.length" class="currency-visual-groups">
            <section v-for="group in currencyGroups" :key="`allocation-${group.currency}`" class="currency-visual-group">
              <div class="visual-group-heading">
                <strong>{{ currencyLabel(group.currency) }}</strong>
                <span>{{ money(group.marketValue, group.currency) }}</span>
              </div>
              <div v-if="group.pricedHoldings" class="allocation-list">
                <div v-for="holding in group.holdings" :key="holding.id" class="allocation-row">
                  <div class="allocation-label">
                    <strong>{{ holding.stock_symbol }}</strong>
                    <span>{{ holding.company_name }}</span>
                  </div>
                  <div class="allocation-track" aria-hidden="true">
                    <span
                      :style="{
                        width: `${holding.uiWeightPct || 0}%`,
                        background: allocationColor(holding.stock_symbol),
                      }"
                    ></span>
                  </div>
                  <div class="allocation-value">
                    <strong>{{ holding.uiWeightPct == null ? "—" : plainPercent(holding.uiWeightPct) }}</strong>
                    <small>{{ moneyOrDash(holding.current_value, group.currency) }}</small>
                  </div>
                </div>
              </div>
              <p v-else class="muted-note">No current prices are available for this currency group.</p>
              <div v-if="group.sectors.length" class="sector-summary">
                <div class="subsection-heading">Sector exposure</div>
                <div v-for="sector in group.sectors" :key="sector.name" class="sector-row">
                  <span>{{ sector.name }}</span>
                  <div class="sector-track"><span :style="{ width: `${sector.weightPct}%` }"></span></div>
                  <strong>{{ plainPercent(sector.weightPct) }}</strong>
                </div>
              </div>
            </section>
          </div>
          <p class="panel-footnote">
            Unpriced holdings are excluded from market-value weights. Sector and position weights are descriptive, not recommendations.
          </p>
        </article>

        <article class="panel insight-panel">
          <div class="panel-heading">
            <div>
              <p class="eyebrow">UNREALISED PERFORMANCE</p>
              <h2>Position profit &amp; loss</h2>
              <p>Bars are scaled within each currency group.</p>
            </div>
          </div>

          <div v-if="currencyGroups.length" class="currency-visual-groups pnl-groups">
            <section v-for="group in currencyGroups" :key="`pnl-${group.currency}`" class="currency-visual-group">
              <div class="visual-group-heading">
                <strong>{{ currencyLabel(group.currency) }}</strong>
                <span :class="toneClass(group.profitLoss)">{{ signedMoney(group.profitLoss, group.currency) }}</span>
              </div>
              <div v-if="group.pricedHoldings" class="pnl-list">
                <div v-for="holding in group.holdings" :key="holding.id" class="pnl-row">
                  <span class="pnl-symbol">{{ holding.stock_symbol }}</span>
                  <div class="pnl-track" aria-hidden="true">
                    <span
                      v-if="holding.unrealized_profit_loss != null"
                      :class="['pnl-fill', Number(holding.unrealized_profit_loss) >= 0 ? 'gain' : 'loss']"
                      :style="pnlBarStyle(holding, group)"
                    ></span>
                  </div>
                  <strong :class="toneClass(holding.unrealized_profit_loss)">
                    {{ signedMoney(holding.unrealized_profit_loss, group.currency) }}
                  </strong>
                </div>
              </div>
              <p v-else class="muted-note">Profit and loss is unavailable until stored prices are available.</p>
            </section>
          </div>
          <p class="panel-footnote">
            Unrealised P/L compares the entered purchase price with the latest stored closing price. It excludes fees, tax, dividends and cash flows.
          </p>
        </article>
      </section>

      <section class="panel holdings-panel">
        <div class="panel-heading">
          <div>
            <p class="eyebrow">POSITIONS</p>
            <h2>Holdings</h2>
            <p>Add a stock or update the quantity and purchase details you entered.</p>
          </div>
          <span class="count-pill">{{ currentPortfolio.holdings.length }} positions</span>
        </div>

        <form class="stock-search-form" @submit.prevent="searchStockOptions">
          <label class="field stock-search-field">
            <span>Find a stock to add</span>
            <input
              v-model.trim="stockSearch"
              type="search"
              placeholder="Search by ticker or company name"
              autocomplete="off"
            />
          </label>
          <button class="button secondary" type="submit" :disabled="loadingStocks">
            {{ loadingStocks ? "Searching…" : "Search catalogue" }}
          </button>
        </form>
        <p v-if="stockLookupError" class="inline-error">{{ stockLookupError }}</p>

        <form class="add-holding-form" @submit.prevent="addHolding">
          <label class="field">
            <span>Stock</span>
            <select v-model="holdingForm.stock_symbol" required>
              <option value="" disabled>Select stock</option>
              <option v-for="stock in stocks" :key="stock.id" :value="stock.symbol">
                {{ stock.symbol }} — {{ stock.company_name }} ({{ stock.currency || "Currency unavailable" }})
              </option>
            </select>
          </label>
          <label class="field">
            <span>Quantity</span>
            <input v-model="holdingForm.quantity" type="number" min="0.000001" step="any" placeholder="10" required />
          </label>
          <label class="field">
            <span>Purchase price ({{ selectedStockCurrency }})</span>
            <input v-model="holdingForm.purchase_price" type="number" min="0.0001" step="any" placeholder="100.00" required />
          </label>
          <label class="field">
            <span>Purchase date</span>
            <input v-model="holdingForm.purchase_date" type="date" />
          </label>
          <button class="button primary add-button" type="submit" :disabled="savingHolding || !holdingForm.stock_symbol">
            {{ savingHolding ? "Adding…" : "Add holding" }}
          </button>
        </form>

        <p class="helper-text">
          Enter the purchase price in the stock's stored trading currency. Values use the latest stored price, not a verified brokerage execution.
          Existing purchase entries are assumed to use that same currency; this update does not convert or rewrite them. The platform does not currently convert currencies.
        </p>
        <p v-if="holdingError" class="inline-error" role="alert">{{ holdingError }}</p>

        <div v-if="!currentPortfolio.holdings.length" class="empty-state">
          <h3>No holdings yet</h3>
          <p>Search the stock catalogue and add your first position.</p>
        </div>

        <div v-else class="table-scroll">
          <table class="holdings-table">
            <thead>
              <tr>
                <th>Stock</th>
                <th>Currency</th>
                <th>Quantity</th>
                <th>Purchase price</th>
                <th>Current price</th>
                <th>Market value</th>
                <th>Cost basis</th>
                <th>Profit / loss</th>
                <th>Return</th>
                <th>Weight*</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="holding in currentPortfolio.holdings" :key="holding.id">
                <td class="stock-cell">
                  <RouterLink :to="`/stocks/${encodeURIComponent(holding.stock_symbol)}`" class="stock-link">
                    {{ holding.stock_symbol }}
                  </RouterLink>
                  <small>{{ holding.company_name }}</small>
                  <small>{{ holding.exchange || "Exchange unavailable" }}</small>
                </td>
                <td><span class="currency-pill">{{ holding.currency || "UNKNOWN" }}</span></td>
                <td>
                  <input v-if="editingHoldingId === holding.id" v-model="editForm.quantity" class="edit-input" type="number" min="0.000001" step="any" aria-label="Edit quantity" />
                  <span v-else>{{ number(holding.quantity, 4) }}</span>
                </td>
                <td>
                  <input v-if="editingHoldingId === holding.id" v-model="editForm.purchase_price" class="edit-input" type="number" min="0.0001" step="any" aria-label="Edit purchase price" />
                  <span v-else>{{ money(holding.purchase_price, holding.currency) }}</span>
                </td>
                <td>
                  {{ moneyOrDash(holding.current_price, holding.currency) }}
                  <small class="date-note">{{ holding.current_price_date || "No price date" }}</small>
                </td>
                <td>{{ moneyOrDash(holding.current_value, holding.currency) }}</td>
                <td>{{ money(holding.cost_basis, holding.currency) }}</td>
                <td :class="toneClass(holding.unrealized_profit_loss)">{{ signedMoney(holding.unrealized_profit_loss, holding.currency) }}</td>
                <td :class="toneClass(holding.unrealized_return_pct)">{{ signedPercent(holding.unrealized_return_pct) }}</td>
                <td>{{ holding.weight_pct == null ? "—" : plainPercent(holding.weight_pct) }}</td>
                <td class="actions-cell">
                  <template v-if="editingHoldingId === holding.id">
                    <button class="mini-button save-button" type="button" :disabled="savingHolding" @click="saveHolding(holding)">Save</button>
                    <button class="mini-button" type="button" @click="cancelEdit">Cancel</button>
                  </template>
                  <template v-else>
                    <button class="mini-button" type="button" @click="startEdit(holding)">Edit</button>
                    <button class="mini-button delete-button" type="button" :disabled="savingHolding" @click="removeHolding(holding)">Remove</button>
                  </template>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="currentPortfolio.holdings.length" class="table-footnote">
          * Weight is measured against other priced holdings in the same currency only. It is not a cross-currency portfolio weight.
        </p>
      </section>

      <section class="panel risk-panel">
        <div class="panel-heading">
          <div>
            <p class="eyebrow">HISTORICAL DOWNSIDE &amp; VOLATILITY</p>
            <h2>Portfolio risk</h2>
            <p>Historical estimates based on adjusted closing prices and current quantities.</p>
          </div>
        </div>

        <div v-if="loadingRisk" class="loading-state">Calculating historical portfolio risk…</div>
        <div v-else-if="riskError" class="inline-error">{{ riskError }}</div>
        <template v-else-if="risk?.available">
          <div class="risk-grid">
            <article class="risk-card"><span>Annualised volatility</span><strong>{{ plainPercent(risk.annualized_volatility_pct) }}</strong><small>{{ risk.observations }} daily returns · {{ currencyLabel(risk.currency) }}</small></article>
            <article class="risk-card"><span>Maximum drawdown</span><strong class="negative">{{ plainPercent(risk.max_drawdown_pct) }}</strong><small>Historical peak-to-trough decline</small></article>
            <article class="risk-card"><span>Period return</span><strong :class="toneClass(risk.period_return_pct)">{{ signedPercent(risk.period_return_pct) }}</strong><small>{{ risk.start_date }} to {{ risk.end_date }}</small></article>
            <article class="risk-card"><span>Annualised historical return</span><strong :class="toneClass(risk.annualized_return_pct)">{{ signedPercent(risk.annualized_return_pct) }}</strong><small>Historical estimate, not a forecast</small></article>
          </div>
        </template>
        <template v-else-if="risk?.by_currency?.length">
          <div class="risk-currency-note">
            This portfolio has multiple currencies. Risk statistics are presented separately for each currency group because no FX conversion is configured.
          </div>
          <div v-for="item in risk.by_currency" :key="`risk-${item.currency}`" class="risk-currency-group">
            <div class="visual-group-heading"><strong>{{ currencyLabel(item.currency) }}</strong></div>
            <div v-if="item.available" class="risk-grid">
              <article class="risk-card"><span>Annualised volatility</span><strong>{{ plainPercent(item.annualized_volatility_pct) }}</strong><small>{{ item.observations }} daily returns</small></article>
              <article class="risk-card"><span>Maximum drawdown</span><strong class="negative">{{ plainPercent(item.max_drawdown_pct) }}</strong><small>Historical peak-to-trough decline</small></article>
              <article class="risk-card"><span>Period return</span><strong :class="toneClass(item.period_return_pct)">{{ signedPercent(item.period_return_pct) }}</strong><small>{{ item.start_date }} to {{ item.end_date }}</small></article>
              <article class="risk-card"><span>Annualised historical return</span><strong :class="toneClass(item.annualized_return_pct)">{{ signedPercent(item.annualized_return_pct) }}</strong><small>Historical estimate, not a forecast</small></article>
            </div>
            <p v-else class="muted-note">{{ item.reason }}</p>
            <p class="risk-footnote">Included: {{ item.included_symbols?.join(", ") || "None" }}<span v-if="item.excluded_symbols?.length"> · Excluded: {{ item.excluded_symbols.join(", ") }}</span></p>
          </div>
        </template>
        <div v-else class="empty-state risk-empty">
          <h3>Risk estimate unavailable</h3>
          <p>{{ risk?.reason || "Add holdings with sufficient stored price history to calculate risk." }}</p>
        </div>

        <div v-if="risk?.available" class="risk-footnote">
          <p>Historical window: {{ risk.start_date }} to {{ risk.end_date }}.</p>
          <p>Included stocks: {{ risk.included_symbols?.join(", ") || "None" }}.</p>
          <p v-if="risk.excluded_symbols?.length">Excluded due to insufficient history: {{ risk.excluded_symbols.join(", ") }}.</p>
          <p>{{ risk.method }}</p>
        </div>
      </section>

      <p class="disclaimer">
        Market values use latest stored closing prices. P/L excludes fees, taxes, dividends, corporate-action adjustments to your entered cost basis and cash flows.
        Historical risk assumes current quantities were held throughout the measurement window; it does not model deposits, withdrawals or rebalancing.
        This is an investment research tool, not personalised financial advice.
      </p>
    </template>
  </main>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { RouterLink } from "vue-router";
import {
  getStockCatalog,
  getPortfolios,
  createPortfolio,
  getPortfolio,
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
const loadingStocks = ref(false);
const savingPortfolio = ref(false);
const savingHolding = ref(false);
const pageError = ref("");
const holdingError = ref("");
const riskError = ref("");
const stockLookupError = ref("");
const stockSearch = ref("");

const portfolioForm = reactive({ name: "", description: "" });
const holdingForm = reactive({ stock_symbol: "", quantity: "", purchase_price: "", purchase_date: "" });
const editingHoldingId = ref(null);
const editForm = reactive({ quantity: "", purchase_price: "", purchase_date: "" });

const summary = computed(() => currentPortfolio.value?.summary || {
  holdings_count: 0,
  priced_holdings: 0,
  unpriced_holdings: 0,
  currency_count: 0,
  mixed_currencies: false,
  currency: null,
  market_value: null,
  total_cost_basis: null,
  unrealized_profit_loss: null,
  unrealized_return_pct: null,
  data_as_of: null,
  currency_breakdown: [],
});

const selectedStock = computed(() => stocks.value.find((stock) => stock.symbol === holdingForm.stock_symbol) || null);
const selectedStockCurrency = computed(() => selectedStock.value?.currency || "currency unavailable");

const currencyGroups = computed(() => {
  const map = new Map();
  const holdings = currentPortfolio.value?.holdings || [];

  for (const holding of holdings) {
    const currency = normalizeCurrency(holding.currency);
    if (!map.has(currency)) {
      map.set(currency, {
        currency,
        holdings: [],
        marketValue: 0,
        totalCostBasis: 0,
        pricedCostBasis: 0,
        profitLoss: 0,
        pricedHoldings: 0,
        unpricedHoldings: 0,
        returnPct: null,
        sectors: [],
      });
    }
    const group = map.get(currency);
    const currentValue = finiteOrNull(holding.current_value);
    const costBasis = finiteOrNull(holding.cost_basis);
    const profitLoss = finiteOrNull(holding.unrealized_profit_loss);
    group.holdings.push(holding);
    group.totalCostBasis += costBasis ?? 0;
    if (currentValue == null) {
      group.unpricedHoldings += 1;
    } else {
      group.pricedHoldings += 1;
      group.marketValue += currentValue;
      group.pricedCostBasis += costBasis ?? 0;
      group.profitLoss += profitLoss ?? 0;
    }
  }

  const apiGroups = new Map((summary.value.currency_breakdown || []).map((item) => [normalizeCurrency(item.currency), item]));
  const result = [];

  for (const group of map.values()) {
    const apiGroup = apiGroups.get(group.currency);
    if (apiGroup) {
      group.marketValue = Number(apiGroup.market_value || 0);
      group.totalCostBasis = Number(apiGroup.total_cost_basis || 0);
      group.pricedCostBasis = Number(apiGroup.priced_cost_basis || 0);
      group.profitLoss = Number(apiGroup.unrealized_profit_loss || 0);
      group.pricedHoldings = Number(apiGroup.priced_holdings || 0);
      group.unpricedHoldings = Number(apiGroup.unpriced_holdings || 0);
    }
    group.returnPct = group.pricedCostBasis > 0 ? group.profitLoss / group.pricedCostBasis * 100 : null;
    group.holdings = group.holdings.map((holding) => ({
      ...holding,
      uiWeightPct: group.marketValue > 0 && finiteOrNull(holding.current_value) != null
        ? Number(holding.current_value) / group.marketValue * 100
        : null,
    }));

    const sectorMap = new Map();
    for (const holding of group.holdings) {
      if (holding.current_value == null) continue;
      const name = holding.sector || "Unclassified";
      sectorMap.set(name, (sectorMap.get(name) || 0) + Number(holding.current_value));
    }
    group.sectors = [...sectorMap.entries()]
      .map(([name, value]) => ({ name, weightPct: group.marketValue > 0 ? value / group.marketValue * 100 : 0 }))
      .sort((a, b) => b.weightPct - a.weightPct);
    group.holdings.sort((a, b) => Number(b.current_value || 0) - Number(a.current_value || 0));
    result.push(group);
  }
  return result.sort((a, b) => a.currency.localeCompare(b.currency));
});

function finiteOrNull(value) {
  if (value == null || value === "") return null;
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberValue : null;
}

function normalizeCurrency(value) {
  const code = String(value || "UNKNOWN").trim().toUpperCase();
  return /^[A-Z]{3}$/.test(code) ? code : "UNKNOWN";
}

function currencyLabel(currency) {
  return currency === "UNKNOWN" ? "Currency unavailable" : currency;
}

function money(value, currency = "USD") {
  const numeric = finiteOrNull(value);
  if (numeric == null) return "—";
  const code = normalizeCurrency(currency);
  if (code === "UNKNOWN") {
    return `${numeric.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} (currency unavailable)`;
  }
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: code,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(numeric);
  } catch {
    return `${code} ${numeric.toFixed(2)}`;
  }
}

function moneyOrDash(value, currency) {
  return value == null ? "—" : money(value, currency);
}

function signedMoney(value, currency) {
  const numeric = finiteOrNull(value);
  if (numeric == null) return "—";
  const prefix = numeric > 0 ? "+" : numeric < 0 ? "−" : "";
  return `${prefix}${money(Math.abs(numeric), currency)}`;
}

function plainPercent(value) {
  const numeric = finiteOrNull(value);
  return numeric == null ? "—" : `${numeric.toFixed(2)}%`;
}

function signedPercent(value) {
  const numeric = finiteOrNull(value);
  if (numeric == null) return "—";
  const prefix = numeric > 0 ? "+" : numeric < 0 ? "−" : "";
  return `${prefix}${Math.abs(numeric).toFixed(2)}%`;
}

function number(value, decimals = 2) {
  const numeric = finiteOrNull(value);
  return numeric == null ? "—" : numeric.toLocaleString(undefined, { maximumFractionDigits: decimals });
}

function formatDate(value) {
  if (!value) return "Unavailable";
  return value;
}

function toneClass(value) {
  const numeric = finiteOrNull(value);
  if (numeric == null || numeric === 0) return "neutral";
  return numeric > 0 ? "positive" : "negative";
}

function allocationColor(symbol) {
  const palette = ["#2563eb", "#0891b2", "#7c3aed", "#0f9f6e", "#d97706", "#db2777", "#64748b", "#4f46e5"];
  let hash = 0;
  for (const char of String(symbol || "")) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return palette[hash % palette.length];
}

function pnlBarStyle(holding, group) {
  const values = group.holdings
    .map((item) => Math.abs(finiteOrNull(item.unrealized_profit_loss) || 0));
  const maxValue = Math.max(...values, 0);
  const value = Math.abs(finiteOrNull(holding.unrealized_profit_loss) || 0);
  const width = maxValue > 0 ? value / maxValue * 48 : 0;
  return Number(holding.unrealized_profit_loss) >= 0
    ? { left: "50%", width: `${width}%` }
    : { left: `${50 - width}%`, width: `${width}%` };
}

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
    return Object.entries(data).map(([field, messages]) => {
      const value = Array.isArray(messages) ? messages.join(", ") : String(messages);
      return `${field}: ${value}`;
    }).join(" | ");
  }
  return error?.message || "An unexpected error occurred.";
}

async function searchStockOptions() {
  loadingStocks.value = true;
  stockLookupError.value = "";
  try {
    const response = await getStockCatalog({
      search: stockSearch.value.trim(),
      page: 1,
      pageSize: 100,
    });
    stocks.value = toList(response).filter((stock) => stock.is_active !== false);
    if (!stocks.value.length) stockLookupError.value = "No active stocks matched that search.";
    if (!holdingForm.stock_symbol && stocks.value.length) holdingForm.stock_symbol = stocks.value[0].symbol;
  } catch (error) {
    stockLookupError.value = errorMessage(error);
  } finally {
    loadingStocks.value = false;
  }
}

async function loadInitial() {
  loadingPortfolios.value = true;
  pageError.value = "";
  try {
    const [portfolioData, stockData] = await Promise.all([
      getPortfolios(),
      getStockCatalog({ page: 1, pageSize: 100 }),
    ]);
    portfolios.value = toList(portfolioData);
    stocks.value = toList(stockData).filter((stock) => stock.is_active !== false);
    if (!holdingForm.stock_symbol && stocks.value.length) holdingForm.stock_symbol = stocks.value[0].symbol;

    const initialPortfolio = portfolios.value.find(
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
  portfolios.value = toList(await getPortfolios());
  const chosen = (preferredId != null
    ? portfolios.value.find((item) => String(item.id) === String(preferredId))
    : null) || portfolios.value.find((item) => String(item.id) === selectedPortfolioId.value) || portfolios.value[0];
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

  if (!currentPortfolio.value) {
    loadingRisk.value = false;
    return;
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
    const created = await createPortfolio({ name: portfolioForm.name.trim(), description: portfolioForm.description.trim() });
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
  if (!window.confirm(`Delete "${portfolio.name}" and all its holdings? This cannot be undone.`)) return;
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
  if (!currentPortfolio.value || !holdingForm.stock_symbol) return;
  holdingError.value = "";
  savingHolding.value = true;
  try {
    await createPortfolioHolding(currentPortfolio.value.id, {
      stock_symbol: holdingForm.stock_symbol,
      quantity: holdingForm.quantity,
      purchase_price: holdingForm.purchase_price,
      purchase_date: holdingForm.purchase_date || null,
    });
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
    await updatePortfolioHolding(currentPortfolio.value.id, holding.id, {
      quantity: String(quantity),
      purchase_price: String(purchasePrice),
      purchase_date: editForm.purchase_date || null,
    });
    cancelEdit();
    await loadSelectedPortfolio();
  } catch (error) {
    holdingError.value = errorMessage(error);
  } finally {
    savingHolding.value = false;
  }
}

async function removeHolding(holding) {
  if (!window.confirm(`Remove ${holding.stock_symbol} from this portfolio?`)) return;
  holdingError.value = "";
  savingHolding.value = true;
  try {
    await deletePortfolioHolding(currentPortfolio.value.id, holding.id);
    if (editingHoldingId.value === holding.id) cancelEdit();
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
.portfolio-page{max-width:1600px;margin:0 auto;padding:28px clamp(16px,3vw,36px) 42px;display:flex;flex-direction:column;gap:20px;color:#142238}
.page-header,.toolbar-title,.panel-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:18px}
.page-header{align-items:center}
.eyebrow{margin:0 0 7px;color:#2563eb;font-size:11px;font-weight:850;letter-spacing:.14em}
h1{margin:0;font-size:clamp(28px,3vw,36px);letter-spacing:-.045em;color:#15243b}
h2{margin:0;font-size:19px;letter-spacing:-.025em;color:#17263d}
.subtitle,.panel-heading p,.toolbar-title p{margin:7px 0 0;color:#71819a;font-size:14px;line-height:1.55}
.panel,.summary-card{background:#fff;border:1px solid #e2eaf4;border-radius:16px;box-shadow:0 4px 16px rgb(15 35 65 / 4%)}
.panel{overflow:hidden}
.portfolio-toolbar{padding:20px 22px}
.toolbar-title{align-items:center;margin-bottom:18px}
.toolbar-grid{display:grid;grid-template-columns:minmax(220px,.75fr) minmax(0,2fr);gap:20px}
.create-form{display:grid;grid-template-columns:1fr 1fr auto;align-items:end;gap:12px}
.field{display:flex;flex-direction:column;min-width:0;gap:7px}
.field span{color:#52627b;font-size:12px;font-weight:700}
.field input,.field select{box-sizing:border-box;width:100%;min-width:0;min-height:42px;border:1px solid #d7e1ee;border-radius:9px;outline:none;padding:0 11px;background:#fff;color:#17263d;font:inherit;font-size:13px}
.field input:focus,.field select:focus{border-color:#3b82f6;box-shadow:0 0 0 3px rgb(59 130 246 / 12%)}
.button{display:inline-flex;align-items:center;justify-content:center;min-height:40px;border:1px solid #cbd7e6;border-radius:9px;padding:0 14px;background:#fff;color:#34445d;cursor:pointer;font:inherit;font-size:13px;font-weight:750;white-space:nowrap}
.button:disabled,.mini-button:disabled{cursor:not-allowed;opacity:.5}
.primary{border-color:#2563eb;background:#2563eb;color:#fff}.primary:hover:not(:disabled){background:#1d4ed8}
.secondary:hover:not(:disabled){background:#f8fbff}
.danger-outline{border-color:#fecaca;color:#b91c1c}.danger-outline:hover:not(:disabled){background:#fff5f5}
.portfolio-summary-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:13px}
.summary-card{display:flex;flex-direction:column;gap:8px;min-width:0;min-height:122px;padding:17px 19px}
.summary-label,.card-kicker{color:#667791;font-size:12px;font-weight:700}
.summary-card>strong{font-size:clamp(22px,2vw,28px);letter-spacing:-.035em;overflow-wrap:anywhere;color:#17263d}
.summary-card small{color:#8291a7;font-size:11px;line-height:1.45}
.currency-summary-card{border-top:3px solid #3b82f6}
.currency-summary-details{display:flex;gap:14px;flex-wrap:wrap;color:#8090a7;font-size:11px}
.currency-summary-details span{display:flex;gap:5px}.currency-summary-details b{color:#33445e;font-weight:750}
.date-value{font-size:19px!important}
.currency-notice{display:flex;align-items:flex-start;gap:11px;padding:13px 15px;border:1px solid #bfdbfe;border-radius:11px;background:#eff6ff;color:#34547d;font-size:12px;line-height:1.55}
.currency-notice p{margin:0}.notice-icon{flex:0 0 20px;display:grid;place-items:center;width:20px;height:20px;border-radius:50%;background:#dbeafe;color:#1d4ed8;font-weight:800}
.insights-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
.insight-panel{min-width:0}
.panel-heading{padding:18px 20px;border-bottom:1px solid #edf2f8}
.panel-heading .eyebrow{margin-bottom:5px}
.panel-heading p{font-size:12px}
.currency-visual-groups{padding:8px 20px 0}
.currency-visual-group{padding:14px 0 17px;border-bottom:1px solid #edf2f8}
.currency-visual-group:last-child{border-bottom:0}
.visual-group-heading{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:13px;color:#273750;font-size:13px}
.visual-group-heading span{font-variant-numeric:tabular-nums;font-weight:750}
.allocation-list,.pnl-list{display:grid;gap:12px}
.allocation-row{display:grid;grid-template-columns:minmax(90px,1fr) minmax(80px,1.6fr) minmax(85px,.8fr);align-items:center;gap:10px}
.allocation-label{min-width:0;display:grid;gap:3px}.allocation-label strong{font-size:12px;color:#263750}.allocation-label span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#8a98ac;font-size:10px}
.allocation-track,.sector-track{height:8px;overflow:hidden;border-radius:99px;background:#e8edf4}.allocation-track span,.sector-track span{display:block;height:100%;border-radius:99px;min-width:0}
.allocation-value{display:grid;justify-items:end;gap:3px;font-variant-numeric:tabular-nums}.allocation-value strong{font-size:11px;color:#34445e}.allocation-value small{font-size:10px;color:#8896aa}
.sector-summary{display:grid;gap:9px;margin-top:18px;padding-top:13px;border-top:1px dashed #e3eaf3}.subsection-heading{color:#71819a;font-size:11px;font-weight:800;letter-spacing:.06em;text-transform:uppercase}
.sector-row{display:grid;grid-template-columns:minmax(95px,1fr) minmax(60px,1.5fr) 48px;gap:9px;align-items:center;color:#6b7c94;font-size:11px}.sector-row strong{text-align:right;color:#3d4f68;font-size:10px}
.sector-track{height:6px}.sector-track span{background:#7c9df3}
.pnl-groups{padding-bottom:4px}.pnl-row{display:grid;grid-template-columns:58px minmax(80px,1fr) minmax(86px,auto);gap:10px;align-items:center}.pnl-symbol{color:#455771;font-size:11px;font-weight:800}.pnl-track{position:relative;height:9px;border-radius:99px;background:#edf1f6;overflow:hidden}.pnl-track::after{content:"";position:absolute;left:50%;top:0;bottom:0;width:1px;background:#b8c4d4}.pnl-fill{position:absolute;top:0;height:100%;border-radius:99px}.pnl-fill.gain{background:#16a36a}.pnl-fill.loss{background:#e34b4b}.pnl-row>strong{text-align:right;font-size:11px;font-variant-numeric:tabular-nums}
.panel-footnote,.table-footnote{margin:0;padding:12px 20px 16px;color:#8a98ac;font-size:10px;line-height:1.55}
.muted-note{margin:0;color:#8997aa;font-size:12px;line-height:1.5}
.count-pill,.currency-pill{display:inline-flex;align-items:center;justify-content:center;border:1px solid #dce7f5;border-radius:999px;background:#f3f7fc;color:#48627f;padding:5px 9px;font-size:10px;font-weight:800;white-space:nowrap}
.holdings-panel .panel-heading{align-items:center}
.stock-search-form{display:grid;grid-template-columns:minmax(220px,1fr) auto;gap:11px;align-items:end;padding:17px 20px 12px;background:#fbfdff}
.add-holding-form{display:grid;grid-template-columns:1.45fr .7fr 1fr .9fr auto;align-items:end;gap:11px;padding:12px 20px 14px}
.add-button{min-height:42px}
.helper-text{margin:0;padding:0 20px 15px;color:#8796aa;font-size:11px;line-height:1.55}
.inline-error{margin:0 20px 14px;padding:10px 12px;border:1px solid #fecaca;border-radius:8px;background:#fff5f5;color:#b91c1c;font-size:12px;line-height:1.5}
.table-scroll{width:100%;overflow-x:auto}
.holdings-table{width:100%;border-collapse:collapse;font-size:12px;white-space:nowrap;font-variant-numeric:tabular-nums}
.holdings-table th{padding:12px 11px;background:#f7f9fc;color:#74839a;font-size:10px;font-weight:800;text-align:right}
.holdings-table th:first-child,.holdings-table td:first-child{padding-left:20px;text-align:left}
.holdings-table td{padding:13px 11px;border-top:1px solid #edf1f6;color:#34445e;text-align:right}
.holdings-table tbody tr:hover{background:#fbfdff}
.stock-cell{min-width:145px}.stock-link{display:block;color:#1d4ed8;font-weight:850;text-decoration:none}.stock-link:hover{text-decoration:underline}.stock-cell small,.date-note{display:block;margin-top:4px;color:#92a0b3;font-size:10px;text-align:left}
.edit-input{width:88px;min-height:32px;box-sizing:border-box;border:1px solid #cbd7e6;border-radius:6px;padding:4px 6px;font:inherit}
.actions-cell{min-width:125px}.mini-button{margin:2px;border:1px solid #d2dce9;border-radius:6px;padding:6px 8px;background:#fff;color:#40516a;cursor:pointer;font:inherit;font-size:10px;font-weight:750}.save-button{border-color:#bbf7d0;color:#166534}.delete-button{border-color:#fecaca;color:#b91c1c}
.positive{color:#15803d!important;font-weight:750}.negative{color:#b91c1c!important;font-weight:750}.neutral{color:#64748b!important}
.risk-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;padding:18px 20px}
.risk-card{display:flex;flex-direction:column;gap:8px;min-width:0;padding:15px;border:1px solid #e2eaf4;border-radius:11px;background:#fbfdff}.risk-card span{color:#71819a;font-size:11px;font-weight:700}.risk-card strong{font-size:21px;letter-spacing:-.025em;overflow-wrap:anywhere}.risk-card small{color:#8b9ab0;font-size:10px;line-height:1.5}
.risk-currency-note{padding:14px 20px 0;color:#71819a;font-size:11px;line-height:1.55}.risk-currency-group{padding:14px 0 8px;border-bottom:1px solid #edf2f8}.risk-currency-group:last-child{border-bottom:0}.risk-footnote{padding:0 20px 15px;color:#8796aa;font-size:10px;line-height:1.55}.risk-footnote p{margin:5px 0}
.empty-state,.empty-portfolio{padding:32px;text-align:center;color:#7d8da4}.empty-state h3,.empty-portfolio h2{margin:0 0 8px;color:#34445e}.empty-state p,.empty-portfolio p{margin:0;font-size:12px;line-height:1.6}.empty-icon{display:grid;place-items:center;width:42px;height:42px;margin:0 auto 12px;border-radius:12px;background:#eff6ff;color:#2563eb;font-size:25px}.loading-state{display:flex;justify-content:center;align-items:center;gap:10px;padding:28px;color:#75859d;font-size:13px}.loader{width:15px;height:15px;border:2px solid #dbeafe;border-top-color:#2563eb;border-radius:50%;animation:spin .8s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}
.alert{border-radius:10px;padding:13px 15px;font-size:12px}.alert p{margin:5px 0 0;line-height:1.5}.error-alert{border:1px solid #fecaca;background:#fff5f5;color:#b91c1c}
.disclaimer{margin:-4px 0 0;color:#8a98ac;font-size:10px;line-height:1.6}
@media(max-width:1180px){.toolbar-grid{grid-template-columns:1fr}.insights-grid{grid-template-columns:1fr}.add-holding-form{grid-template-columns:repeat(3,minmax(0,1fr))}.risk-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:760px){.portfolio-page{padding:20px 12px 30px;gap:15px}.page-header,.toolbar-title{align-items:flex-start;flex-direction:column}.create-form,.add-holding-form{grid-template-columns:1fr 1fr}.stock-search-form{grid-template-columns:1fr}.summary-card{min-height:110px}.allocation-row{grid-template-columns:86px minmax(50px,1fr) 80px;gap:7px}.panel-heading{padding:16px}.currency-visual-groups{padding:7px 15px 0}.panel-footnote,.table-footnote{padding-left:15px;padding-right:15px}}
@media(max-width:440px){.create-form,.add-holding-form,.risk-grid{grid-template-columns:1fr}.currency-summary-details{flex-direction:column;gap:5px}.allocation-row{grid-template-columns:74px minmax(40px,1fr) 74px}.pnl-row{grid-template-columns:48px minmax(45px,1fr) minmax(78px,auto)}}
</style>
