<template>
  <div class="simulator-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">HISTORICAL INVESTMENT TOOL</p>
        <h1>Investment Simulator</h1>
        <p class="subtitle">
          Explore how a hypothetical lump-sum investment and recurring
          contributions would have performed using historical prices.
        </p>
      </div>

      <span class="status-badge">
        <span class="status-dot"></span>
        Historical simulation
      </span>
    </header>

    <section class="panel">
      <div class="panel-heading">
        <div>
          <h2>Configure your investment</h2>
          <p>Change the assumptions and run a new simulation.</p>
        </div>
      </div>

      <form class="simulation-form" @submit.prevent="runSimulation">
        <label class="field">
          <span>Stock</span>
          <select v-model="form.symbol" required :disabled="loadingStocks">
            <option value="" disabled>Select a stock</option>
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
          <span>Initial investment (USD)</span>
          <input
            v-model="form.initial_investment"
            type="number"
            min="0.01"
            step="any"
            required
          />
        </label>

        <label class="field">
          <span>Monthly contribution (USD)</span>
          <input
            v-model="form.monthly_contribution"
            type="number"
            min="0"
            step="any"
          />
        </label>

        <label class="field">
          <span>Start date</span>
          <input v-model="form.start_date" type="date" required />
        </label>

        <label class="field">
          <span>End date</span>
          <input
            v-model="form.end_date"
            type="date"
            :min="form.start_date"
            required
          />
        </label>

        <div class="form-actions">
          <button class="primary-button" type="submit" :disabled="loading">
            {{ loading ? "Calculating…" : "Run simulation" }}
          </button>
        </div>
      </form>

      <p class="form-note">
        Fractional shares are allowed. Monthly contributions are invested
        on the first available trading day of each subsequent calendar month.
      </p>
    </section>

    <div v-if="error" class="error-message">
      <strong>Simulation could not be completed</strong>
      <p>{{ error }}</p>
      <p>Try a different date range or check that historical prices are available.</p>
    </div>

    <div v-if="loading" class="loading-message">
      Calculating your historical investment…
    </div>

    <template v-if="simulation">
      <section class="summary-grid">
        <article class="summary-card">
          <span class="summary-label">Ending value</span>
          <strong>{{ money(simulation.summary.ending_value) }}</strong>
          <small>
            {{ simulation.actual_period.end_date }}
          </small>
        </article>

        <article class="summary-card">
          <span class="summary-label">Total invested</span>
          <strong>{{ money(simulation.summary.total_invested) }}</strong>
          <small>
            Initial investment + contributions
          </small>
        </article>

        <article class="summary-card">
          <span class="summary-label">Profit / loss</span>
          <strong :class="toneClass(simulation.summary.profit_loss)">
            {{ signedMoney(simulation.summary.profit_loss) }}
          </strong>
          <small :class="toneClass(simulation.summary.total_return_pct)">
            {{ signedPercent(simulation.summary.total_return_pct) }} return
          </small>
        </article>

        <article class="summary-card">
          <span class="summary-label">Money-weighted annualised return</span>
          <strong :class="toneClass(
            simulation.summary.annualized_money_weighted_return_pct
          )">
            {{ signedPercent(
              simulation.summary.annualized_money_weighted_return_pct
            ) }}
          </strong>
          <small>Estimated from dated cash flows</small>
        </article>
      </section>

      <section class="panel chart-panel">
        <div class="panel-heading chart-heading">
          <div>
            <h2>{{ simulation.symbol }} investment growth</h2>
            <p>
              {{ simulation.actual_period.start_date }}
              to
              {{ simulation.actual_period.end_date }}
            </p>
          </div>

          <div class="chart-legend">
            <span><i class="legend-dot value-dot"></i>Investment value</span>
            <span><i class="legend-dot invested-dot"></i>Total invested</span>
          </div>
        </div>

        <div
          ref="chartElement"
          class="growth-chart"
          role="img"
          :aria-label="`${simulation.symbol} historical investment value and invested capital chart`"
        ></div>

        <div class="chart-footer">
          <span>
            {{ simulation.actual_period.price_observations }}
            trading observations
          </span>
          <span>
            {{ simulation.summary.contribution_count }}
            monthly contributions
          </span>
        </div>
      </section>

      <section class="panel details-panel">
        <div class="panel-heading">
          <div>
            <h2>Simulation breakdown</h2>
            <p>Key figures for this hypothetical scenario.</p>
          </div>
        </div>

        <div class="details-grid">
          <div class="detail-row">
            <span>Stock</span>
            <strong>
              {{ simulation.symbol }} — {{ simulation.company_name }}
            </strong>
          </div>

          <div class="detail-row">
            <span>Initial investment</span>
            <strong>{{ money(simulation.summary.initial_investment) }}</strong>
          </div>

          <div class="detail-row">
            <span>Monthly contribution</span>
            <strong>{{ money(simulation.summary.monthly_contribution) }}</strong>
          </div>

          <div class="detail-row">
            <span>Additional contributions</span>
            <strong>
              {{ money(simulation.summary.additional_contributions) }}
            </strong>
          </div>

          <div class="detail-row">
            <span>Initial adjusted price</span>
            <strong>
              {{ money(simulation.summary.initial_adjusted_price) }}
            </strong>
          </div>

          <div class="detail-row">
            <span>Ending adjusted price</span>
            <strong>
              {{ money(simulation.summary.ending_adjusted_price) }}
            </strong>
          </div>

          <div class="detail-row">
            <span>Initial investment date</span>
            <strong>{{ simulation.actual_period.start_date }}</strong>
          </div>

          <div class="detail-row">
            <span>Last available price date</span>
            <strong>{{ simulation.summary.final_date }}</strong>
          </div>
        </div>
      </section>

      <section class="assumptions">
        <h3>Methodology and assumptions</h3>
        <p>{{ simulation.assumptions.price_basis }}</p>
        <p>{{ simulation.assumptions.contribution_schedule }}</p>
        <p>{{ simulation.assumptions.dividends }}</p>
        <p>
          Transaction fees and taxes are not included.
          Past historical returns do not predict future performance.
        </p>
      </section>
    </template>
  </div>
</template>

<script setup>
import {
  nextTick,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
} from "vue";

import Plotly from "plotly.js-finance-dist-min";

import {
  getStocks,
  getInvestmentSimulation,
} from "../services/api";

const stocks = ref([]);
const loadingStocks = ref(false);
const loading = ref(false);
const error = ref("");
const simulation = ref(null);
const chartElement = ref(null);

function localDateString(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

function yearsAgoDate(years) {
  const date = new Date();
  date.setFullYear(date.getFullYear() - years);
  return localDateString(date);
}

const form = reactive({
  symbol: "",
  start_date: yearsAgoDate(1),
  end_date: localDateString(new Date()),
  initial_investment: "10000",
  monthly_contribution: "200",
});

function normalizeStocks(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
}

function getErrorMessage(requestError) {
  const data = requestError?.response?.data;

  if (typeof data === "string") return data;
  if (data?.error) return data.error;
  if (data?.detail) return data.detail;

  if (data && typeof data === "object") {
    return Object.entries(data)
      .map(([key, value]) => {
        return `${key}: ${
          Array.isArray(value) ? value.join(", ") : String(value)
        }`;
      })
      .join(" | ");
  }

  return requestError?.message || "An unexpected error occurred.";
}

async function loadStocks() {
  loadingStocks.value = true;

  try {
    const data = await getStocks();

    stocks.value = normalizeStocks(data).filter(
      (stock) => stock.is_active !== false
    );

    if (!form.symbol && stocks.value.length) {
      form.symbol = stocks.value.some(
        (stock) => stock.symbol === "AAPL"
      )
        ? "AAPL"
        : stocks.value[0].symbol;
    }
  } catch (requestError) {
    error.value = getErrorMessage(requestError);
  } finally {
    loadingStocks.value = false;
  }
}

async function runSimulation() {
  error.value = "";

  if (!form.symbol) {
    error.value = "Please select a stock.";
    return;
  }

  if (!form.start_date || !form.end_date) {
    error.value = "Please select both start and end dates.";
    return;
  }

  if (form.end_date <= form.start_date) {
    error.value = "The end date must be after the start date.";
    return;
  }

  const initialInvestment = Number(form.initial_investment);
  const monthlyContribution =
    form.monthly_contribution === ""
      ? 0
      : Number(form.monthly_contribution);

  if (!Number.isFinite(initialInvestment) || initialInvestment <= 0) {
    error.value = "Initial investment must be greater than zero.";
    return;
  }

  if (
    !Number.isFinite(monthlyContribution) ||
    monthlyContribution < 0
  ) {
    error.value = "Monthly contribution cannot be negative.";
    return;
  }

  loading.value = true;
  simulation.value = null;

  try {
    const result = await getInvestmentSimulation({
      symbol: form.symbol,
      start_date: form.start_date,
      end_date: form.end_date,
      initial_investment: initialInvestment,
      monthly_contribution: monthlyContribution,
    });

    simulation.value = result;

    await nextTick();
    await renderChart();
  } catch (requestError) {
    error.value = getErrorMessage(requestError);
  } finally {
    loading.value = false;
  }
}

async function renderChart() {
  const data = simulation.value;

  if (
    !chartElement.value ||
    !data ||
    !Array.isArray(data.curve) ||
    data.curve.length === 0
  ) {
    return;
  }

  const dates = data.curve.map((point) => point.date);
  const portfolioValues = data.curve.map(
    (point) => point.portfolio_value
  );
  const investedValues = data.curve.map(
    (point) => point.invested_capital
  );

  const traces = [
    {
      x: dates,
      y: portfolioValues,
      type: "scatter",
      mode: "lines",
      name: "Investment value",
      line: {
        color: "#2563eb",
        width: 2.5,
      },
      hovertemplate: "%{x}<br>Value: $%{y:,.2f}<extra></extra>",
    },
    {
      x: dates,
      y: investedValues,
      type: "scatter",
      mode: "lines",
      name: "Total invested",
      line: {
        color: "#16a34a",
        width: 2,
        dash: "dot",
      },
      hovertemplate: "%{x}<br>Invested: $%{y:,.2f}<extra></extra>",
    },
  ];

  const layout = {
    autosize: true,
    height: 400,
    margin: {
      l: 70,
      r: 25,
      t: 20,
      b: 60,
    },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: {
      family: "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
      color: "#64748b",
      size: 12,
    },
    hovermode: "x unified",
    legend: {
      orientation: "h",
      x: 0,
      y: 1.12,
    },
    xaxis: {
      title: "Date",
      type: "date",
      gridcolor: "#eef2f7",
      linecolor: "#dbe3ed",
      tickfont: {
        size: 11,
      },
    },
    yaxis: {
      title: "Value (USD)",
      tickprefix: "$",
      tickformat: ",.0f",
      rangemode: "tozero",
      gridcolor: "#eef2f7",
      zerolinecolor: "#cbd5e1",
    },
  };

  await Plotly.react(
    chartElement.value,
    traces,
    layout,
    {
      responsive: true,
      displaylogo: false,
      modeBarButtonsToRemove: ["select2d", "lasso2d"],
    }
  );
}

function handleResize() {
  if (chartElement.value && simulation.value) {
    Plotly.Plots.resize(chartElement.value);
  }
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

function signedMoney(value) {
  if (value == null || !Number.isFinite(Number(value))) {
    return "—";
  }

  const numeric = Number(value);
  const prefix = numeric > 0 ? "+" : numeric < 0 ? "−" : "";

  return `${prefix}${money(Math.abs(numeric))}`;
}

function signedPercent(value) {
  if (value == null || !Number.isFinite(Number(value))) {
    return "Not available";
  }

  const numeric = Number(value);
  const prefix = numeric > 0 ? "+" : numeric < 0 ? "−" : "";

  return `${prefix}${Math.abs(numeric).toFixed(2)}%`;
}

function toneClass(value) {
  if (value == null || !Number.isFinite(Number(value))) {
    return "neutral-value";
  }

  if (Number(value) > 0) return "positive-value";
  if (Number(value) < 0) return "negative-value";

  return "neutral-value";
}

onMounted(async () => {
  await loadStocks();

  if (form.symbol) {
    await runSimulation();
  }

  window.addEventListener("resize", handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);

  if (chartElement.value) {
    Plotly.purge(chartElement.value);
  }
});
</script>

<style scoped>
.simulator-page {
  max-width: 1500px;
  margin: 0 auto;
  padding: 28px clamp(16px, 3vw, 36px) 40px;
  display: flex;
  flex-direction: column;
  gap: 22px;
  color: #111827;
}

.page-header,
.panel-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
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

h3 {
  margin: 0 0 12px;
  font-size: 15px;
}

.subtitle,
.panel-heading p {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 14px;
  line-height: 1.6;
}

.status-badge {
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

.panel,
.summary-card {
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 3px 12px rgb(15 23 42 / 3%);
}

.panel {
  overflow: hidden;
}

.panel-heading {
  padding: 20px 22px;
  border-bottom: 1px solid #eef2f7;
}

.simulation-form {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  padding: 22px;
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
  height: 42px;
  border: 1px solid #dbe3ed;
  border-radius: 8px;
  outline: none;
  padding: 0 11px;
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

.form-actions {
  display: flex;
  align-items: end;
}

.primary-button,
.secondary-button {
  min-height: 41px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 0 16px;
  background: #fff;
  color: #334155;
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

.primary-button {
  width: 100%;
  border-color: #172554;
  background: #172554;
  color: #fff;
}

.primary-button:hover:not(:disabled) {
  background: #1e3a8a;
}

.primary-button:disabled {
  cursor: not-allowed;
  opacity: .55;
}

.form-note {
  margin: 0;
  padding: 0 22px 20px;
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.6;
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
  font-size: clamp(20px, 2vw, 27px);
  letter-spacing: -.03em;
  overflow-wrap: anywhere;
}

.summary-card small {
  color: #94a3b8;
  font-size: 12px;
}

.chart-heading {
  flex-wrap: wrap;
  align-items: center;
}

.chart-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  color: #64748b;
  font-size: 12px;
}

.chart-legend span {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.legend-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.value-dot {
  background: #2563eb;
}

.invested-dot {
  background: #16a34a;
}

.growth-chart {
  width: 100%;
  min-height: 400px;
  padding: 5px 10px 0;
}

.chart-footer {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  padding: 14px 22px;
  border-top: 1px solid #eef2f7;
  color: #94a3b8;
  font-size: 12px;
}

.details-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  padding: 10px 22px 18px;
  column-gap: 32px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  padding: 13px 0;
  border-bottom: 1px solid #eef2f7;
  font-size: 13px;
}

.detail-row span {
  color: #64748b;
}

.detail-row strong {
  text-align: right;
  overflow-wrap: anywhere;
}

.positive-value {
  color: #15803d !important;
}

.negative-value {
  color: #b91c1c !important;
}

.neutral-value {
  color: #475569;
}

.error-message {
  border: 1px solid #fecaca;
  border-radius: 12px;
  padding: 16px;
  background: #fef2f2;
  color: #b91c1c;
  font-size: 13px;
}

.error-message p {
  margin: 7px 0 0;
  line-height: 1.5;
}

.loading-message {
  padding: 35px 20px;
  text-align: center;
  color: #64748b;
  font-size: 13px;
}

.assumptions {
  padding: 18px 20px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fff;
  color: #64748b;
  font-size: 12px;
  line-height: 1.7;
}

.assumptions h3 {
  color: #334155;
}

.assumptions p {
  margin: 7px 0;
}

@media (max-width: 1100px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .simulator-page {
    padding: 20px 12px 30px;
    gap: 16px;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .simulation-form {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    padding: 16px;
  }

  .panel-heading {
    padding: 16px;
  }

  .form-note {
    padding: 0 16px 16px;
  }

  .growth-chart {
    min-height: 320px;
    padding: 0;
  }

  .chart-footer {
    padding: 14px 16px;
  }

  .details-grid {
    grid-template-columns: 1fr;
    padding: 8px 16px 16px;
  }
}

@media (max-width: 430px) {
  .simulation-form,
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .summary-card {
    min-height: 105px;
  }

  .chart-legend {
    gap: 9px;
  }
}
</style>