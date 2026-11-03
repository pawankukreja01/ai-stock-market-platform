
<template>
  <div class="recommendations-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">AI STOCK RESEARCH</p>
        <h1>Stock Recommendations</h1>
        <p class="subtitle">
          Understand US and UK stocks with evidence-based rankings, plain-language explanations
          and an illustrative allocation — not a promise of future returns.
        </p>
      </div>

      <button
        type="button"
        class="secondary-button"
        :disabled="loading"
        @click="loadRecommendations"
      >
        {{ loading ? "Analysing…" : "Refresh analysis" }}
      </button>
    </header>

    <section class="research-guide" aria-label="How to use MarketPulse recommendations">
      <div class="research-guide-heading">
        <span class="guide-label">START HERE</span>
        <h2>Find investments you understand, not just high scores.</h2>
        <p>Use the rankings as a shortlist to investigate. A high score does not tell you how much a stock will rise.</p>
      </div>
      <div class="guide-steps">
        <div><span class="guide-number">01</span><strong>Choose your horizon</strong><p>Set your time frame and risk comfort. The current research ranking adjusts its evidence weights for your selected holding period; these adjustments are not validated return forecasts.</p></div>
        <div><span class="guide-number">02</span><strong>Read the evidence</strong><p>Check price freshness, fundamentals, market risk, and news sentiment for every candidate.</p></div>
        <div><span class="guide-number">03</span><strong>Compare before acting</strong><p>Research the stock page and potential downside. Forecasts are not currently part of these rankings.</p></div>
      </div>
      <p class="guide-caution">Research-only preview · Not personalised financial advice · You can lose money, including your original investment.</p>
    </section>

    <section class="panel">
      <div class="section-heading">
        <div>
          <h2>Investment parameters</h2>
          <p>Adjust the inputs and run the analysis again.</p>
        </div>
      </div>

      <form class="parameters-grid" @submit.prevent="loadRecommendations">
        <div class="field">
          <label for="budget">Investment budget</label>
          <input
            id="budget"
            v-model="form.budget"
            type="number"
            min="0.01"
            step="0.01"
            required
          />
        </div>

        <div class="field">
          <label for="currency">Budget currency</label>
          <select id="currency" v-model="form.currency">
            <option value="USD">USD — US dollar</option>
            <option value="GBP">GBP — British pound</option>
          </select>
        </div>

        <div class="field">
          <label for="risk">Risk tolerance</label>
          <select id="risk" v-model="form.risk_tolerance">
            <option value="low">Conservative</option>
            <option value="moderate">Moderate</option>
            <option value="high">Aggressive</option>
          </select>
        </div>

        <div class="field">
          <label for="horizon">Investment horizon</label>
          <select id="horizon" v-model.number="form.horizon_months">
            <option :value="3">3 months</option>
            <option :value="6">6 months</option>
            <option :value="12">12 months</option>
            <option :value="24">24 months</option>
            <option :value="60">60 months</option>
          </select>
        </div>

        <div class="field">
          <label for="market">Market</label>
          <select id="market" v-model="form.market">
            <option value="">All available markets</option>
            <option value="NASDAQ">NASDAQ</option>
            <option value="NYSE">NYSE</option>
            <option value="LSE">London Stock Exchange (LSE)</option>
          </select>
        </div>

        <div class="field">
          <label for="candidate-count">Number of results</label>
          <select id="candidate-count" v-model.number="form.max_candidates">
            <option :value="5">5 stocks</option>
            <option :value="10">10 stocks</option>
            <option :value="20">20 stocks</option>
            <option :value="30">30 stocks</option>
          </select>
        </div>

        <div class="form-actions">
          <button class="primary-button" type="submit" :disabled="loading">
            {{ loading ? "Calculating…" : "Generate recommendations" }}
          </button>
        </div>
      </form>
    </section>

    <div v-if="error" class="notice error-notice" role="alert">
      <strong>Unable to load recommendations</strong>
      <p>{{ error }}</p>
      <p>
        Check that you are logged in and the Django backend is running.
      </p>
    </div>

    <div v-if="loading && !data" class="notice">
      Calculating stock rankings and whole-share allocation…
    </div>

    <template v-if="data">
      <section class="stats-grid">
        <article class="stat-card">
          <span>Candidate universe</span>
          <strong>{{ data.candidate_universe_size }}</strong>
          <small>Stocks considered</small>
        </article>

        <article class="stat-card">
          <span>Scored stocks</span>
          <strong>{{ data.scored_candidate_count }}</strong>
          <small>Stocks scored by the model</small>
        </article>

        <article class="stat-card">
          <span>Invested</span>
          <strong>{{ money(data.allocation?.invested) }}</strong>
          <small>Illustrative allocation</small>
        </article>

        <article class="stat-card">
          <span>Remaining cash</span>
          <strong>{{ money(data.allocation?.remaining_cash) }}</strong>
          <small>Not allocated to shares</small>
        </article>
      </section>

      <section class="panel">
        <div class="section-heading">
          <div>
            <h2>Ranked stocks</h2>
            <p>
              Showing {{ data.results?.length ?? 0 }} stocks.
              Scores are relative percentiles, not probabilities of profit. Your selected horizon adjusts provisional scoring weights.
            </p>
          </div>
          <span class="pill">{{ data.risk_tolerance }} risk profile</span>
        </div>

        <div v-if="!data.results?.length" class="empty-state">
          No recommendations were returned for these parameters.
          Try another market or candidate count.
        </div>

        <div v-else class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Rank</th>
                <th>Stock</th>
                <th>Sector</th>
                <th>Latest price</th>
                <th>Score</th>
                <th>Data availability</th>
              </tr>
            </thead>

            <tbody>
              <tr v-for="stock in data.results" :key="stock.symbol">
                <td>
                  <span class="rank-number">#{{ stock.rank }}</span>
                </td>
                <td>
                  <strong>{{ stock.symbol }}</strong>
                  <span class="company-name">{{ stock.company_name }}</span>
                  <span class="exchange-name">{{ stock.exchange }}</span>
                </td>
                <td>{{ stock.sector || "Unavailable" }}</td>
                <td>
                  {{ money(stock.latest_price, stock.currency) }}
                  <span class="company-name">
                    As of {{ stock.latest_price_date || "unknown date" }}
                  </span>
                </td>
                <td>
                  <strong>{{ number(stock.score) }}</strong>
                  <div class="score-track">
                    <div
                      class="score-fill"
                      :style="{ width: `${clampScore(stock.score)}%` }"
                    ></div>
                  </div>
                </td>
                <td>
                  <span
                    class="data-status"
                    :class="stock.data_quality?.fundamental_data_available
                      ? 'available'
                      : 'missing'"
                  >
                    {{
                      stock.data_quality?.fundamental_data_available
                        ? "Fundamentals available"
                        : "Fundamentals missing"
                    }}
                  </span>
                  <span class="company-name">
                    {{
                      stock.data_quality?.sentiment_articles ?? 0
                    }} sentiment articles
                  </span>
                  <details class="component-details">
                    <summary>Score breakdown</summary>
                    <dl>
                      <template
                        v-for="(value, key) in stock.components"
                        :key="key"
                      >
                        <dt>{{ labelFor(key) }}</dt>
                        <dd>{{ value == null ? "Unavailable" : number(value) }}</dd>
                      </template>
                    </dl>
                    <ul>
                      <li
                        v-for="(explanation, index) in stock.explanations"
                        :key="index"
                      >
                        {{ explanation }}
                      </li>
                    </ul>
                  </details>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="panel">
        <div class="section-heading">
          <div>
            <h2>Illustrative allocation</h2>
            <p>
              Ranking-first allocation using whole shares. This is not an
              executable order.
            </p>
          </div>
          <span class="pill">
            {{ data.allocation?.fractional_shares_used
              ? "Fractional shares"
              : "Whole shares only" }}
          </span>
        </div>

        <div class="allocation-summary">
          <div>
            <span>Budget</span>
            <strong>{{ money(data.allocation?.budget) }}</strong>
          </div>
          <div>
            <span>Invested</span>
            <strong>{{ money(data.allocation?.invested) }}</strong>
          </div>
          <div>
            <span>Remaining</span>
            <strong>{{ money(data.allocation?.remaining_cash) }}</strong>
          </div>
        </div>

        <div v-if="!data.allocation?.allocations?.length" class="empty-state">
          No shares could be allocated within this budget and currency.
        </div>

        <div v-else class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Rank</th>
                <th>Stock</th>
                <th>Shares</th>
                <th>Price per share</th>
                <th>Estimated cost</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in data.allocation.allocations"
                :key="item.symbol"
              >
                <td>#{{ item.rank }}</td>
                <td>
                  <strong>{{ item.symbol }}</strong>
                  <span class="company-name">{{ item.company_name }}</span>
                </td>
                <td>{{ item.shares }}</td>
                <td>{{ money(item.latest_price, item.currency) }}</td>
                <td>{{ money(item.estimated_cost, item.currency) }}</td>
                <td>{{ number(item.score) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div
          v-if="data.allocation?.excluded?.length"
          class="excluded-section"
        >
          <h3>Excluded from allocation</h3>
          <ul>
            <li
              v-for="(item, index) in data.allocation.excluded"
              :key="index"
            >
              {{ typeof item === "string" ? item : JSON.stringify(item) }}
            </li>
          </ul>
        </div>

        <p v-if="data.allocation?.disclaimer" class="disclaimer">
          {{ data.allocation.disclaimer }}
        </p>
      </section>

      <section class="panel">
        <div class="section-heading">
          <div>
            <h2>Methodology and limitations</h2>
            <p>Scoring weights vary with risk preference and time horizon. They are provisional research heuristics, not a validated prediction of future performance.</p>
          </div>
        </div>

        <div class="weights-grid">
          <div
            v-for="(weight, key) in data.scoring_weights"
            :key="key"
            class="weight-item"
          >
            <span>{{ labelFor(key) }}</span>
            <strong>{{ percentage(weight) }}</strong>
          </div>
        </div>

        <p class="forecast-note">
          Forecast included in scoring:
          <strong>{{ data.forecast_included ? "Yes" : "No" }}</strong>
        </p>

        <ul class="limitations-list">
          <li v-for="(item, index) in data.limitations" :key="index">
            {{ item }}
          </li>
        </ul>

        <p class="disclaimer">{{ data.disclaimer }}</p>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from "vue";
import { getStockRecommendations } from "../services/api";

const form = reactive({
  budget: "1000.00",
  currency: "USD",
  risk_tolerance: "moderate",
  horizon_months: 12,
  market: "NASDAQ",
  max_candidates: 10,
});

const data = ref(null);
const loading = ref(false);
const error = ref("");

const selectedCurrency = computed(() => form.currency);

function money(value, currency = selectedCurrency.value) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  const amount = Number(value);
  if (!Number.isFinite(amount)) return "—";

  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(amount);
  } catch {
    return `${currency} ${amount.toFixed(2)}`;
  }
}

function number(value) {
  if (value === null || value === undefined || value === "") return "—";

  const amount = Number(value);
  return Number.isFinite(amount) ? amount.toFixed(2) : "—";
}

function percentage(value) {
  const amount = Number(value);
  return Number.isFinite(amount) ? `${(amount * 100).toFixed(0)}%` : "—";
}

function clampScore(value) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return 0;
  return Math.max(0, Math.min(100, amount));
}

function labelFor(key) {
  return String(key)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

async function loadRecommendations() {
  error.value = "";

  const budget = Number(form.budget);

  if (!Number.isFinite(budget) || budget <= 0) {
    error.value = "Enter a budget greater than zero.";
    return;
  }

  loading.value = true;

  try {
    data.value = await getStockRecommendations({
      budget: form.budget,
      currency: form.currency,
      risk_tolerance: form.risk_tolerance,
      horizon_months: form.horizon_months,
      market: form.market,
      max_candidates: form.max_candidates,
    });
  } catch (err) {
    console.error("Failed to load stock recommendations:", err);
    error.value =
      err?.response?.data?.detail ||
      err?.response?.data?.error ||
      "The recommendations request failed. Please try again.";
  } finally {
    loading.value = false;
  }
}

loadRecommendations();
</script>

<style scoped>

.research-guide{margin:0 0 24px;padding:28px;background:linear-gradient(135deg,#132d3e,#1c4350 65%,#215b5a);color:#f8fafc;border-radius:20px;box-shadow:0 18px 40px rgba(10,35,49,.15)}
.research-guide-heading{max-width:780px}
.guide-label{display:inline-block;font-size:11px;font-weight:750;letter-spacing:.13em;color:#a7f3d0;margin-bottom:12px}
.research-guide h2{font-size:clamp(22px,2.5vw,30px);line-height:1.2;margin:0 0 10px;color:#fff}
.research-guide-heading p{color:#d3e4e6;line-height:1.65;margin:0}
.guide-steps{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:24px}
.guide-steps>div{border:1px solid rgba(255,255,255,.17);background:rgba(255,255,255,.07);border-radius:14px;padding:18px}
.guide-number{display:block;font-size:12px;font-weight:700;letter-spacing:.08em;color:#8ff0cb;margin-bottom:10px}
.guide-steps strong{display:block;font-size:14px;color:#fff;margin-bottom:7px}
.guide-steps p{color:#d1e4e7;font-size:13px;line-height:1.55;margin:0}
.guide-caution{font-size:12px;line-height:1.5;color:#c0d4db;margin:18px 0 0}
@media(max-width:860px){.guide-steps{grid-template-columns:1fr}.research-guide{padding:20px}}

.recommendations-page {
  max-width: 1440px;
  margin: 0 auto;
  color: #172033;
}

.page-header,
.section-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  margin: 4px 0 10px;
  font-size: clamp(26px, 3vw, 34px);
  letter-spacing: -0.8px;
}

.eyebrow {
  margin: 0;
  color: #2563eb;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 1.3px;
}

.subtitle,
.section-heading p {
  margin: 0;
  color: #64748b;
  line-height: 1.6;
}

.panel,
.stat-card {
  margin-bottom: 22px;
  padding: 24px;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 3px 12px rgb(15 23 42 / 3%);
}

.section-heading {
  margin-bottom: 22px;
}

.section-heading h2 {
  margin: 0 0 7px;
  font-size: 20px;
}

.parameters-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 20px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field label {
  color: #475569;
  font-size: 13px;
  font-weight: 700;
}

.field input,
.field select {
  width: 100%;
  min-height: 44px;
  padding: 10px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #fff;
  color: #172033;
  font: inherit;
  box-sizing: border-box;
}

.field input:focus,
.field select:focus {
  outline: 2px solid #93c5fd;
  border-color: #2563eb;
}

.form-actions {
  display: flex;
  align-items: flex-end;
}

.primary-button,
.secondary-button {
  min-height: 42px;
  padding: 10px 16px;
  border: 0;
  border-radius: 8px;
  cursor: pointer;
  font: inherit;
  font-weight: 700;
}

.primary-button {
  background: #2563eb;
  color: #fff;
}

.secondary-button {
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #334155;
}

.primary-button:hover:not(:disabled) {
  background: #1d4ed8;
}

.secondary-button:hover:not(:disabled) {
  background: #f8fafc;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 22px;
}

.stat-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin: 0;
}

.stat-card span,
.allocation-summary span {
  color: #64748b;
  font-size: 13px;
}

.stat-card strong {
  font-size: 26px;
  overflow-wrap: anywhere;
}

.stat-card small {
  color: #64748b;
}

.pill {
  display: inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 700;
  text-transform: capitalize;
  white-space: nowrap;
}

.table-wrapper {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

th,
td {
  padding: 14px 12px;
  border-bottom: 1px solid #e2e8f0;
  vertical-align: top;
}

th {
  background: #f8fafc;
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.35px;
  white-space: nowrap;
}

td {
  font-size: 13px;
}

.company-name,
.exchange-name {
  display: block;
  margin-top: 5px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.45;
}

.rank-number {
  display: inline-block;
  padding: 5px 8px;
  border-radius: 6px;
  background: #f1f5f9;
  font-weight: 800;
}

.score-track {
  width: 85px;
  height: 5px;
  margin-top: 8px;
  overflow: hidden;
  border-radius: 99px;
  background: #e2e8f0;
}

.score-fill {
  height: 100%;
  border-radius: inherit;
  background: #2563eb;
}

.data-status {
  display: inline-block;
  font-size: 12px;
  font-weight: 700;
}

.data-status.available {
  color: #047857;
}

.data-status.missing {
  color: #b45309;
}

.component-details {
  min-width: 150px;
  margin-top: 9px;
  color: #475569;
  font-size: 12px;
}

.component-details summary {
  cursor: pointer;
  font-weight: 700;
}

.component-details dl {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 5px 10px;
}

.component-details dt,
.component-details dd {
  margin: 0;
}

.component-details ul {
  padding-left: 17px;
  line-height: 1.5;
}

.allocation-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 20px;
}

.allocation-summary > div {
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 9px;
}

.allocation-summary strong {
  font-size: 20px;
  overflow-wrap: anywhere;
}

.excluded-section {
  margin-top: 20px;
  color: #475569;
  font-size: 13px;
}

.disclaimer {
  margin: 18px 0 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.7;
}

.weights-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.weight-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 9px;
}

.weight-item span {
  color: #64748b;
  font-size: 12px;
}

.weight-item strong {
  font-size: 19px;
}

.forecast-note {
  margin: 20px 0;
  color: #475569;
  font-size: 13px;
}

.limitations-list {
  padding-left: 20px;
  color: #475569;
  font-size: 13px;
  line-height: 1.8;
}

.notice,
.empty-state {
  padding: 18px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  color: #475569;
  background: #fff;
  line-height: 1.6;
}

.error-notice {
  margin-bottom: 20px;
  border-color: #fecaca;
  background: #fff7f7;
  color: #991b1b;
}

.error-notice p {
  margin-bottom: 0;
}

@media (max-width: 1000px) {
  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .parameters-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .weights-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 600px) {
  .page-header,
  .section-heading {
    flex-direction: column;
  }

  .panel {
    padding: 16px;
  }

  .stats-grid,
  .parameters-grid,
  .allocation-summary {
    grid-template-columns: 1fr;
  }

  .weights-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
