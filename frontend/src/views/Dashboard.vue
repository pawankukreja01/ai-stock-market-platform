
<template>
  <div class="dashboard">
    <div class="page-header">
      <div>
        <h1>Stock Market Dashboard</h1>
        <p>
          AI-powered market analysis, forecasting, and risk assessment.
        </p>
      </div>

      <div class="market-status">
        <span class="status-dot"></span>
        API Connected
      </div>
    </div>

    <!-- Existing dashboard statistics -->
    <div class="stats-grid">
      <div class="stat-card">
        <span class="stat-label">Tracked Stocks</span>
        <strong class="stat-value">{{ stocks.length }}</strong>
      </div>

      <div class="stat-card">
        <span class="stat-label">Market</span>
        <strong class="stat-value">US Equities</strong>
      </div>

      <div class="stat-card">
        <span class="stat-label">Data Source</span>
        <strong class="stat-value">Django API</strong>
      </div>
    </div>

    <!-- Existing tracked stocks section -->
    <section class="stocks-section">
      <div class="section-header">
        <div>
          <h2>Tracked Stocks</h2>
          <p>Stocks currently stored in the platform.</p>
        </div>
      </div>

      <div v-if="loadingStocks" class="message">
        Loading stocks...
      </div>

      <div v-else-if="stocksError" class="message error">
        {{ stocksError }}
      </div>

      <div v-else-if="stocks.length === 0" class="message">
        No stocks found.
      </div>

      <div v-else class="stock-list">
        <div
          v-for="stock in stocks"
          :key="stock.id"
          class="stock-row"
        >
          <div>
            <strong>{{ stock.symbol }}</strong>
            <span>{{ stock.company_name }}</span>
          </div>

          <div class="stock-meta">
            <span>{{ stock.exchange || "—" }}</span>
            <span>{{ stock.sector || "Sector unavailable" }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Existing stock price chart -->
    <StockPriceChart
      v-if="stocks.length > 0"
      :stock-id="stocks[0].id"
      :symbol="stocks[0].symbol"
    />

    <ExplainabilityPanel    
      v-if="stocks.length > 0"
      :symbol="selectedSymbol || stocks[0].symbol"
    />

    <!-- News sentiment dashboard -->
    <section class="sentiment-section">
      <div class="section-header sentiment-header">
        <div>
          <h2>News Sentiment Analysis</h2>
          <p>
            Financial news analyzed using FinBERT.
            This measures news sentiment, not future stock returns.
          </p>
        </div>

        <div class="sentiment-controls">
          <label for="sentiment-symbol">Stock symbol</label>
          <select
            id="sentiment-symbol"
            v-model="selectedSymbol"
            :disabled="loadingStocks || stocks.length === 0"
            @change="loadSentiment"
          >
            <option
              v-for="stock in stocks"
              :key="stock.id"
              :value="stock.symbol"
            >
              {{ stock.symbol }}
            </option>
          </select>

          <button
            type="button"
            class="refresh-button"
            :disabled="sentimentLoading || !selectedSymbol"
            @click="loadSentiment"
          >
            {{ sentimentLoading ? "Loading..." : "Refresh" }}
          </button>
        </div>
      </div>

      <div v-if="sentimentLoading" class="message">
        Loading sentiment summary for {{ selectedSymbol }}...
      </div>

      <div v-else-if="sentimentError" class="message error">
        <p>{{ sentimentError }}</p>
        <button
          type="button"
          class="refresh-button"
          @click="loadSentiment"
        >
          Try again
        </button>
      </div>

      <div
        v-else-if="sentiment && sentiment.articles_analyzed > 0"
        class="sentiment-content"
      >
        <div class="sentiment-metrics">
          <div class="sentiment-metric">
            <span class="stat-label">Articles analyzed</span>
            <strong class="stat-value">
              {{ sentiment.articles_analyzed }}
            </strong>
            <span class="metric-detail">
              {{ sentiment.articles_with_scores }} with scores
            </span>
          </div>

          <div class="sentiment-metric">
            <span class="stat-label">Average sentiment score</span>
            <strong
              class="stat-value"
              :class="averageScoreClass"
            >
              {{ formatScore(sentiment.average_sentiment_score) }}
            </strong>
            <span class="metric-detail">
              {{ averageScoreDescription }}
            </span>
          </div>

          <div class="sentiment-metric">
            <span class="stat-label">Most common sentiment</span>
            <strong
              class="stat-value"
              :class="dominantSentimentClass"
            >
              {{ dominantSentiment }}
            </strong>
            <span class="metric-detail">
              Based on article classifications
            </span>
          </div>
        </div>

        <div class="sentiment-chart-card">
          <div class="chart-heading">
            <div>
              <h3>{{ sentiment.symbol }} sentiment distribution</h3>
              <p>
                {{ sentiment.articles_analyzed }}
                analyzed news articles
              </p>
            </div>

            <span class="model-label">FinBERT</span>
          </div>

          <div ref="sentimentChart" class="sentiment-chart"></div>

          <div class="distribution-list">
            <div
              v-for="item in distributionItems"
              :key="item.label"
              class="distribution-row"
            >
              <div class="distribution-label">
                <span
                  class="distribution-dot"
                  :class="item.className"
                ></span>
                <span>{{ item.label }}</span>
              </div>

              <div class="distribution-bar-track">
                <div
                  class="distribution-bar"
                  :class="item.className"
                  :style="{ width: `${item.percentage}%` }"
                ></div>
              </div>

              <div class="distribution-value">
                {{ item.count }}
                <span>({{ item.percentage.toFixed(1) }}%)</span>
              </div>
            </div>
          </div>

          <p class="analysis-timestamp">
            Last analysis:
            {{ formatDate(sentiment.latest_analysis_at) }}
          </p>
        </div>
      </div>

      <div v-else-if="sentiment" class="message">
        No analyzed news articles are available for
        {{ selectedSymbol }}. Ingest news and run sentiment analysis first.
      </div>

      <div v-else-if="!loadingStocks && stocks.length === 0" class="message">
        Add a tracked stock to view its news sentiment.
      </div>
    </section>
  </div>
</template>

<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
} from "vue";
import Plotly from "plotly.js-finance-dist-min";

import {
  getStocks,
  getStockSentiment,
} from "../services/api";

import StockPriceChart from "../components/charts/StockPriceChart.vue";

import ExplainabilityPanel from "../components/ExplainabilityPanel.vue";

const stocks = ref([]);
const loadingStocks = ref(true);
const stocksError = ref("");

const selectedSymbol = ref("");
const sentiment = ref(null);
const sentimentLoading = ref(false);
const sentimentError = ref("");
const sentimentChart = ref(null);

let requestNumber = 0;

const distributionItems = computed(() => {
  const distribution = sentiment.value?.sentiment_distribution || {};

  return [
    {
      label: "Positive",
      count: distribution.positive?.count ?? 0,
      percentage: distribution.positive?.percentage ?? 0,
      className: "positive",
    },
    {
      label: "Neutral",
      count: distribution.neutral?.count ?? 0,
      percentage: distribution.neutral?.percentage ?? 0,
      className: "neutral",
    },
    {
      label: "Negative",
      count: distribution.negative?.count ?? 0,
      percentage: distribution.negative?.percentage ?? 0,
      className: "negative",
    },
  ];
});

const dominantSentiment = computed(() => {
  const distribution = sentiment.value?.sentiment_distribution;

  if (!distribution || !sentiment.value?.articles_analyzed) {
    return "—";
  }

  const labels = [
    { key: "positive", name: "Positive" },
    { key: "neutral", name: "Neutral" },
    { key: "negative", name: "Negative" },
  ];

  return labels.reduce((best, item) => {
    const currentCount = distribution[item.key]?.count ?? 0;
    const bestCount = distribution[best.key]?.count ?? 0;

    return currentCount > bestCount ? item : best;
  }).name;
});

const dominantSentimentClass = computed(() => {
  const value = dominantSentiment.value.toLowerCase();

  if (value === "positive") return "positive-text";
  if (value === "negative") return "negative-text";

  return "neutral-text";
});

const averageScoreClass = computed(() => {
  const score = sentiment.value?.average_sentiment_score;

  if (score == null) return "neutral-text";
  if (score > 0.05) return "positive-text";
  if (score < -0.05) return "negative-text";

  return "neutral-text";
});

const averageScoreDescription = computed(() => {
  const score = sentiment.value?.average_sentiment_score;

  if (score == null) return "No scores available";
  if (score > 0.05) return "Positive text signal";
  if (score < -0.05) return "Negative text signal";

  return "Near neutral";
});

function formatScore(value) {
  if (value == null || !Number.isFinite(Number(value))) {
    return "—";
  }

  const number = Number(value);
  return `${number > 0 ? "+" : ""}${number.toFixed(4)}`;
}

function formatDate(value) {
  if (!value) return "Not available";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Not available";
  }

  return date.toLocaleString();
}

async function renderSentimentChart() {
  if (!sentimentChart.value || !sentiment.value) return;

  const items = distributionItems.value;

  const trace = {
    type: "bar",
    x: items.map((item) => item.label),
    y: items.map((item) => item.count),
    marker: {
      color: ["#16a34a", "#9ca3af", "#dc2626"],
    },
    text: items.map(
      (item) => `${item.count} (${item.percentage.toFixed(1)}%)`
    ),
    textposition: "outside",
    cliponaxis: false,
    hovertemplate: "%{x}<br>Articles: %{y}<extra></extra>",
  };

  const layout = {
    autosize: true,
    height: 300,
    margin: {
      l: 45,
      r: 15,
      t: 30,
      b: 45,
    },
    paper_bgcolor: "#ffffff",
    plot_bgcolor: "#ffffff",
    font: {
      family: "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
      color: "#374151",
      size: 12,
    },
    showlegend: false,
    xaxis: {
      fixedrange: true,
      showgrid: false,
    },
    yaxis: {
      title: "Articles",
      rangemode: "tozero",
      fixedrange: true,
      gridcolor: "#e5e7eb",
      zeroline: false,
    },
  };

  await Plotly.react(
    sentimentChart.value,
    [trace],
    layout,
    {
      responsive: true,
      displayModeBar: false,
    }
  );
}

async function loadSentiment() {
  const symbol = selectedSymbol.value;
  const currentRequest = ++requestNumber;

  sentimentError.value = "";
  sentiment.value = null;

  if (!symbol) {
    sentimentLoading.value = false;
    return;
  }

  sentimentLoading.value = true;

  try {
    const result = await getStockSentiment(symbol, 50);

    // Ignore an older response if the selection changed meanwhile.
    if (currentRequest !== requestNumber) return;

    sentiment.value = result;

    await nextTick();

    if (
      currentRequest === requestNumber &&
      result.articles_analyzed > 0
    ) {
      await renderSentimentChart();
    }
  } catch (error) {
    if (currentRequest !== requestNumber) return;

    console.error("Failed to load news sentiment:", error);

    sentimentError.value =
      error.response?.data?.error ||
      "Unable to load the sentiment summary. Check that Django is running and the API is available.";
  } finally {
    if (currentRequest === requestNumber) {
      sentimentLoading.value = false;
    }
  }
}

async function loadStocks() {
  loadingStocks.value = true;
  stocksError.value = "";

  try {
    const result = await getStocks();

    stocks.value = Array.isArray(result)
      ? result
      : result.results || [];

    // Prefer AAPL for the initial view when it exists.
    selectedSymbol.value =
      stocks.value.find(
        (stock) => stock.symbol?.toUpperCase() === "AAPL"
      )?.symbol ||
      stocks.value[0]?.symbol ||
      "";

    if (selectedSymbol.value) {
      await loadSentiment();
    }
  } catch (error) {
    console.error("Failed to load stocks:", error);

    stocksError.value =
      "Unable to load stocks. Make sure the Django API is running.";
  } finally {
    loadingStocks.value = false;
  }
}

function handleChartResize() {
  if (sentimentChart.value) {
    Plotly.Plots.resize(sentimentChart.value);
  }
}

onMounted(() => {
  loadStocks();
  window.addEventListener("resize", handleChartResize);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleChartResize);

  if (sentimentChart.value) {
    Plotly.purge(sentimentChart.value);
  }
});
</script>

<style scoped>
.dashboard {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 30px;
}

.page-header h1 {
  margin: 0;
  font-size: 30px;
}

.page-header p {
  margin: 8px 0 0;
  color: #6b7280;
  line-height: 1.6;
}

.market-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #ecfdf5;
  color: #047857;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card,
.sentiment-metric {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 22px;
  min-width: 0;
}

.stat-label {
  display: block;
  color: #6b7280;
  font-size: 14px;
  margin-bottom: 10px;
}

.stat-value {
  display: block;
  font-size: 26px;
  color: #111827;
  overflow-wrap: anywhere;
}

.stocks-section,
.sentiment-section,
.sentiment-chart-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  overflow: hidden;
}

.stocks-section {
  margin-bottom: 30px;
}

.section-header {
  padding: 22px;
  border-bottom: 1px solid #e5e7eb;
}

.section-header h2 {
  margin: 0;
  font-size: 20px;
}

.section-header p {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 14px;
  line-height: 1.6;
}

.stock-list {
  display: flex;
  flex-direction: column;
}

.stock-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  padding: 18px 22px;
  border-bottom: 1px solid #f3f4f6;
}

.stock-row:last-child {
  border-bottom: none;
}

.stock-row strong {
  display: block;
  font-size: 17px;
}

.stock-row span {
  display: block;
  margin-top: 4px;
  color: #6b7280;
  font-size: 13px;
}

.stock-meta {
  display: flex;
  gap: 25px;
  text-align: right;
}

.stock-meta span {
  margin: 0;
}

.message {
  padding: 30px;
  text-align: center;
  color: #6b7280;
  line-height: 1.6;
}

.message.error {
  color: #b91c1c;
  background: #fef2f2;
}

.sentiment-section {
  margin-top: 30px;
}

.sentiment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
}

.sentiment-controls {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.sentiment-controls label {
  color: #6b7280;
  font-size: 13px;
}

.sentiment-controls select {
  min-width: 110px;
  padding: 10px 12px;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  color: #111827;
  font-size: 14px;
}

.refresh-button {
  padding: 10px 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: white;
  color: #374151;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.refresh-button:hover:not(:disabled) {
  background: #f9fafb;
}

.refresh-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.sentiment-content {
  padding: 22px;
  background: #f9fafb;
}

.sentiment-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 22px;
}

.sentiment-metric {
  padding: 20px;
}

.metric-detail {
  display: block;
  color: #6b7280;
  font-size: 12px;
  margin-top: 8px;
  line-height: 1.5;
}

.positive-text {
  color: #15803d;
}

.neutral-text {
  color: #4b5563;
}

.negative-text {
  color: #b91c1c;
}

.sentiment-chart-card {
  padding: 22px;
}

.chart-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.chart-heading h3 {
  margin: 0;
  font-size: 18px;
}

.chart-heading p {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 13px;
}

.model-label {
  padding: 6px 9px;
  background: #eff6ff;
  color: #1d4ed8;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.sentiment-chart {
  width: 100%;
  min-height: 300px;
}

.distribution-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-top: 12px;
}

.distribution-row {
  display: grid;
  grid-template-columns: 100px minmax(50px, 1fr) 115px;
  align-items: center;
  gap: 14px;
}

.distribution-label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #374151;
  font-size: 13px;
}

.distribution-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex: 0 0 auto;
}

.distribution-dot.positive,
.distribution-bar.positive {
  background: #16a34a;
}

.distribution-dot.neutral,
.distribution-bar.neutral {
  background: #9ca3af;
}

.distribution-dot.negative,
.distribution-bar.negative {
  background: #dc2626;
}

.distribution-bar-track {
  height: 9px;
  border-radius: 999px;
  background: #e5e7eb;
  overflow: hidden;
}

.distribution-bar {
  height: 100%;
  border-radius: 999px;
  min-width: 0;
  transition: width 250ms ease;
}

.distribution-value {
  text-align: right;
  color: #111827;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}

.distribution-value span {
  color: #6b7280;
  font-weight: 400;
}

.analysis-timestamp {
  margin: 22px 0 0;
  padding-top: 16px;
  border-top: 1px solid #e5e7eb;
  color: #6b7280;
  font-size: 12px;
}

@media (max-width: 900px) {
  .sentiment-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .sentiment-metrics {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 800px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
  }

  .stock-row {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }

  .stock-meta {
    text-align: left;
    flex-wrap: wrap;
    gap: 15px;
  }
}

@media (max-width: 520px) {
  .distribution-row {
    grid-template-columns: 82px minmax(35px, 1fr) 95px;
    gap: 8px;
  }

  .distribution-value {
    font-size: 12px;
  }

  .sentiment-content,
  .sentiment-chart-card {
    padding: 14px;
  }

  .sentiment-controls {
    width: 100%;
  }
}
</style>
