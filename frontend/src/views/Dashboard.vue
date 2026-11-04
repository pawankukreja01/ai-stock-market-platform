<template>

  <div class="dashboard">

    <div class="page-header">

      <div>

        <h1>Market overview</h1>

        <p>Track your markets, review the latest available quotes and explore quantitative research.</p>

      </div>



      <div
        class="market-status"
        :class="{
          'market-status-loading': loadingStocks,
          'market-status-error': Boolean(stocksError),
        }"
        role="status"
        aria-live="polite"
      >
        <span class="status-dot"></span>
        {{ loadingStocks ? "Connecting to API" : stocksError ? "API unavailable" : "API connected" }}
      </div>

    </div>



    <div class="stats-grid">

      <div class="stat-card">

        <span class="stat-label">Available stocks</span>

        <strong class="stat-value">{{ stocks.length }}</strong>

      </div>



      <div class="stat-card">

        <span class="stat-label">Preferred market</span>

        <strong class="stat-value">{{ marketLabel }}</strong>

      </div>



      <div class="stat-card">

        <span class="stat-label">API source</span>

        <strong class="stat-value">Django API</strong>

      </div>

    </div>



    <section v-if="marketCoverage" class="preview-coverage" aria-label="Stored market data availability">
      <strong>{{ marketCoverage.historical_price_count ? "Historical market data available" : "Market data not loaded" }}</strong>
      <p v-if="!marketCoverage.historical_price_count">
        Your stock catalogue is available, but this isolated preview has no historical OHLC prices yet.
        Price charts, risk analysis, predictions, backtests and recommendations need stored observations.
        Import a reviewed offline market snapshot into the preview database. No live market data is implied.
      </p>
      <p v-else>
        {{ marketCoverage.historical_price_count.toLocaleString() }} stored price rows;
        latest observation {{ marketCoverage.last_historical_date || "unknown" }}.
        {{ marketCoverage.fundamental_record_count.toLocaleString() }} fundamental records;
        {{ marketCoverage.news_article_count.toLocaleString() }} news articles.
        Historical observations are not live market quotes.
      </p>
    </section>

    <!-- Market benchmarks powered by the existing Django API. -->
    <section class="market-overview-section" aria-labelledby="market-overview-title">
      <div class="market-overview-heading">
        <div>
          <p class="market-overview-eyebrow">MARKET SNAPSHOT</p>
          <h2 id="market-overview-title">Market performance</h2>
          <p class="market-overview-subtitle">
            Latest available benchmark closes and recent price performance.
          </p>
        </div>

        <div class="market-overview-actions">
          <span v-if="marketOverviewAsOf" class="market-overview-asof">
            Data through {{ formatMarketDate(marketOverviewAsOf) }}
          </span>
          <button
            type="button"
            class="market-overview-refresh"
            :disabled="marketOverviewLoading"
            @click="loadMarketOverview"
          >
            {{ marketOverviewLoading ? "Refreshing…" : "Refresh markets" }}
          </button>
        </div>
      </div>

      <div v-if="marketOverviewLoading && marketOverviewCards.length === 0" class="market-overview-state">
        Loading benchmark data…
      </div>

      <div v-else-if="marketOverviewError" class="market-overview-state market-overview-state-error" role="status">
        <span>{{ marketOverviewError }}</span>
        <button type="button" class="market-overview-retry" @click="loadMarketOverview">
          Try again
        </button>
      </div>

      <div v-else class="market-index-grid">
        <article
          v-for="item in marketOverviewCards"
          :key="item.key"
          class="market-index-card"
          :class="[
            item.available ? item.trendClass : 'market-index-unavailable',
          ]"
        >
          <div class="market-index-card-heading">
            <div class="market-index-symbol" aria-hidden="true">{{ item.shortLabel }}</div>
            <div class="market-index-name-wrap">
              <h3>{{ item.label }}</h3>
              <p>{{ item.description }}</p>
            </div>
            <span v-if="item.available" class="market-index-period">30D</span>
            <span v-else class="market-index-period">N/A</span>
          </div>

          <template v-if="item.available">
            <div class="market-index-values">
              <strong class="market-index-level">{{ formatMarketLevel(item.level) }}</strong>
              <span class="market-index-unit">Latest level</span>
            </div>

            <div class="market-index-performance">
              <span class="market-index-daily" :class="item.dayTrendClass">
                {{ formatMarketPercent(item.dayChangePct) }}
                <small>latest session</small>
              </span>
              <span class="market-index-monthly" :class="item.trendClass">
                {{ formatMarketPercent(item.monthChangePct) }}
                <small>period change</small>
              </span>
            </div>

            <div class="market-index-sparkline" aria-hidden="true">
              <svg viewBox="0 0 100 42" preserveAspectRatio="none">
                <polyline
                  :points="item.sparklinePoints"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2.4"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
            </div>

            <p class="market-index-date">Latest observation: {{ formatMarketDate(item.latestDate) }}</p>
          </template>

          <div v-else class="market-index-unavailable-note">
            No observations returned for this benchmark.
          </div>
        </article>
      </div>

      <p class="market-overview-footnote">
        Changes are calculated from the returned daily benchmark levels. They are historical observations,
        not live quotes or investment recommendations.
      </p>
    </section>

    <!-- ============================================================
         LATEST STOCK QUOTE
    ============================================================= -->
    <section class="quote-section">
      <div class="section-header quote-section-header">
        <div>
          <h2>Latest Available Stock Quote</h2>
          <p>Latest price and market data retrieved from the configured provider.</p>
        </div>

        <div class="quote-controls">
          <div class="quote-select-control">
            <label for="quote-stock-select">Select stock</label>
            <select
              id="quote-stock-select"
              v-model="quoteSymbol"
              :disabled="loadingStocks || stocks.length === 0"
              @change="loadLatestQuote"
            >
              <option
                v-for="stock in stocks"
                :key="stock.id"
                :value="stock.symbol"
              >
                {{ stock.symbol }} — {{ stock.company_name }}
              </option>
            </select>
          </div>

          <button
            type="button"
            class="quote-refresh-button"
            :disabled="latestQuoteLoading || !quoteSymbol"
            @click="loadLatestQuote"
          >
            {{ latestQuoteLoading ? "Refreshing..." : "Refresh quote" }}
          </button>
        </div>
      </div>

      <div v-if="latestQuoteLoading" class="quote-message">
        Loading latest available quote...
      </div>

      <div v-else-if="latestQuoteError" class="quote-message quote-error">
        <p>{{ latestQuoteError }}</p>
        <button
          type="button"
          class="quote-refresh-button"
          :disabled="!quoteSymbol"
          @click="loadLatestQuote"
        >
          Try again
        </button>
      </div>

      <div v-else-if="latestQuote" class="quote-content">
        <div class="quote-primary-grid">
          <div class="quote-primary-item">
            <span class="quote-label">Latest available price</span>
            <strong class="quote-price">
              {{ formatQuotePrice(latestQuote.price) }}
            </strong>
            <span class="quote-symbol">
              {{ latestQuote.symbol }} · {{ latestQuote.company_name }}
            </span>
          </div>

          <div class="quote-primary-item">
            <span class="quote-label">Daily change</span>
            <strong class="quote-change" :class="quoteChangeClass">
              {{ formatQuoteChange(latestQuote.change) }}
            </strong>
            <span class="quote-change-percent" :class="quoteChangeClass">
              {{ formatQuotePercent(latestQuote.change_percent) }}
            </span>
          </div>
        </div>

        <div class="quote-metrics-grid">
          <div class="quote-metric">
            <span>Previous close</span>
            <strong>{{ formatQuotePrice(latestQuote.previous_close) }}</strong>
          </div>

          <div class="quote-metric">
            <span>{{ quoteVolumeLabel }}</span>
            <strong>{{ formatQuoteVolume(latestQuote.volume) }}</strong>
          </div>

          <div class="quote-metric">
            <span>Quote type</span>
            <strong>
              {{ latestQuote.quote_type === "intraday_1m"
                ? "Intraday 1-minute bar"
                : latestQuote.quote_type === "daily_close"
                  ? "Daily close"
                  : "Unavailable" }}
            </strong>
          </div>

          <div class="quote-metric">
            <span>Data freshness</span>
            <strong
              class="quote-freshness"
              :class="`freshness-${latestQuote.freshness_status}`"
            >
              {{ quoteFreshnessLabel }}
            </strong>
          </div>

          <div class="quote-metric">
            <span>Source timestamp</span>
            <strong>{{ formatQuoteTimestamp(latestQuote.source_timestamp) }}</strong>
          </div>

          <div class="quote-metric">
            <span>Retrieved at</span>
            <strong>{{ formatQuoteTimestamp(latestQuote.retrieved_at) }}</strong>
          </div>

          <div class="quote-metric">
            <span>Provider</span>
            <strong>{{ latestQuote.provider || "Unavailable" }}</strong>
          </div>
        </div>

        <p class="quote-data-note">
          {{ latestQuote.data_note }}
        </p>
      </div>

      <div v-else class="quote-message">
        Select a stock to view its latest available quote.
      </div>
    </section>



    <!-- Saved investment preferences -->

    <section class="personalisation-card">

      <div class="personalisation-heading">

        <div>

          <p class="personalisation-eyebrow">YOUR INVESTMENT PROFILE</p>

          <h2>Personalisation</h2>

          <p>Dashboard context based on your saved profile preferences.</p>

        </div>



        <span class="personalisation-status">

          {{ preferencesLoading ? "Loading profile…" : "Profile preferences" }}

        </span>

      </div>



      <div v-if="preferencesError" class="personalisation-message error">

        {{ preferencesError }}

      </div>



      <div v-else-if="preferencesLoading" class="personalisation-message">

        Loading your saved investment preferences…

      </div>



      <div v-else class="preference-grid">

        <div class="preference-item">

          <span>Preferred market</span>

          <strong>{{ marketLabel }}</strong>

        </div>



        <div class="preference-item">

          <span>Risk tolerance</span>

          <strong>{{ riskLabel }}</strong>

        </div>



        <div class="preference-item">

          <span>Investment horizon</span>

          <strong>{{ horizonLabel }}</strong>

        </div>



        <div class="preference-item">

          <span>Preferred sectors</span>

          <strong>{{ sectorsLabel }}</strong>

        </div>

      </div>



      <p class="personalisation-note">

        These preferences provide context for your research. They do not

        guarantee performance or constitute a personalised financial

        recommendation.

      </p>

    </section>



    <!-- Tracked stocks -->

    <section class="stocks-section">

      <div class="section-header">

        <div>

          <h2>Tracked Stocks</h2>

          <p>Search and browse the stocks available in your platform.</p>

        </div>



        <span class="section-count">

          {{ filteredStocks.length }} stocks

        </span>

      </div>



      <div

        v-if="!loadingStocks && !stocksError && stocks.length > 0"

        class="stock-list-toolbar"

      >

        <div class="stock-search-control">

          <label for="tracked-stock-search">Search stocks</label>

          <input

            id="tracked-stock-search"

            v-model.trim="stockSearch"

            type="search"

            placeholder="Search symbol or company"

            autocomplete="off"

          />

        </div>



        <div class="stock-market-control">

          <label for="tracked-stock-exchange">Exchange</label>

          <select id="tracked-stock-exchange" v-model="selectedExchange">

            <option value="">All exchanges</option>

            <option

              v-for="exchange in availableExchanges"

              :key="exchange"

              :value="exchange"

            >

              {{ exchange }}

            </option>

          </select>

        </div>



        <button

          v-if="stockSearch || selectedExchange"

          type="button"

          class="clear-filters-button"

          @click="clearStockFilters"

        >

          Clear filters

        </button>

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



      <div v-else class="stock-results">

        <div v-if="filteredStocks.length === 0" class="message no-results">

          <p>No stocks match your search or exchange filter.</p>

          <button

            type="button"

            class="clear-filters-button"

            @click="clearStockFilters"

          >

            Clear filters

          </button>

        </div>



        <template v-else>

          <div class="stock-list">

            <div

              v-for="stock in paginatedStocks"

              :key="stock.id"

              class="stock-row"

            >

              <div class="stock-identity">

                <strong>{{ stock.symbol }}</strong>

                <span>{{ stock.company_name }}</span>

              </div>



              <div class="stock-meta">

                <span class="exchange-pill">

                  {{ stock.exchange || "Exchange unavailable" }}

                </span>

                <span>{{ stock.sector || "Sector unavailable" }}</span>

              </div>

            </div>

          </div>



          <div class="stock-pagination-footer">

            <p class="stock-range">

              Showing

              <strong>{{ paginationStart }}–{{ paginationEnd }}</strong>

              of <strong>{{ filteredStocks.length }}</strong> stocks

            </p>



            <nav

              v-if="totalPages > 1"

              class="stock-pagination"

              aria-label="Tracked stocks pagination"

            >

              <button

                type="button"

                class="pagination-button"

                :disabled="currentPage <= 1"

                @click="goToPage(currentPage - 1)"

              >

                <span aria-hidden="true">‹</span>

                Previous

              </button>



              <span class="pagination-page">

                Page {{ currentPage }} of {{ totalPages }}

              </span>



              <button

                type="button"

                class="pagination-button"

                :disabled="currentPage >= totalPages"

                @click="goToPage(currentPage + 1)"

              >

                Next

                <span aria-hidden="true">›</span>

              </button>

            </nav>

          </div>

        </template>

      </div>

    </section>



    <!-- Pick any stock from the existing catalogue for technical research. -->
    <section
      v-if="stocks.length > 0"
      class="chart-stock-toolbar"
      aria-label="Price history stock selection"
    >
      <div class="chart-stock-intro">
        <span class="chart-stock-eyebrow">CHART &amp; TECHNICAL ANALYSIS</span>
        <h2>Explore a stock</h2>
        <p>Switch the price chart, market regime, performance, and explainability to any tracked stock.</p>
      </div>

      <div class="chart-stock-controls">
        <div class="chart-stock-field">
          <label for="chart-stock-search">Find a stock</label>
          <input
            id="chart-stock-search"
            v-model="chartStockSearch"
            type="search"
            placeholder="Symbol or company name"
            autocomplete="off"
          />
        </div>
        <div class="chart-stock-field">
          <label for="chart-stock-select">Stock for chart</label>
          <select
            id="chart-stock-select"
            v-model="chartSymbol"
            :disabled="loadingStocks"
          >
            <option
              v-if="selectedChartStock && !chartStockOptions.some(stock => stock.id === selectedChartStock.id)"
              :value="selectedChartStock.symbol"
            >
              {{ selectedChartStock.symbol }} — {{ selectedChartStock.company_name }}
            </option>
            <option
              v-for="stock in chartStockOptions"
              :key="stock.id"
              :value="stock.symbol"
            >
              {{ stock.symbol }} — {{ stock.company_name }}
            </option>
          </select>
        </div>
        <p class="chart-stock-count" role="status">
          {{ chartStockOptions.length }} matching {{ chartStockOptions.length === 1 ? "stock" : "stocks" }}
        </p>
      </div>
    </section>

    <StockPriceChart
      v-if="selectedChartStock"
      :key="selectedChartStock.id"
      :stock-id="selectedChartStock.id"
      :symbol="selectedChartStock.symbol"
    />

    <!-- Explainability follows the same chart stock, not the news selector. -->
    <ExplainabilityPanel
      v-if="selectedChartStock"
      :key="selectedChartStock.symbol"
      :symbol="selectedChartStock.symbol"
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

            <strong class="stat-value" :class="averageScoreClass">

              {{ formatScore(sentiment.average_sentiment_score) }}

            </strong>

            <span class="metric-detail">

              {{ averageScoreDescription }}

            </span>

          </div>



          <div class="sentiment-metric">

            <span class="stat-label">Most common sentiment</span>

            <strong class="stat-value" :class="dominantSentimentClass">

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

                {{ sentiment.articles_analyzed }} analyzed news articles

              </p>

            </div>



            <span class="model-label">FinBERT</span>

          </div>






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

            Last analysis: {{ formatDate(sentiment.latest_analysis_at) }}

          </p>

        </div>

      </div>



      <div v-else-if="sentiment" class="message">

        No analyzed news articles are available for {{ selectedSymbol }}.

        Ingest news and run sentiment analysis first.

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



  onMounted,

  ref,

  watch,

} from "vue";





import {
  getStocks,
  getStockSentiment,
  getCurrentUser,
  getLatestQuote,
  getBenchmarkComparison,
  getMarketDataCoverage,
} from "../services/api";


import StockPriceChart from "../components/charts/StockPriceChart.vue";

import ExplainabilityPanel from "../components/ExplainabilityPanel.vue";



// --------------------------------------------------

// Stocks

// --------------------------------------------------



const stocks = ref([]);

const loadingStocks = ref(true);

const stocksError = ref("");

const marketCoverage = ref(null);
async function loadMarketCoverage() {
  try {
    marketCoverage.value = await getMarketDataCoverage();
  } catch {
    // An unavailable readiness check must not prevent other dashboard content.
    marketCoverage.value = null;
  }
}




const selectedSymbol = ref("");

// Chart selection is independent of quote and news selectors.
const chartSymbol = ref("");
const chartStockSearch = ref("");
const selectedChartStock = computed(
  () => stocks.value.find(stock => stock.symbol === chartSymbol.value) || null
);
const chartStockOptions = computed(() => {
  const query = chartStockSearch.value.trim().toLowerCase();
  if (!query) return stocks.value;
  return stocks.value.filter(stock =>
    String(stock.symbol || "").toLowerCase().includes(query) ||
    String(stock.company_name || "").toLowerCase().includes(query)
  );
});

watch(chartSymbol, symbol => {
  if (!symbol) return;
  // Clear the filter after choosing so the next selection can use the full list.
  chartStockSearch.value = "";
  try {
    window.localStorage.setItem("marketpulse:chart-symbol", symbol);
  } catch {
    // Browser privacy settings may disable storage; selection still works.
  }
});



// --------------------------------------------------
// Latest stock quote
// --------------------------------------------------

const quoteSymbol = ref("");
const latestQuote = ref(null);
const latestQuoteLoading = ref(false);
const latestQuoteError = ref("");

let quoteRequestNumber = 0;

const quoteFreshnessLabel = computed(() => {
  const labels = {
    recent: "Recent",
    latest_available: "Latest available",
    stale: "Stale",
    unknown: "Unknown",
  };

  return labels[latestQuote.value?.freshness_status] || "Unknown";
});

const quoteChangeClass = computed(() => {
  const rawChange = latestQuote.value?.change;

  if (rawChange === null || rawChange === undefined || rawChange === "") {
    return "neutral-text";
  }

  const change = Number(rawChange);
  if (!Number.isFinite(change) || change === 0) return "neutral-text";
  return change > 0 ? "positive-text" : "negative-text";
});

const quoteVolumeLabel = computed(() => {
  if (latestQuote.value?.quote_type === "intraday_1m") {
    return "Session volume";
  }

  if (latestQuote.value?.quote_type === "daily_close") {
    return "Daily volume";
  }

  return "Volume";
});

function formatQuotePrice(value) {
  if (value === null || value === undefined || value === "") return "—";

  const number = Number(value);
  if (!Number.isFinite(number)) return "—";

  const formatted = number.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  const currency = latestQuote.value?.currency;
  return currency ? `${currency} ${formatted}` : formatted;
}

function formatQuoteChange(value) {
  if (value === null || value === undefined || value === "") return "—";

  const number = Number(value);
  if (!Number.isFinite(number)) return "—";

  const sign = number > 0 ? "+" : "";
  return `${sign}${number.toFixed(2)}`;
}

function formatQuotePercent(value) {
  if (value === null || value === undefined || value === "") return "—";

  const number = Number(value);
  if (!Number.isFinite(number)) return "—";

  const sign = number > 0 ? "+" : "";
  return `${sign}${number.toFixed(2)}%`;
}

function formatQuoteVolume(value) {
  if (value === null || value === undefined || value === "") return "—";

  const number = Number(value);
  if (!Number.isFinite(number)) return "—";

  return Math.round(number).toLocaleString();
}

function formatQuoteTimestamp(value) {
  if (!value) return "—";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

async function loadLatestQuote() {
  const symbol = quoteSymbol.value.trim();
  const currentRequest = ++quoteRequestNumber;

  latestQuoteError.value = "";
  latestQuote.value = null;

  if (!symbol) {
    latestQuoteLoading.value = false;
    return;
  }

  latestQuoteLoading.value = true;

  try {
    const result = await getLatestQuote(symbol);

    // Ignore stale responses after the user changes the selected symbol.
    if (currentRequest !== quoteRequestNumber) return;

    latestQuote.value = result;
  } catch (error) {
    if (currentRequest !== quoteRequestNumber) return;

    console.error(`Failed to load quote for ${symbol}:`, error);

    latestQuoteError.value =
      error.response?.data?.detail ||
      `Unable to load the latest available quote for ${symbol}.`;
  } finally {
    if (currentRequest === quoteRequestNumber) {
      latestQuoteLoading.value = false;
    }
  }
}



// --------------------------------------------------
// Market overview (existing benchmark-comparison API)
// --------------------------------------------------

const marketOverviewCards = ref([]);
const marketOverviewLoading = ref(false);
const marketOverviewError = ref("");
const marketOverviewAsOf = ref("");
let marketOverviewRequestNumber = 0;

function toLocalDateString(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function buildMarketOverviewCard(key, label, shortLabel, description, series) {
  const dates = Array.isArray(series?.dates) ? series.dates : [];
  const closes = Array.isArray(series?.close) ? series.close : [];
  const observations = dates
    .map((date, index) => ({
      date,
      close: Number(closes[index]),
    }))
    .filter((point) => point.date && Number.isFinite(point.close) && point.close > 0);

  if (observations.length === 0) {
    return {
      key,
      label,
      shortLabel,
      description,
      available: false,
      level: null,
      dayChangePct: null,
      monthChangePct: null,
      latestDate: "",
      trendClass: "market-index-neutral",
      dayTrendClass: "market-index-neutral",
      sparklinePoints: "0,21 100,21",
    };
  }

  const first = observations[0];
  const latest = observations[observations.length - 1];
  const previous = observations.length > 1
    ? observations[observations.length - 2]
    : null;

  const dayChangePct = previous
    ? ((latest.close / previous.close) - 1) * 100
    : null;
  const monthChangePct = observations.length > 1
    ? ((latest.close / first.close) - 1) * 100
    : null;

  const values = observations.map((point) => point.close);
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const spread = maximum - minimum || 1;
  const sparklinePoints = values.map((value, index) => {
    const x = values.length > 1 ? (index / (values.length - 1)) * 100 : 100;
    const y = 38 - ((value - minimum) / spread) * 32;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");

  const trendClass = monthChangePct == null || monthChangePct === 0
    ? "market-index-neutral"
    : monthChangePct > 0
      ? "market-index-positive"
      : "market-index-negative";
  const dayTrendClass = dayChangePct == null || dayChangePct === 0
    ? "market-index-neutral"
    : dayChangePct > 0
      ? "market-index-positive"
      : "market-index-negative";

  return {
    key,
    label: series?.name || label,
    shortLabel,
    description,
    available: true,
    level: latest.close,
    dayChangePct,
    monthChangePct,
    latestDate: String(latest.date),
    trendClass,
    dayTrendClass,
    sparklinePoints,
  };
}

function formatMarketLevel(value) {
  if (value == null || !Number.isFinite(Number(value))) return "—";
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatMarketPercent(value) {
  if (value == null || !Number.isFinite(Number(value))) return "—";
  const number = Number(value);
  return `${number > 0 ? "+" : ""}${number.toFixed(2)}%`;
}

function formatMarketDate(value) {
  if (!value) return "Date unavailable";
  const date = new Date(`${String(value).slice(0, 10)}T12:00:00`);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}

async function loadMarketOverview() {
  const requestNumber = ++marketOverviewRequestNumber;
  marketOverviewLoading.value = true;
  marketOverviewError.value = "";

  const end = new Date();
  const start = new Date(end);
  start.setDate(start.getDate() - 30);

  try {
    const response = await getBenchmarkComparison(
      toLocalDateString(start),
      toLocalDateString(end),
      ""
    );

    if (requestNumber !== marketOverviewRequestNumber) return;
    if (!response?.benchmarks) {
      throw new Error("The benchmark API returned an unexpected response.");
    }

    const benchmarks = response.benchmarks;
    const cards = [
      buildMarketOverviewCard(
        "sp500",
        "S&P 500",
        "SPX",
        "US large-cap benchmark",
        benchmarks.sp500
      ),
      buildMarketOverviewCard(
        "nasdaq100",
        "Nasdaq 100",
        "NDX",
        "US growth and technology benchmark",
        benchmarks.nasdaq100
      ),
      buildMarketOverviewCard(
        "sector",
        benchmarks.sector?.name || "Sector benchmark",
        "ETF",
        "Configured sector comparison",
        benchmarks.sector
      ),
    ];

    if (!cards.some((card) => card.available)) {
      throw new Error("No benchmark observations are available for this date range.");
    }

    marketOverviewCards.value = cards;
    const availableDates = cards
      .filter((card) => card.available && card.latestDate)
      .map((card) => card.latestDate)
      .sort();
    marketOverviewAsOf.value = availableDates.at(-1) || "";
  } catch (error) {
    if (requestNumber !== marketOverviewRequestNumber) return;
    console.error("Failed to load market overview:", error);
    marketOverviewError.value =
      error.response?.data?.detail ||
      error.message ||
      "Unable to load benchmark market data.";
  } finally {
    if (requestNumber === marketOverviewRequestNumber) {
      marketOverviewLoading.value = false;
    }
  }
}

const STOCKS_PER_PAGE = 10;



const stockSearch = ref("");

const selectedExchange = ref("");

const currentPage = ref(1);



// --------------------------------------------------

// User investment preferences

// --------------------------------------------------



const preferencesLoading = ref(true);

const preferencesError = ref("");



const userPreferences = ref({

  preferred_market: "global",

  risk_tolerance: "moderate",

  investment_horizon: "medium",

  preferred_sectors: [],

});



const marketLabels = {

  global: "Global (US & UK available)",

  us: "United States",

  uk: "United Kingdom",

  pakistan: "Pakistan",

};



const riskLabels = {

  conservative: "Conservative",

  moderate: "Moderate",

  aggressive: "Aggressive",

};



const horizonLabels = {

  short: "Short-term",

  medium: "Medium-term",

  long: "Long-term",

};



const marketLabel = computed(

  () =>

    marketLabels[userPreferences.value.preferred_market] ||

    "Global"

);



const riskLabel = computed(

  () =>

    riskLabels[userPreferences.value.risk_tolerance] ||

    "Moderate"

);



const horizonLabel = computed(

  () =>

    horizonLabels[userPreferences.value.investment_horizon] ||

    "Medium-term"

);



const sectorsLabel = computed(() => {

  const sectors = userPreferences.value.preferred_sectors;



  return Array.isArray(sectors) && sectors.length

    ? sectors.join(", ")

    : "No sectors selected";

});



async function loadUserPreferences() {

  preferencesLoading.value = true;

  preferencesError.value = "";



  try {

    const response = await getCurrentUser();

    const user = response?.user || response;



    userPreferences.value = {

      preferred_market: user?.preferred_market || "global",

      risk_tolerance: user?.risk_tolerance || "moderate",

      investment_horizon: user?.investment_horizon || "medium",

      preferred_sectors: Array.isArray(user?.preferred_sectors)

        ? user.preferred_sectors

        : [],

    };

  } catch (error) {

    console.error(

      "Failed to load investment preferences:",

      error

    );



    preferencesError.value =

      "Unable to load your preferences. Please check your profile or try refreshing.";

  } finally {

    preferencesLoading.value = false;

  }

}



// --------------------------------------------------

// Stock filtering and pagination

// --------------------------------------------------



const availableExchanges = computed(() => {

  return [

    ...new Set(

      stocks.value

        .map((stock) => String(stock.exchange || "").trim())

        .filter(Boolean)

    ),

  ].sort((a, b) => a.localeCompare(b));

});



const filteredStocks = computed(() => {

  const query = stockSearch.value.toLocaleLowerCase();



  return stocks.value.filter((stock) => {

    const searchableText = [

      stock.symbol,

      stock.company_name,

      stock.exchange,

      stock.sector,

    ]

      .map((value) => String(value ?? ""))

      .join(" ")

      .toLocaleLowerCase();



    const matchesSearch =

      !query || searchableText.includes(query);



    const matchesExchange =

      !selectedExchange.value ||

      String(stock.exchange || "").trim() ===

        selectedExchange.value;



    return matchesSearch && matchesExchange;

  });

});



const totalPages = computed(() => {

  return Math.ceil(

    filteredStocks.value.length / STOCKS_PER_PAGE

  );

});



const paginatedStocks = computed(() => {

  const start =

    (currentPage.value - 1) * STOCKS_PER_PAGE;



  return filteredStocks.value.slice(

    start,

    start + STOCKS_PER_PAGE

  );

});



const paginationStart = computed(() => {

  if (filteredStocks.value.length === 0) return 0;



  return (

    (currentPage.value - 1) * STOCKS_PER_PAGE + 1

  );

});



const paginationEnd = computed(() => {

  return Math.min(

    currentPage.value * STOCKS_PER_PAGE,

    filteredStocks.value.length

  );

});



function clearStockFilters() {

  stockSearch.value = "";

  selectedExchange.value = "";

  currentPage.value = 1;

}



function goToPage(page) {

  if (!Number.isFinite(page)) return;



  currentPage.value = Math.min(

    Math.max(1, page),

    Math.max(1, totalPages.value)

  );

}



// Return to page one whenever the filters change.

watch([stockSearch, selectedExchange], () => {

  currentPage.value = 1;

});



// --------------------------------------------------

// News sentiment

// --------------------------------------------------



const sentiment = ref(null);

const sentimentLoading = ref(false);

const sentimentError = ref("");




let requestNumber = 0;



const distributionItems = computed(() => {

  const distribution =

    sentiment.value?.sentiment_distribution || {};



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

  const distribution =

    sentiment.value?.sentiment_distribution;



  if (

    !distribution ||

    !sentiment.value?.articles_analyzed

  ) {

    return "—";

  }



  const labels = [

    { key: "positive", name: "Positive" },

    { key: "neutral", name: "Neutral" },

    { key: "negative", name: "Negative" },

  ];



  return labels.reduce((best, item) => {

    const currentCount =

      distribution[item.key]?.count ?? 0;



    const bestCount =

      distribution[best.key]?.count ?? 0;



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



// --------------------------------------------------

// Load sentiment for selected stock

// --------------------------------------------------



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



    // Ignore outdated responses if the selected stock changed.

    if (currentRequest !== requestNumber) return;



    sentiment.value = result;

  } catch (error) {

    if (currentRequest !== requestNumber) return;



    console.error(

      "Failed to load news sentiment:",

      error

    );



    sentimentError.value =

      error.response?.data?.error ||

      "Unable to load the sentiment summary. Check that Django is running and the API is available.";

  } finally {

    if (currentRequest === requestNumber) {

      sentimentLoading.value = false;

    }

  }

}



// --------------------------------------------------

// Load stock list

// --------------------------------------------------



async function loadStocks() {

  loadingStocks.value = true;

  stocksError.value = "";



  try {

    const result = await getStocks();



    stocks.value = Array.isArray(result)

      ? result

      : result.results || [];



    // Prefer AAPL for the initial dashboard selection.

    selectedSymbol.value =
      stocks.value.find(
        (stock) => stock.symbol?.toUpperCase() === "AAPL"
      )?.symbol ||
      stocks.value[0]?.symbol ||
      "";

    // Restore the chart choice across visits where browser storage allows.
    let preferredChartSymbol = "";
    try {
      preferredChartSymbol = window.localStorage.getItem("marketpulse:chart-symbol") || "";
    } catch {
      // Browser storage may be disabled.
    }
    chartSymbol.value = stocks.value.find(
      stock => stock.symbol === preferredChartSymbol
    )?.symbol || selectedSymbol.value;

    // Quote selection is independent of the news sentiment selector.
    quoteSymbol.value = selectedSymbol.value;

    if (selectedSymbol.value) {
      await Promise.all([
        loadSentiment(),
        loadLatestQuote(),
      ]);
    }

  } catch (error) {

    console.error("Failed to load stocks:", error);



    stocksError.value =

      "Unable to load stocks. Make sure the Django API is running.";

  } finally {

    loadingStocks.value = false;

  }

}




// Initialise dashboard data after the component mounts.
// These calls were accidentally omitted in the previous visual patch,
// leaving the dashboard permanently in its loading state.
onMounted(() => {
  loadStocks();
  loadMarketCoverage();
  loadUserPreferences();
  loadMarketOverview();
});

</script>



<style scoped>

.preview-coverage{
  padding:15px 18px;
  margin:0 0 22px;
  border:1px solid #c7d7ef;
  border-left:4px solid #2563eb;
  border-radius:12px;
  background:#f3f7fd;
  color:#1f3555;
}
.preview-coverage strong{display:block;margin-bottom:5px}
.preview-coverage p{margin:0;line-height:1.6;font-size:13px}

.dashboard {

  max-width: 1440px;

  margin: 0 auto;

  color: var(--text-primary);

}



/* Page header */

.page-header {

  display: flex;

  align-items: flex-start;

  justify-content: space-between;

  gap: 20px;

  margin-bottom: 26px;

}



.page-header h1 {

  margin: 0;

  font-size: 30px;

  letter-spacing: -0.025em;

}



.page-header p {

  margin: 8px 0 0;

  color: var(--text-muted);

  line-height: 1.6;

}



.market-status {

  display: flex;

  align-items: center;

  gap: 8px;

  padding: 8px 12px;

  background: var(--success-soft);

  color: var(--success);

  border-radius: var(--radius-control);

  font-size: 13px;

  font-weight: 600;

  white-space: nowrap;

}



.status-dot {

  width: 8px;

  height: 8px;

  border-radius: 50%;

  background: #10b981;

}



/* Summary cards */

.stats-grid {

  display: grid;

  grid-template-columns: repeat(3, minmax(0, 1fr));

  gap: 18px;

  margin-bottom: 24px;

}



.stat-card,

.sentiment-metric {

  min-width: 0;

  padding: 22px;

  background: var(--surface);

  border: 1px solid var(--border);

  border-radius: var(--radius-card);

  box-shadow: var(--card-shadow);

}



.stat-label {

  display: block;

  margin-bottom: 10px;

  color: var(--text-muted);

  font-size: 13px;

}



.stat-value {

  display: block;

  color: var(--text-primary);

  font-size: 26px;

  line-height: 1.3;

  overflow-wrap: anywhere;

}



/* Main sections */

.stocks-section,

.sentiment-section,

.sentiment-chart-card {

  overflow: hidden;

  background: var(--surface);

  border: 1px solid var(--border);

  border-radius: var(--radius-card);

  box-shadow: var(--card-shadow);

}



.stocks-section {

  margin-bottom: 24px;

}



.section-header {

  display: flex;

  align-items: center;

  justify-content: space-between;

  gap: 16px;

  padding: 22px;

  border-bottom: 1px solid var(--border);

}



.section-header h2 {

  margin: 0;

  font-size: 19px;

  letter-spacing: -0.01em;

}



.section-header p {

  margin: 6px 0 0;

  color: var(--text-muted);

  font-size: 13px;

  line-height: 1.6;

}



.section-count {

  flex: 0 0 auto;

  padding: 6px 10px;

  color: var(--text-secondary);

  background: var(--surface-subtle);

  border: 1px solid var(--border);

  border-radius: 999px;

  font-size: 12px;

  font-weight: 700;

  font-variant-numeric: tabular-nums;

}



/* Stock search and exchange filters */

.stock-list-toolbar {

  display: grid;

  grid-template-columns: minmax(220px, 1.4fr) minmax(180px, 0.8fr) auto;

  align-items: end;

  gap: 14px;

  padding: 18px 22px;

  background: var(--surface-subtle);

  border-bottom: 1px solid var(--border);

}



.stock-search-control,

.stock-market-control {

  display: flex;

  flex-direction: column;

  gap: 7px;

  min-width: 0;

}



.stock-search-control label,

.stock-market-control label {

  color: var(--text-secondary);

  font-size: 12px;

  font-weight: 650;

}



.stock-search-control input,

.stock-market-control select {

  width: 100%;

  min-height: 42px;

  padding: 9px 12px;

  color: var(--text-primary);

  background: var(--surface);

  border: 1px solid var(--border-strong);

  border-radius: var(--radius-control);

  font-size: 13px;

  transition: border-color 140ms ease, box-shadow 140ms ease;

}



.stock-search-control input:focus,

.stock-market-control select:focus {

  border-color: var(--accent);

  outline: 3px solid rgb(37 99 235 / 12%);

}



.clear-filters-button {

  min-height: 40px;

  padding: 9px 12px;

  color: var(--text-secondary);

  background: var(--surface);

  border: 1px solid var(--border-strong);

  border-radius: var(--radius-control);

  font-size: 12px;

  font-weight: 650;

  cursor: pointer;

  white-space: nowrap;

}



.clear-filters-button:hover {

  color: var(--accent-hover);

  background: var(--accent-soft);

  border-color: #bfdbfe;

}



/* Stock rows */

.stock-list {

  display: flex;

  flex-direction: column;

}



.stock-row {

  display: flex;

  align-items: center;

  justify-content: space-between;

  gap: 20px;

  min-height: 76px;

  padding: 16px 22px;

  border-bottom: 1px solid var(--border-soft);

  transition: background 140ms ease;

}



.stock-row:last-child {

  border-bottom: none;

}



.stock-row:hover {

  background: var(--surface-subtle);

}



.stock-identity {

  min-width: 0;

}



.stock-identity strong {

  display: block;

  color: var(--text-primary);

  font-size: 16px;

  letter-spacing: 0.01em;

}



.stock-identity span {

  display: block;

  margin-top: 4px;

  color: var(--text-muted);

  font-size: 13px;

  overflow-wrap: anywhere;

}



.stock-meta {

  display: flex;

  align-items: center;

  justify-content: flex-end;

  gap: 20px;

  text-align: right;

}



.stock-meta span {

  color: var(--text-muted);

  font-size: 12px;

}



.exchange-pill {

  display: inline-flex !important;

  align-items: center;

  width: fit-content;

  padding: 4px 8px;

  color: var(--text-secondary) !important;

  background: var(--surface-subtle);

  border: 1px solid var(--border);

  border-radius: 6px;

  font-size: 11px !important;

  font-weight: 650;

  white-space: nowrap;

}



/* Pagination */

.stock-pagination-footer {

  display: flex;

  align-items: center;

  justify-content: space-between;

  flex-wrap: wrap;

  gap: 14px;

  padding: 14px 20px;

  background: var(--surface);

  border-top: 1px solid var(--border);

}



.stock-range {

  margin: 0;

  color: var(--text-muted);

  font-size: 12px;

  font-variant-numeric: tabular-nums;

}



.stock-range strong {

  color: var(--text-secondary);

  font-weight: 700;

}



.stock-pagination {

  display: flex;

  align-items: center;

  justify-content: flex-end;

  gap: 10px;

}



.pagination-button {

  min-height: 36px;

  padding: 8px 12px;

  color: var(--text-secondary);

  background: var(--surface);

  border: 1px solid var(--border-strong);

  border-radius: var(--radius-control);

  font-size: 12px;

  font-weight: 650;

  cursor: pointer;

  transition: background 140ms ease, border-color 140ms ease;

}



.pagination-button:hover:not(:disabled) {

  color: var(--accent-hover);

  background: var(--accent-soft);

  border-color: #bfdbfe;

}



.pagination-button:disabled {

  opacity: 0.45;

  cursor: not-allowed;

}



.pagination-page {

  color: var(--text-secondary);

  font-size: 12px;

  font-variant-numeric: tabular-nums;

  white-space: nowrap;

}



/* Loading, errors and empty states */

.no-results {

  display: flex;

  flex-direction: column;

  align-items: center;

  gap: 12px;

}



.message {

  padding: 30px;

  color: var(--text-muted);

  text-align: center;

  line-height: 1.6;

}



.message.error {

  color: var(--danger);

  background: var(--danger-soft);

}



/* Sentiment section */

.sentiment-section {

  margin-top: 24px;

}



.sentiment-header {

  display: flex;

  align-items: center;

  justify-content: space-between;

  gap: 24px;

}



.sentiment-controls {

  display: flex;

  align-items: center;

  flex-wrap: wrap;

  gap: 10px;

}



.sentiment-controls label {

  color: var(--text-muted);

  font-size: 13px;

}



.sentiment-controls select {

  min-width: 110px;

  padding: 10px 12px;

  color: var(--text-primary);

  background: var(--surface);

  border: 1px solid var(--border-strong);

  border-radius: var(--radius-control);

  font-size: 14px;

}



.refresh-button {

  padding: 10px 14px;

  color: var(--text-secondary);

  background: var(--surface);

  border: 1px solid var(--border-strong);

  border-radius: var(--radius-control);

  font-size: 13px;

  font-weight: 600;

  cursor: pointer;

}



.refresh-button:hover:not(:disabled) {

  background: var(--surface-subtle);

}



.refresh-button:disabled {

  opacity: 0.55;

  cursor: not-allowed;

}



.sentiment-content {

  padding: 22px;

  background: var(--surface-subtle);

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

  margin-top: 8px;

  color: var(--text-muted);

  font-size: 12px;

  line-height: 1.5;

}



.positive-text {

  color: var(--positive);

}



.neutral-text {

  color: #4b5563;

}



.negative-text {

  color: var(--negative);

}



/* Sentiment chart */

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

  color: var(--text-muted);

  font-size: 13px;

}



.model-label {

  padding: 6px 9px;

  color: var(--accent-hover);

  background: var(--accent-soft);

  border-radius: 6px;

  font-size: 12px;

  font-weight: 600;

  white-space: nowrap;

}



/* Sentiment distribution bars */

.distribution-list {

  display: flex;

  flex-direction: column;

  gap: 16px;

  padding-top: 0;

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

  color: var(--text-secondary);

  font-size: 13px;

}



.distribution-dot {

  flex: 0 0 auto;

  width: 9px;

  height: 9px;

  border-radius: 50%;

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

  background: var(--negative);

}



.distribution-bar-track {

  height: 9px;

  overflow: hidden;

  background: var(--border);

  border-radius: 999px;

}



.distribution-bar {

  height: 100%;

  min-width: 0;

  border-radius: 999px;

  transition: width 250ms ease;

}



.distribution-value {

  color: var(--text-primary);

  font-size: 13px;

  font-weight: 600;

  text-align: right;

  white-space: nowrap;

}



.distribution-value span {

  color: var(--text-muted);

  font-weight: 400;

}



.analysis-timestamp {

  margin: 22px 0 0;

  padding-top: 16px;

  color: var(--text-muted);

  border-top: 1px solid var(--border);

  font-size: 12px;

}



/* Saved investment preferences */

.personalisation-card {

  margin-bottom: 24px;

  padding: 22px;

  background: var(--surface);

  border: 1px solid var(--border);

  border-radius: var(--radius-card);

  box-shadow: var(--card-shadow);

}



.personalisation-heading {

  display: flex;

  align-items: flex-start;

  justify-content: space-between;

  gap: 16px;

  margin-bottom: 20px;

}



.personalisation-heading h2 {

  margin: 0;

  color: var(--text-primary);

  font-size: 20px;

}



.personalisation-heading p:not(.personalisation-eyebrow) {

  margin: 7px 0 0;

  color: var(--text-muted);

  font-size: 14px;

  line-height: 1.6;

}



.personalisation-eyebrow {

  margin: 0 0 8px;

  color: var(--accent);

  font-size: 11px;

  font-weight: 800;

  letter-spacing: 0.12em;

}



.personalisation-status {

  padding: 7px 10px;

  color: var(--text-muted);

  border: 1px solid var(--border);

  border-radius: 8px;

  font-size: 12px;

  white-space: nowrap;

}



.preference-grid {

  display: grid;

  grid-template-columns: repeat(4, minmax(0, 1fr));

  gap: 12px;

}



.preference-item {

  min-width: 0;

  padding: 15px;

  background: var(--surface-subtle);

  border: 1px solid var(--border);

  border-radius: 10px;

}



.preference-item span {

  display: block;

  margin-bottom: 9px;

  color: var(--text-muted);

  font-size: 12px;

}



.preference-item strong {

  display: block;

  color: var(--text-primary);

  font-size: 14px;

  line-height: 1.5;

  overflow-wrap: anywhere;

}



.personalisation-note {

  margin: 16px 0 0;

  color: var(--text-muted);

  font-size: 12px;

  line-height: 1.6;

}



.personalisation-message {

  padding: 16px;

  color: var(--text-muted);

  font-size: 14px;

}



.personalisation-message.error {

  color: var(--danger);

}



/* Responsive layout */

@media (max-width: 1000px) {

  .stock-list-toolbar {

    grid-template-columns: minmax(0, 1fr) minmax(0, 0.8fr);

  }



  .clear-filters-button {

    justify-self: start;

  }

}



@media (max-width: 900px) {

  .sentiment-header {

    align-items: flex-start;

    flex-direction: column;

  }



  .sentiment-metrics {

    grid-template-columns: 1fr;

  }



  .preference-grid {

    grid-template-columns: repeat(2, minmax(0, 1fr));

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

    justify-content: flex-start;

    flex-wrap: wrap;

    gap: 12px;

    text-align: left;

  }

}



@media (max-width: 640px) {

  .section-header {

    align-items: flex-start;

  }



  .stock-list-toolbar {

    grid-template-columns: minmax(0, 1fr);

    padding: 14px;

  }



  .stock-pagination-footer {

    align-items: flex-start;

    flex-direction: column;

    padding: 14px;

  }



  .stock-pagination {

    width: 100%;

    justify-content: space-between;

  }

}



@media (max-width: 520px) {

  .page-header h1 {

    font-size: 25px;

  }



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



  .personalisation-heading {

    flex-direction: column;

  }



  .preference-grid {

    grid-template-columns: 1fr;

  }

}


/* ============================================================
   LATEST STOCK QUOTE
============================================================ */

.quote-section {
  margin-bottom: 24px;
  overflow: hidden;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  box-shadow: var(--card-shadow);
}

.quote-section-header {
  align-items: center;
}

.quote-controls {
  display: flex;
  align-items: end;
  gap: 12px;
}

.quote-select-control {
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 220px;
}

.quote-select-control label {
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 650;
}

.quote-select-control select {
  width: 100%;
  min-height: 40px;
  padding: 9px 12px;
  color: var(--text-primary);
  background: var(--surface);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-control);
  font-size: 13px;
}

.quote-refresh-button {
  min-height: 40px;
  padding: 9px 15px;
  color: #fff;
  background: var(--accent);
  border: 1px solid var(--accent);
  border-radius: var(--radius-control);
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
  white-space: nowrap;
}

.quote-refresh-button:hover:not(:disabled) {
  background: var(--accent-hover);
}

.quote-refresh-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.quote-content {
  padding: 22px;
}

.quote-primary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  padding-bottom: 22px;
  border-bottom: 1px solid var(--border);
}

.quote-primary-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.quote-label {
  color: var(--text-muted);
  font-size: 13px;
}

.quote-price {
  color: var(--text-primary);
  font-size: 34px;
  line-height: 1.2;
  overflow-wrap: anywhere;
  font-variant-numeric: tabular-nums;
}

.quote-symbol {
  color: var(--text-muted);
  font-size: 13px;
}

.quote-change,
.quote-change-percent {
  font-variant-numeric: tabular-nums;
}

.quote-change {
  font-size: 28px;
}

.quote-change-percent {
  font-size: 14px;
  font-weight: 650;
}

.quote-metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-top: 22px;
}

.quote-metric {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  padding: 15px;
  background: var(--surface-subtle);
  border: 1px solid var(--border);
  border-radius: var(--radius-control);
}

.quote-metric span {
  color: var(--text-muted);
  font-size: 12px;
}

.quote-metric strong {
  color: var(--text-primary);
  font-size: 14px;
  overflow-wrap: anywhere;
}

.quote-metric .freshness-recent {
  color: var(--success);
}

.quote-metric .freshness-latest_available,
.quote-metric .freshness-unknown {
  color: var(--text-secondary);
}

.quote-metric .freshness-stale {
  color: var(--danger);
}

.quote-data-note {
  margin: 18px 0 0;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.6;
}

.quote-message {
  padding: 22px;
  color: var(--text-secondary);
  font-size: 14px;
}

.quote-error {
  color: var(--danger);
}

@media (max-width: 850px) {
  .quote-section-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .quote-controls {
    width: 100%;
  }

  .quote-select-control {
    flex: 1;
  }

  .quote-metrics-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 520px) {
  .quote-content {
    padding: 15px;
  }

  .quote-primary-grid {
    grid-template-columns: 1fr;
  }

  .quote-price {
    font-size: 29px;
  }

  .quote-metrics-grid {
    grid-template-columns: 1fr;
  }

  .quote-controls {
    align-items: stretch;
    flex-direction: column;
  }

  .quote-select-control {
    min-width: 0;
  }
}



/* --------------------------------------------------------------------------
   MarketPulse dashboard refresh
   Presentation-only overrides; existing API calls and Vue state are retained.
---------------------------------------------------------------------------- */
.dashboard {
  max-width: 1540px;
  padding-bottom: 36px;
}

.dashboard .page-header {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  align-items: center;
  min-height: 154px;
  margin-bottom: 22px;
  padding: 30px 32px;
  border: 1px solid #1e3a5f;
  border-radius: 20px;
  background:
    radial-gradient(circle at 88% 12%, rgb(59 130 246 / 25%), transparent 28%),
    linear-gradient(115deg, #0b1424 0%, #142945 58%, #163b63 100%);
  box-shadow: 0 16px 36px rgb(15 23 42 / 13%);
}

.dashboard .page-header::after {
  position: absolute;
  z-index: -1;
  right: -42px;
  bottom: -112px;
  width: 300px;
  height: 300px;
  border: 1px solid rgb(191 219 254 / 13%);
  border-radius: 50%;
  box-shadow: 0 0 0 28px rgb(191 219 254 / 4%), 0 0 0 58px rgb(191 219 254 / 3%);
  content: "";
  pointer-events: none;
}

.dashboard .page-header h1 {
  color: #f8fafc;
  font-size: clamp(26px, 3vw, 34px);
  font-weight: 750;
  letter-spacing: -0.04em;
}

.dashboard .page-header p {
  max-width: 620px;
  margin-top: 10px;
  color: #c2d0e0;
  font-size: 14px;
}

.dashboard .market-status {
  position: relative;
  z-index: 1;
  padding: 9px 13px;
  border: 1px solid rgb(167 243 208 / 24%);
  border-radius: 999px;
  background: rgb(5 150 105 / 14%);
  color: #bbf7d0;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.dashboard .market-status .status-dot {
  box-shadow: 0 0 0 4px rgb(16 185 129 / 15%);
}

.dashboard .market-status-loading {
  border-color: rgb(191 219 254 / 25%);
  background: rgb(59 130 246 / 14%);
  color: #dbeafe;
}

.dashboard .market-status-loading .status-dot {
  background: #93c5fd;
}

.dashboard .market-status-error {
  border-color: rgb(254 202 202 / 30%);
  background: rgb(220 38 38 / 15%);
  color: #fecaca;
}

.dashboard .market-status-error .status-dot {
  background: #fca5a5;
}

.dashboard .stats-grid {
  gap: 16px;
  margin-bottom: 22px;
}

.dashboard .stat-card,
.dashboard .sentiment-metric {
  position: relative;
  overflow: hidden;
  padding: 21px 22px;
  border-color: #e4eaf2;
  border-radius: 15px;
  box-shadow: 0 4px 14px rgb(15 23 42 / 4%);
  transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
}

.dashboard .stat-card::before {
  position: absolute;
  top: 0;
  right: 0;
  left: 0;
  height: 3px;
  background: linear-gradient(90deg, #2563eb, #38bdf8);
  content: "";
}

.dashboard .stat-card:hover,
.dashboard .sentiment-metric:hover {
  transform: translateY(-2px);
  border-color: #cbdaf0;
  box-shadow: 0 10px 24px rgb(15 23 42 / 7%);
}

.dashboard .stat-label {
  color: #64748b;
  font-size: 12px;
  font-weight: 650;
  letter-spacing: 0.015em;
}

.dashboard .stat-value {
  margin-top: 5px;
  color: #142338;
  font-size: 27px;
  font-weight: 750;
  letter-spacing: -0.035em;
  font-variant-numeric: tabular-nums;
}

.dashboard .quote-section,
.dashboard .personalisation-card,
.dashboard .stocks-section,
.dashboard .sentiment-section,
.dashboard .sentiment-chart-card,
.dashboard .chart-card {
  border-color: #e3eaf2;
  border-radius: 16px;
  box-shadow: 0 4px 18px rgb(15 23 42 / 4%);
}

.dashboard .quote-section,
.dashboard .personalisation-card,
.dashboard .stocks-section,
.dashboard .sentiment-section {
  margin-bottom: 22px;
}

.dashboard .section-header {
  padding: 21px 23px;
}

.dashboard .section-header h2,
.dashboard .personalisation-heading h2 {
  color: #17263b;
  font-size: 18px;
  font-weight: 730;
  letter-spacing: -0.025em;
}

.dashboard .section-header p,
.dashboard .personalisation-heading p:not(.personalisation-eyebrow) {
  color: #718096;
}

.dashboard .quote-content {
  padding: 24px;
}

.dashboard .quote-primary-grid {
  gap: 22px;
  padding-bottom: 24px;
}

.dashboard .quote-primary-item {
  padding: 2px 0;
}

.dashboard .quote-price {
  color: #142338;
  font-size: clamp(30px, 3.5vw, 40px);
  font-weight: 760;
  letter-spacing: -0.04em;
}

.dashboard .quote-change {
  font-size: 29px;
  font-weight: 740;
  letter-spacing: -0.03em;
}

.dashboard .quote-metric,
.dashboard .preference-item {
  border-color: #e7edf4;
  border-radius: 11px;
  background: #f8fafc;
}

.dashboard .quote-metric strong,
.dashboard .preference-item strong {
  color: #1e293b;
  font-weight: 700;
}

.dashboard .personalisation-card {
  padding: 23px;
}

.dashboard .personalisation-eyebrow {
  color: #2563eb;
  letter-spacing: 0.14em;
}

.dashboard .personalisation-status,
.dashboard .section-count,
.dashboard .model-label {
  border-radius: 999px;
}

.dashboard .stock-list-toolbar {
  background: #f8fafc;
}

.dashboard .stock-row {
  min-height: 72px;
  padding-right: 23px;
  padding-left: 23px;
}

.dashboard .stock-identity strong {
  color: #17263b;
  font-weight: 750;
}

.dashboard .exchange-pill {
  background: #eff6ff;
  border-color: #dbeafe;
  color: #1d4ed8 !important;
}

.dashboard .sentiment-content {
  background: #f8fafc;
}

.dashboard .sentiment-chart-card {
  border-color: #e3eaf2;
  background: #fff;
}

.dashboard .sentiment-metric {
  background: #fff;
}

.dashboard .analysis-timestamp {
  color: #8190a3;
}

.dashboard .quote-refresh-button,
.dashboard .refresh-button,
.dashboard .clear-filters-button,
.dashboard .pagination-button {
  min-height: 40px;
  border-radius: 9px;
  font-weight: 700;
  transition: transform 140ms ease, box-shadow 140ms ease, background 140ms ease;
}

.dashboard .quote-refresh-button:hover:not(:disabled),
.dashboard .refresh-button:hover:not(:disabled),
.dashboard .clear-filters-button:hover,
.dashboard .pagination-button:hover:not(:disabled) {
  transform: translateY(-1px);
}

.dashboard input,
.dashboard select {
  border-radius: 9px !important;
}

@media (max-width: 800px) {
  .dashboard .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .dashboard .page-header {
    align-items: flex-start;
    padding: 24px;
  }
}

@media (max-width: 520px) {
  .dashboard .stats-grid {
    grid-template-columns: 1fr;
  }

  .dashboard .page-header {
    min-height: 0;
    padding: 22px 20px;
    border-radius: 15px;
  }

  .dashboard .section-header {
    padding: 18px;
  }

  .dashboard .quote-content,
  .dashboard .personalisation-card {
    padding: 18px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .dashboard .stat-card,
  .dashboard .sentiment-metric,
  .dashboard button {
    transition: none;
  }
}


/* Market overview cards */
.market-overview-section {
  margin: 0 0 22px;
}

.market-overview-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 14px;
}

.market-overview-eyebrow {
  margin: 0 0 6px;
  color: #2563eb;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.14em;
}

.market-overview-heading h2 {
  margin: 0;
  color: #17263b;
  font-size: 20px;
  font-weight: 760;
  letter-spacing: -0.03em;
}

.market-overview-subtitle {
  margin: 6px 0 0;
  color: #718096;
  font-size: 13px;
  line-height: 1.5;
}

.market-overview-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 10px;
}

.market-overview-asof {
  color: #718096;
  font-size: 11px;
  white-space: nowrap;
}

.market-overview-refresh,
.market-overview-retry {
  min-height: 36px;
  padding: 8px 12px;
  border: 1px solid #d8e2ef;
  border-radius: 9px;
  background: #fff;
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: background 140ms ease, border-color 140ms ease, transform 140ms ease;
}

.market-overview-refresh:hover:not(:disabled),
.market-overview-retry:hover {
  transform: translateY(-1px);
  border-color: #bfdbfe;
  background: #eff6ff;
}

.market-overview-refresh:disabled {
  cursor: wait;
  opacity: 0.65;
}

.market-index-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  align-items: stretch;
  gap: 16px;
}

.market-index-card {
  position: relative;
  display: flex;
  min-width: 0;
  min-height: 286px;
  flex-direction: column;
  overflow: hidden;
  padding: 18px 19px 14px;
  border: 1px solid #e3eaf2;
  border-radius: 15px;
  background: #fff;
  box-shadow: 0 4px 16px rgb(15 23 42 / 4%);
}

.market-index-card::before {
  position: absolute;
  top: 0;
  right: 0;
  left: 0;
  height: 3px;
  background: linear-gradient(90deg, #2563eb, #38bdf8);
  content: "";
}

.market-index-card-heading {
  display: flex;
  align-items: center;
  gap: 11px;
  width: 100%;
  min-width: 0;
  min-height: 42px;
  height: 42px;
}

.market-index-symbol {
  display: grid;
  flex: 0 0 42px;
  width: 42px;
  height: 42px;
  place-items: center;
  border: 1px solid #dbeafe;
  border-radius: 12px;
  background: #eff6ff;
  color: #1d4ed8;
  overflow: hidden;
  padding: 0 2px;
  font-size: 10px;
  font-weight: 850;
  letter-spacing: -0.035em;
  white-space: nowrap;
}

.market-index-name-wrap {
  width: 0;
  min-width: 0;
  flex: 1 1 auto;
  overflow: hidden;
}

.market-index-name-wrap h3 {
  overflow: hidden;
  margin: 0;
  color: #17263b;
  font-size: 14px;
  font-weight: 760;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.market-index-name-wrap p {
  overflow: hidden;
  margin: 4px 0 0;
  color: #8290a3;
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.market-index-period {
  flex: 0 0 auto;
  padding: 5px 8px;
  border: 1px solid #e7edf4;
  border-radius: 999px;
  color: #64748b;
  font-size: 10px;
  font-weight: 800;
}

.market-index-values {
  display: flex;
  min-height: 54px;
  flex-direction: column;
  gap: 3px;
  margin-top: 18px;
}

.market-index-level {
  color: #142338;
  font-size: clamp(23px, 2vw, 29px);
  font-weight: 780;
  letter-spacing: -0.045em;
  font-variant-numeric: tabular-nums;
}

.market-index-unit {
  color: #8a97a8;
  font-size: 10px;
}

.market-index-performance {
  display: flex;
  min-height: 35px;
  align-items: flex-start;
  gap: 18px;
  margin-top: 12px;
}

.market-index-daily,
.market-index-monthly {
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: 13px;
  font-weight: 760;
  font-variant-numeric: tabular-nums;
}

.market-index-daily small,
.market-index-monthly small {
  color: #8a97a8;
  font-size: 10px;
  font-weight: 500;
}

.market-index-positive {
  color: #15803d;
}

.market-index-negative {
  color: #dc2626;
}

.market-index-neutral {
  color: #64748b;
}

.market-index-sparkline {
  height: 44px;
  min-height: 44px;
  flex: 0 0 44px;
  margin-top: auto;
  padding-top: 10px;
  color: #2563eb;
}

.market-index-card.market-index-positive .market-index-sparkline {
  color: #16a34a;
}

.market-index-card.market-index-negative .market-index-sparkline {
  color: #dc2626;
}

.market-index-sparkline svg {
  display: block;
  width: 100%;
  height: 100%;
  overflow: visible;
}

.market-index-date {
  min-height: 27px;
  margin: 7px 0 0;
  padding-top: 9px;
  border-top: 1px solid #eef2f6;
  color: #8a97a8;
  font-size: 10px;
  line-height: 1.4;
}

.market-index-unavailable {
  border-style: dashed;
  background: #fbfcfe;
}

.market-index-unavailable-note {
  padding: 28px 4px 20px;
  color: #8a97a8;
  font-size: 12px;
}

.market-overview-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-height: 112px;
  padding: 22px;
  border: 1px solid #e3eaf2;
  border-radius: 15px;
  background: #fff;
  color: #718096;
  font-size: 13px;
  text-align: center;
}

.market-overview-state-error {
  flex-wrap: wrap;
  color: #b91c1c;
}

.market-overview-footnote {
  margin: 10px 2px 0;
  color: #8a97a8;
  font-size: 10px;
  line-height: 1.5;
}

@media (max-width: 900px) {
  .market-index-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .market-overview-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .market-overview-actions {
    width: 100%;
    justify-content: space-between;
  }

  .market-index-grid {
    grid-template-columns: 1fr;
  }
}

@media (prefers-reduced-motion: reduce) {
  .market-overview-refresh,
  .market-overview-retry {
    transition: none;
  }
}


/* Dashboard price-history stock picker: independent from quotes and sentiment. */
.chart-stock-toolbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 18px;
  margin: 24px 0 14px;
  padding: 20px 24px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--surface);
}
.chart-stock-intro {
  flex: 1 1 260px;
  min-width: 0;
}
.chart-stock-eyebrow {
  color: var(--text-muted);
  font-size: 11px;
  letter-spacing: .13em;
  font-weight: 700;
}
.chart-stock-intro h2 {
  margin: 7px 0 5px;
  color: var(--text-primary);
  font-size: 20px;
}
.chart-stock-intro p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.5;
}
.chart-stock-controls {
  display: flex;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 12px;
  flex: 1 1 450px;
  justify-content: flex-end;
}
.chart-stock-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  flex: 1 1 175px;
}
.chart-stock-field label {
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 650;
}
.chart-stock-field input,
.chart-stock-field select {
  box-sizing: border-box;
  width: 100%;
  min-height: 42px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-control);
  padding: 9px 11px;
  color: var(--text-primary);
  background: var(--surface);
  font-size: 13px;
}
.chart-stock-field input:focus,
.chart-stock-field select:focus {
  outline: 3px solid rgb(37 99 235 / 12%);
  border-color: var(--accent);
}
.chart-stock-count {
  margin: 0 0 11px;
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
}
@media (max-width: 700px) {
  .chart-stock-toolbar { padding: 16px; }
  .chart-stock-controls { justify-content: flex-start; }
  .chart-stock-field { flex-basis: 100%; }
  .chart-stock-count { margin-bottom: 0; }
}

</style>
