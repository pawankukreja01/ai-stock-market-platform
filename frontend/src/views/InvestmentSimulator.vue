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

    <section class="panel strategy-panel">
      <div class="panel-heading">
        <div>
          <p class="eyebrow">OUT-OF-SAMPLE STRATEGY TESTING</p>
          <h2>Strategy backtesting</h2>
          <p>Compare a walk-forward ML strategy with Buy &amp; Hold and SMA 200 using the selected stock's available history.</p>
        </div>
        <span class="strategy-tag">Historical research</span>
      </div>

      <form class="simulation-form backtest-form" @submit.prevent="runStrategyBacktest">
        <label class="field">
          <span>ML model</span>
          <select v-model="backtestForm.model">
            <option value="linear_regression">Linear Regression</option>
            <option value="random_forest">Random Forest</option>
            <option value="xgboost">XGBoost</option>
          </select>
        </label>

        <label class="field">
          <span>Prediction horizon</span>
          <select v-model="backtestForm.horizon">
            <option value="1">1 trading day</option>
            <option value="5">5 trading days</option>
            <option value="20">20 trading days</option>
            <option value="60">60 trading days</option>
            <option value="126">126 trading days</option>
            <option value="252">252 trading days</option>
          </select>
        </label>

        <label class="field">
          <span>Transaction cost (bps)</span>
          <input v-model="backtestForm.transaction_cost_bps" type="number" min="0" step="any" required />
        </label>

        <label class="field">
          <span>Slippage (bps)</span>
          <input v-model="backtestForm.slippage_bps" type="number" min="0" step="any" required />
        </label>

        <label class="field">
          <span>Prediction threshold (decimal return)</span>
          <input v-model="backtestForm.threshold" type="number" step="any" required />
        </label>

        <div class="form-actions">
          <button class="primary-button" type="submit" :disabled="backtestLoading || loadingStocks || !form.symbol">
            {{ backtestLoading ? "Running walk-forward test…" : "Run strategy backtest" }}
          </button>
        </div>
      </form>

      <p class="form-note">
        The API uses expanding-window walk-forward training and needs at least 1,200 stored historical observations. A 0.01 threshold means a predicted return greater than 1%. Signals generated at a close execute at the next session close; the ML strategy then holds for the selected number of return sessions. Entry and exit costs are included. Historical returns use unadjusted closes, so dividends are excluded. Longer horizons may require more than 1,200 observations.
      </p>
    </section>

    <div v-if="backtestError" class="error-message">
      <strong>Strategy backtest could not be completed</strong>
      <p>{{ backtestError }}</p>
    </div>

    <div v-if="backtestLoading" class="loading-message">
      Training walk-forward folds and calculating strategy results. This may take a little while.
    </div>

    <template v-if="backtest">
      <section class="summary-grid">
        <article class="summary-card">
          <span class="summary-label">Out-of-sample period</span>
          <strong class="backtest-summary-value">{{ backtest.backtest_period.start_date }}</strong>
          <small>to {{ backtest.backtest_period.end_date }}</small>
        </article>
        <article class="summary-card">
          <span class="summary-label">Prediction horizon</span>
          <strong>{{ backtest.horizon_label }}</strong>
          <small>{{ backtest.horizon }} trading days</small>
        </article>
        <article class="summary-card">
          <span class="summary-label">Walk-forward folds</span>
          <strong>{{ backtest.configuration.folds }}</strong>
          <small>{{ backtest.final_validation?.metrics?.selected_model?.observations ?? 0 }} forecast observations evaluated</small>
        </article>
        <article class="summary-card">
          <span class="summary-label">Evaluation observations</span>
          <strong>{{ backtest.backtest_period.observations }}</strong>
          <small>Daily returns in strategy comparison</small>
        </article>
      </section>

      <section class="panel chart-panel">
        <div class="panel-heading chart-heading">
          <div>
            <h2>{{ backtest.symbol }} strategy equity curves</h2>
            <p>Growth of a normalised 1.00 starting value over the out-of-sample period.</p>
          </div>
          <span class="strategy-tag">{{ backtest.model_name }}</span>
        </div>
        <div ref="backtestChartElement" class="growth-chart" role="img" :aria-label="`${backtest.symbol} walk-forward strategy equity curves`"></div>
      </section>

      <section class="panel backtest-table-panel">
        <div class="panel-heading">
          <div>
            <h2>Strategy comparison</h2>
            <p>All strategies are measured over the same out-of-sample window and cost assumptions.</p>
          </div>
        </div>
        <div class="table-scroll">
          <table class="backtest-table">
            <thead>
              <tr>
                <th>Strategy</th><th>Total return</th><th>Annualised return</th><th>Annualised volatility</th><th>Max drawdown</th><th>Sharpe</th><th>Sortino</th><th>Win rate</th><th>Profit factor</th><th>Trades</th><th>Trading cost</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in backtestStrategyRows" :key="row.key">
                <td><strong>{{ row.label }}</strong></td>
                <td>{{ backtestPercent(row.metrics.cumulative_return) }}</td>
                <td>{{ backtestPercent(row.metrics.annualised_return) }}</td>
                <td>{{ backtestPercent(row.metrics.annualised_volatility) }}</td>
                <td>{{ backtestPercent(row.metrics.maximum_drawdown) }}</td>
                <td>{{ backtestNumber(row.metrics.sharpe_ratio) }}</td>
                <td>{{ backtestNumber(row.metrics.sortino_ratio) }}</td>
                <td>{{ backtestPercent(row.metrics.win_rate) }}</td>
                <td>{{ backtestNumber(row.metrics.profit_factor) }}</td>
                <td>{{ row.metrics.trades ?? "—" }}</td>
                <td>{{ backtestPercent(row.metrics.total_trading_cost) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="backtest.analysis?.interpretation" class="analysis-copy">{{ backtest.analysis.interpretation }}</p>
      </section>

      <section class="panel backtest-table-panel">
        <div class="panel-heading">
          <div>
            <h2>Trade &amp; cost diagnostics</h2>
            <p>Completed round trips, market exposure, gross-versus-net returns and execution friction for each strategy.</p>
          </div>
        </div>
        <div class="table-scroll">
          <table class="backtest-table diagnostics-table">
            <thead>
              <tr>
                <th>Strategy</th>
                <th>Completed trades</th>
                <th>Win rate</th>
                <th>Avg holding (sessions)</th>
                <th>Time invested</th>
                <th>Gross return</th>
                <th>Net return</th>
                <th>Gross-to-net drag</th>
                <th>Transaction costs*</th>
                <th>Slippage*</th>
                <th>Turnover (x)</th>
                <th>Avg winning trade</th>
                <th>Avg losing trade</th>
                <th>Profit factor</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in backtestStrategyRows" :key="`diagnostics-${row.key}`">
                <td><strong>{{ row.label }}</strong></td>
                <td>{{ row.metrics.completed_trades ?? row.metrics.trades ?? 0 }}</td>
                <td>{{ backtestPercent(row.metrics.win_rate) }}</td>
                <td>{{ backtestNumber(row.metrics.average_holding_sessions) }}</td>
                <td>{{ backtestPercent(row.metrics.exposure_pct) }}</td>
                <td>{{ backtestPercent(row.metrics.gross_cumulative_return) }}</td>
                <td>{{ backtestPercent(row.metrics.net_cumulative_return ?? row.metrics.cumulative_return) }}</td>
                <td>{{ backtestPercent(row.metrics.gross_to_net_return_drag) }}</td>
                <td>{{ backtestPercent(row.metrics.total_transaction_cost) }}</td>
                <td>{{ backtestPercent(row.metrics.total_slippage_cost) }}</td>
                <td>{{ backtestNumber(row.metrics.total_turnover) }}</td>
                <td>{{ backtestPercent(row.metrics.average_winning_trade_return) }}</td>
                <td>{{ backtestPercent(row.metrics.average_losing_trade_return) }}</td>
                <td>{{ backtestNumber(row.metrics.profit_factor) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="analysis-copy diagnostics-note">
          <p><strong>Closed-trade win rate:</strong> calculated from completed round trips, not daily returns. Buy &amp; Hold is normally one continuous position; a 100% win rate means that single completed position was profitable.</p>
          <p><strong>*Cost units:</strong> transaction cost and slippage are summed as return-space deductions against the normalised starting capital. They are not USD cash fee totals. Gross-to-net drag is the difference between compounded gross and net strategy returns.</p>
          <p><strong>Turnover:</strong> sum of absolute changes in portfolio exposure. One fully closed long round trip contributes approximately 2.00x.</p>
        </div>
      </section>

      <section class="panel backtest-table-panel trade-ledgers-panel">
        <div class="panel-heading">
          <div>
            <h2>Completed-trade ledger</h2>
            <p>Individual entries and exits used to calculate completed-trade statistics.</p>
          </div>
        </div>
        <details v-for="row in backtestStrategyRows" :key="`trade-ledger-${row.key}`" class="trade-ledger-details">
          <summary>{{ row.label }} · {{ row.trades.length }} completed trades</summary>
          <div v-if="row.trades.length" class="table-scroll">
            <table class="backtest-table trade-ledger-table">
              <thead>
                <tr><th>#</th><th>Entry date</th><th>Exit date</th><th>Holding sessions</th><th>Gross trade return</th><th>Net trade return</th><th>Transaction cost*</th><th>Slippage*</th><th>Combined cost*</th><th>Outcome</th></tr>
              </thead>
              <tbody>
                <tr v-for="(trade, tradeIndex) in row.trades" :key="`${row.key}-${trade.entry_date}-${tradeIndex}`">
                  <td>{{ tradeIndex + 1 }}</td>
                  <td>{{ backtestTradeDate(trade.entry_date) }}</td>
                  <td>{{ backtestTradeDate(trade.exit_date) }}</td>
                  <td>{{ trade.holding_sessions ?? "—" }}</td>
                  <td>{{ backtestPercent(trade.gross_return) }}</td>
                  <td>{{ backtestPercent(trade.net_return ?? trade.return) }}</td>
                  <td>{{ backtestPercent(trade.transaction_cost) }}</td>
                  <td>{{ backtestPercent(trade.slippage_cost) }}</td>
                  <td>{{ backtestPercent(trade.total_cost) }}</td>
                  <td>{{ Number(trade.net_return ?? trade.return) > 0 ? "Win" : Number(trade.net_return ?? trade.return) < 0 ? "Loss" : "Flat" }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else class="empty-ledger">No completed trades were recorded for this strategy and test window.</p>
        </details>
        <p class="ledger-footnote">*Cost values use the same normalised return-space units described above; they are not currency amounts.</p>
      </section>

      <section class="panel backtest-table-panel">
        <div class="panel-heading">
          <div>
            <h2>Forecast validation against simple baselines</h2>
            <p>Regression error and direction metrics for the same out-of-sample forecast dates.</p>
          </div>
        </div>
        <div class="table-scroll">
          <table class="backtest-table validation-table">
            <thead><tr><th>Forecast source</th><th>MAE</th><th>RMSE</th><th>Directional accuracy</th><th>Balanced directional accuracy</th><th>Observations</th></tr></thead>
            <tbody>
              <tr v-for="row in backtestValidationRows" :key="row.key">
                <td><strong>{{ row.label }}</strong></td>
                <td>{{ backtestPercent(row.mae) }}</td>
                <td>{{ backtestPercent(row.rmse) }}</td>
                <td>{{ backtestPercent(row.directional_accuracy) }}</td>
                <td>{{ backtestPercent(row.balanced_directional_accuracy) }}</td>
                <td>{{ row.observations }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="panel backtest-table-panel">
        <div class="panel-heading">
          <div>
            <h2>Transaction-cost and slippage sensitivity</h2>
            <p>{{ backtest.sensitivity.grid.scenario_count }} scenarios; the same OOS predictions are reused while frictions change.</p>
          </div>
        </div>
        <div class="table-scroll">
          <table class="backtest-table sensitivity-table">
            <thead><tr><th>Transaction cost</th><th>Slippage</th><th>Combined friction</th><th>ML gross return</th><th>ML net return</th><th>Return drag</th><th>ML transaction costs*</th><th>ML slippage*</th><th>ML annualised return</th><th>ML max drawdown</th><th>Selected</th></tr></thead>
            <tbody>
              <tr v-for="scenario in backtestSensitivityRows" :key="scenario.scenario_id" :class="{ 'selected-scenario': scenario.is_selected_configuration }">
                <td>{{ backtestNumber(scenario.transaction_cost_bps) }} bps</td>
                <td>{{ backtestNumber(scenario.slippage_bps) }} bps</td>
                <td>{{ backtestNumber(scenario.combined_friction_bps) }} bps</td>
                <td>{{ backtestPercent(scenario.mlMetrics.gross_cumulative_return) }}</td>
                <td>{{ backtestPercent(scenario.mlMetrics.net_cumulative_return ?? scenario.mlMetrics.cumulative_return) }}</td>
                <td>{{ backtestPercent(scenario.mlMetrics.gross_to_net_return_drag) }}</td>
                <td>{{ backtestPercent(scenario.mlMetrics.total_transaction_cost) }}</td>
                <td>{{ backtestPercent(scenario.mlMetrics.total_slippage_cost) }}</td>
                <td>{{ backtestPercent(scenario.mlMetrics.annualised_return) }}</td>
                <td>{{ backtestPercent(scenario.mlMetrics.maximum_drawdown) }}</td>
                <td>{{ scenario.is_selected_configuration ? "Yes" : "—" }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <p class="form-note result-note">*Transaction-cost and slippage totals are expressed as return-space deductions against the normalised starting capital, not absolute broker fees in USD. Gross-to-net drag is the compounded gross return less the compounded net return.</p>

      <details class="panel folds-panel">
        <summary>Walk-forward fold details ({{ backtest.folds.length }} folds)</summary>
        <div class="table-scroll">
          <table class="backtest-table">
            <thead><tr><th>Fold</th><th>Train observations</th><th>Test observations</th><th>Gap</th><th>Train start</th><th>Train end</th><th>Test start</th><th>Test end</th></tr></thead>
            <tbody>
              <tr v-for="fold in backtest.folds" :key="fold.fold">
                <td>{{ fold.fold }}</td><td>{{ fold.train_size }}</td><td>{{ fold.test_size }}</td><td>{{ fold.gap }}</td><td>{{ fold.train_start_date || "—" }}</td><td>{{ fold.train_end_date || "—" }}</td><td>{{ fold.test_start_date || "—" }}</td><td>{{ fold.test_end_date || "—" }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </details>

      <section class="assumptions">
        <h3>Backtest methodology and limitations</h3>
        <p v-for="(note, index) in backtest.notes" :key="index">{{ note }}</p>
        <p v-for="(limitation, index) in (backtest.final_validation?.limitations || [])" :key="`validation-limitation-${index}`">{{ limitation }}</p>
        <p><strong>Price basis:</strong> {{ backtest.price_basis?.description }}</p>
        <p>These are historical research results, not investment advice or a forecast of future returns. Model performance must be monitored on genuinely new data before being relied upon.</p>
      </section>
    </template>

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
  computed,
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
  getBacktestResults,
} from "../services/api";

const stocks = ref([]);
const loadingStocks = ref(false);
const loading = ref(false);
const error = ref("");
const simulation = ref(null);
const chartElement = ref(null);

const backtest = ref(null);
const backtestChartElement = ref(null);
const backtestLoading = ref(false);
const backtestError = ref("");
const backtestForm = reactive({
  model: "random_forest",
  horizon: "5",
  transaction_cost_bps: "5",
  slippage_bps: "5",
  threshold: "0",
});

const backtestStrategyRows = computed(() => {
  const strategies = backtest.value?.strategies || {};
  const modelName = backtest.value?.model_name || "Selected model";

  return [
    { key: "ml", label: `${modelName} strategy`, metrics: strategies.ml?.metrics, trades: strategies.ml?.trades || [] },
    { key: "buy_and_hold", label: "Buy & Hold", metrics: strategies.buy_and_hold?.metrics, trades: strategies.buy_and_hold?.trades || [] },
    { key: "sma", label: "SMA 200", metrics: strategies.sma?.metrics, trades: strategies.sma?.trades || [] },
  ].filter((row) => row.metrics);
});

const backtestValidationRows = computed(() => {
  const metrics = backtest.value?.final_validation?.metrics || {};
  const labels = [
    ["selected_model", backtest.value?.model_name || "Selected model"],
    ["zero_return", "Zero-return baseline"],
    ["historical_mean", "Historical-mean baseline"],
    ["momentum", "Momentum baseline"],
  ];

  return labels
    .filter(([key]) => metrics[key])
    .map(([key, label]) => ({ key, label, ...metrics[key] }));
});

const backtestSensitivityRows = computed(() => {
  return (backtest.value?.sensitivity?.scenarios || []).map((scenario) => ({
    ...scenario,
    mlMetrics: scenario.strategies?.ml || {},
  }));
});

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

async function runStrategyBacktest() {
  backtestError.value = "";

  if (!form.symbol) {
    backtestError.value = "Please select a stock before running a strategy backtest.";
    return;
  }

  const transactionCost = Number(backtestForm.transaction_cost_bps);
  const slippage = Number(backtestForm.slippage_bps);
  const threshold = Number(backtestForm.threshold);
  const horizon = Number(backtestForm.horizon);

  if (
    !Number.isFinite(transactionCost) ||
    !Number.isFinite(slippage) ||
    !Number.isFinite(threshold) ||
    transactionCost < 0 ||
    slippage < 0
  ) {
    backtestError.value = "Costs and threshold must be finite numbers; costs cannot be negative.";
    return;
  }

  backtestLoading.value = true;
  backtest.value = null;

  try {
    const result = await getBacktestResults(
      form.symbol,
      horizon,
      backtestForm.model,
      transactionCost,
      slippage,
      threshold
    );

    backtest.value = result;
    await nextTick();
    await renderBacktestChart();
  } catch (requestError) {
    backtestError.value = getErrorMessage(requestError);
  } finally {
    backtestLoading.value = false;
  }
}

async function renderBacktestChart() {
  const result = backtest.value;
  if (!backtestChartElement.value || !result?.strategies) return;

  const definitions = [
    { key: "ml", label: `ML · ${result.model_name}`, color: "#2563eb" },
    { key: "buy_and_hold", label: "Buy & Hold", color: "#16a34a" },
    { key: "sma", label: "SMA 200", color: "#d97706" },
  ];

  const traces = definitions
    .map((definition) => {
      const curve = result.strategies[definition.key]?.equity_curve;
      if (!curve || !Array.isArray(curve.dates) || !Array.isArray(curve.values)) return null;

      return {
        x: [result.backtest_period.start_date, ...curve.dates],
        y: [1, ...curve.values.map(Number)],
        type: "scatter",
        mode: "lines",
        name: definition.label,
        line: { color: definition.color, width: 2.4 },
        hovertemplate: "%{x}<br>Growth of 1.00: %{y:.4f}<extra></extra>",
      };
    })
    .filter(Boolean);

  await Plotly.react(
    backtestChartElement.value,
    traces,
    {
      autosize: true,
      height: 420,
      margin: { l: 70, r: 25, t: 20, b: 60 },
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      font: { family: "Inter, -apple-system, BlinkMacSystemFont, sans-serif", color: "#64748b", size: 12 },
      hovermode: "x unified",
      legend: { orientation: "h", x: 0, y: 1.12 },
      xaxis: { title: "Date", type: "date", gridcolor: "#eef2f7", linecolor: "#dbe3ed" },
      yaxis: { title: "Growth of 1.00", tickformat: ".2f", gridcolor: "#eef2f7", zerolinecolor: "#cbd5e1" },
    },
    { responsive: true, displaylogo: false, modeBarButtonsToRemove: ["select2d", "lasso2d"] }
  );
}

function backtestPercent(value) {
  if (value == null || !Number.isFinite(Number(value))) return "—";
  return `${(Number(value) * 100).toFixed(2)}%`;
}

function backtestNumber(value) {
  if (value == null || !Number.isFinite(Number(value))) return "—";
  return Number(value).toFixed(2);
}

function backtestTradeDate(value) {
  if (!value) return "—";
  return String(value).slice(0, 10);
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

  if (backtestChartElement.value && backtest.value) {
    Plotly.Plots.resize(backtestChartElement.value);
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

  if (backtestChartElement.value) {
    Plotly.purge(backtestChartElement.value);
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

.strategy-tag {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
  border: 1px solid #dbe4ee;
  border-radius: 999px;
  padding: 7px 10px;
  color: #475569;
  background: #f8fafc;
  font-size: 11px;
  font-weight: 700;
}

.backtest-form {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.backtest-form .form-actions {
  align-items: stretch;
}

.backtest-summary-value {
  font-size: 18px !important;
}

.backtest-table-panel {
  min-width: 0;
}

.table-scroll {
  width: 100%;
  overflow-x: auto;
}

.backtest-table {
  width: 100%;
  min-width: 1050px;
  border-collapse: collapse;
  font-size: 12px;
  text-align: right;
}

.backtest-table th,
.backtest-table td {
  padding: 12px 13px;
  border-bottom: 1px solid #eef2f7;
  white-space: nowrap;
}

.backtest-table th {
  color: #64748b;
  background: #f8fafc;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: .03em;
  text-transform: uppercase;
}

.backtest-table th:first-child,
.backtest-table td:first-child {
  position: sticky;
  left: 0;
  z-index: 1;
  text-align: left;
  background: #fff;
}

.backtest-table th:first-child {
  background: #f8fafc;
}

.backtest-table tbody tr:last-child td {
  border-bottom: 0;
}

.backtest-table strong {
  color: #0f172a;
}

.analysis-copy {
  margin: 0;
  padding: 15px 18px;
  border-top: 1px solid #eef2f7;
  color: #475569;
  font-size: 12px;
  line-height: 1.65;
}

.selected-scenario td {
  background: #eff6ff;
  font-weight: 700;
}

.selected-scenario td:first-child {
  background: #eff6ff;
}

.folds-panel {
  padding: 0;
}

.folds-panel summary {
  padding: 18px 22px;
  color: #334155;
  cursor: pointer;
  font-size: 13px;
  font-weight: 750;
}

.diagnostics-table,
.trade-ledger-table {
  min-width: 1450px;
}

.trade-ledgers-panel .panel-heading {
  border-bottom: 1px solid #eef2f7;
}

.trade-ledger-details {
  border-bottom: 1px solid #eef2f7;
}

.trade-ledger-details:last-of-type {
  border-bottom: 0;
}

.trade-ledger-details summary {
  padding: 15px 22px;
  color: #334155;
  cursor: pointer;
  font-size: 12px;
  font-weight: 750;
}

.trade-ledger-details[open] summary {
  border-bottom: 1px solid #eef2f7;
  background: #f8fafc;
}

.trade-ledger-table {
  min-width: 1100px;
}

.diagnostics-note p {
  margin: 4px 0;
}

.empty-ledger,
.ledger-footnote {
  margin: 0;
  padding: 13px 22px;
  color: #64748b;
  font-size: 12px;
}

.ledger-footnote {
  border-top: 1px solid #eef2f7;
  color: #94a3b8;
}

.folds-panel[open] summary {
  border-bottom: 1px solid #eef2f7;
}

.folds-panel .table-scroll {
  padding-bottom: 4px;
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

  .backtest-form {
    grid-template-columns: repeat(2, minmax(0, 1fr));
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

  .backtest-form {
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