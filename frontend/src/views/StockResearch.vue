<template>
  <main class="research-page">
    <div class="research-topline">
      <router-link to="/discover" class="back-link">← Back to Discover Stocks</router-link>
      <span class="workspace-label">EQUITY RESEARCH WORKSPACE</span>
    </div>

    <section v-if="loading" class="state-card" aria-live="polite">
      <span class="loading-mark"></span>
      <div>
        <strong>Loading {{ symbol }} research</strong>
        <p>Retrieving the stock catalogue record and latest available market data.</p>
      </div>
    </section>

    <section v-else-if="pageError" class="state-card state-error" role="alert">
      <div>
        <strong>Unable to open this stock</strong>
        <p>{{ pageError }}</p>
        <button type="button" class="primary-button" @click="loadStock">Try again</button>
      </div>
    </section>

    <template v-else-if="stock">
      <header class="stock-hero">
        <div class="stock-heading">
          <div class="symbol-tile">{{ stock.symbol }}</div>
          <div class="stock-heading-copy">
            <p class="eyebrow">{{ marketLabel }} · {{ stock.exchange || "Exchange unavailable" }}</p>
            <h1>{{ stock.company_name || stock.symbol }}</h1>
            <p class="stock-subtitle">
              <span>{{ stock.sector || "Sector unavailable" }}</span>
              <span class="dot-separator">·</span>
              <span>{{ stock.industry || "Industry unavailable" }}</span>
            </p>
          </div>
        </div>
        <div class="hero-actions">
          <span class="catalog-badge">In stock catalogue</span>
          <button type="button" class="secondary-button" @click="refreshQuote" :disabled="quoteLoading">
            {{ quoteLoading ? "Refreshing…" : "Check stored quote" }}
          </button>
        </div>
      </header>

      <section class="quote-panel" aria-label="Latest available stock quote">
        <div v-if="quoteLoading && !quote" class="quote-state">Loading latest available quote…</div>
        <div v-else-if="quoteError" class="quote-state quote-error">
          <span>{{ quoteError }}</span>
          <button type="button" class="text-action" @click="refreshQuote">Try again</button>
        </div>
        <template v-else-if="quote">
          <div class="quote-main">
            <div>
              <span class="field-label">Latest available price</span>
              <strong class="quote-price">{{ formatPrice(quote.price, quote.currency) }}</strong>
              <span class="quote-caption">{{ quote.symbol }} · {{ quote.company_name || stock.company_name }}</span>
            </div>
            <div class="change-block">
              <span class="field-label">Daily change</span>
              <strong :class="changeTone">{{ formatSigned(quote.change) }}</strong>
              <span :class="changeTone">{{ formatSignedPercent(quote.change_percent) }}</span>
            </div>
          </div>
          <div class="quote-meta-grid">
            <div><span>Previous close</span><strong>{{ formatPrice(quote.previous_close, quote.currency) }}</strong></div>
            <div><span>Quote type</span><strong>{{ quoteTypeLabel }}</strong></div>
            <div><span>Data freshness</span><strong :class="freshnessTone">{{ freshnessLabel }}</strong></div>
            <div><span>Source timestamp</span><strong>{{ formatDate(quote.source_timestamp) }}</strong></div>
            <div><span>Provider</span><strong>{{ quote.provider || "Unavailable" }}</strong></div>
          </div>
          <p v-if="quote.data_note" class="data-note">{{ quote.data_note }}</p>
          <p class="data-note">
            Checks stored API quotes approximately every 60 seconds while this tab is visible.
            Run the optional personal market monitor to update prices from yfinance.
            This is not guaranteed exchange-real-time data.
          </p>
        </template>
        <div v-else class="quote-state">No quote is currently available for {{ stock.symbol }}.</div>
      </section>

      <section class="sentiment-panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">NEWS CONTEXT</p>
            <h2>News sentiment</h2>
            <p class="muted">Classification of retrieved article text; this is not a forecast of stock returns.</p>
          </div>
          <button type="button" class="secondary-button" @click="refreshSentiment" :disabled="sentimentLoading">
            {{ sentimentLoading ? "Refreshing…" : "Refresh sentiment" }}
          </button>
        </div>

        <div v-if="sentimentLoading && !sentiment" class="sentiment-state">Loading sentiment summary…</div>
        <div v-else-if="sentimentError" class="sentiment-state state-error">
          {{ sentimentError }}
          <button type="button" class="text-action" @click="refreshSentiment">Try again</button>
        </div>
        <div v-else-if="sentiment && sentiment.articles_analyzed > 0" class="sentiment-body">
          <div class="sentiment-summary">
            <article class="sentiment-stat">
              <span>Articles analyzed</span>
              <strong>{{ sentiment.articles_analyzed }}</strong>
              <small>{{ sentiment.articles_with_scores ?? 0 }} with scores</small>
            </article>
            <article class="sentiment-stat">
              <span>Average sentiment</span>
              <strong :class="scoreTone">{{ formatScore(sentiment.average_sentiment_score) }}</strong>
              <small>{{ sentimentDescription }}</small>
            </article>
            <article class="sentiment-stat">
              <span>Most common</span>
              <strong>{{ dominantSentiment }}</strong>
              <small>Based on article classifications</small>
            </article>
          </div>
          <div class="distribution-list">
            <div v-for="item in distributionItems" :key="item.key" class="distribution-row">
              <div class="distribution-name"><span class="distribution-dot" :class="item.key"></span>{{ item.label }}</div>
              <div class="distribution-track"><span :class="item.key" :style="{ width: `${item.percentage}%` }"></span></div>
              <strong>{{ item.count }} <small>({{ item.percentage.toFixed(1) }}%)</small></strong>
            </div>
          </div>
          <p class="sentiment-footnote">Last analysis: {{ formatDate(sentiment.latest_analysis_at) }}</p>
        </div>
        <div v-else class="sentiment-state">No analyzed news articles are currently available for {{ stock.symbol }}.</div>
      </section>

      <div class="research-section-heading">
        <div>
          <p class="eyebrow">PRICE, PERFORMANCE & RISK</p>
          <h2>Quantitative research</h2>
          <p>Historical price analysis, technical indicators, benchmark comparisons, fundamentals and risk metrics.</p>
        </div>
      </div>
      <StockPriceChart :key="`${stock.id}-${stock.symbol}`" :stock-id="stock.id" :symbol="stock.symbol" />

      <div class="research-section-heading explainability-heading">
        <div>
          <p class="eyebrow">MODEL INTERPRETATION</p>
          <h2>AI prediction explainability</h2>
          <p>Inspect the selected model output and the features contributing to it.</p>
        </div>
      </div>
      <ExplainabilityPanel :key="`xai-${stock.symbol}`" :symbol="stock.symbol" />

      <p class="research-disclaimer">
        Market data may be delayed or stale. Historical returns and model outputs are research information only, not guaranteed outcomes or personalised investment advice.
      </p>
    </template>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import StockPriceChart from "../components/charts/StockPriceChart.vue";
import ExplainabilityPanel from "../components/ExplainabilityPanel.vue";
import { getStocks, getLatestQuote, getStockSentiment } from "../services/api";

const route = useRoute();
const stock = ref(null);
const quote = ref(null);
const sentiment = ref(null);
const loading = ref(false);
const quoteLoading = ref(false);
const sentimentLoading = ref(false);
const pageError = ref("");
const quoteError = ref("");
const sentimentError = ref("");
let activeRequest = 0;
let quotePollTimer = null;
const QUOTE_POLL_MS = 60_000;

const symbol = computed(() => String(route.params.symbol || "").trim().toUpperCase());
const marketLabel = computed(() => {
  const exchange = String(stock.value?.exchange || "").toUpperCase();
  return exchange === "LSE" ? "United Kingdom" : "United States";
});
const changeTone = computed(() => {
  const value = Number(quote.value?.change);
  return !Number.isFinite(value) || value === 0 ? "tone-neutral" : value > 0 ? "tone-positive" : "tone-negative";
});
const quoteTypeLabel = computed(() => {
  const type = quote.value?.quote_type;
  if (type === "intraday_1m") return "Intraday 1-minute bar";
  if (type === "daily_close") return "Daily close";
  return "Unavailable";
});
const freshnessLabel = computed(() => ({
  recent: "Recent",
  latest_available: "Latest available",
  stale: "Stale",
  unknown: "Unknown",
}[quote.value?.freshness_status] || "Unknown"));
const freshnessTone = computed(() => quote.value?.freshness_status === "recent" || quote.value?.freshness_status === "latest_available" ? "tone-positive" : "tone-neutral");

const distributionItems = computed(() => {
  const d = sentiment.value?.sentiment_distribution || {};
  return [
    { key: "positive", label: "Positive", count: Number(d.positive?.count || 0), percentage: Number(d.positive?.percentage || 0) },
    { key: "neutral", label: "Neutral", count: Number(d.neutral?.count || 0), percentage: Number(d.neutral?.percentage || 0) },
    { key: "negative", label: "Negative", count: Number(d.negative?.count || 0), percentage: Number(d.negative?.percentage || 0) },
  ];
});
const dominantSentiment = computed(() => {
  if (!sentiment.value?.articles_analyzed) return "—";
  return [...distributionItems.value].sort((a, b) => b.count - a.count)[0]?.label || "—";
});
const scoreTone = computed(() => {
  const score = Number(sentiment.value?.average_sentiment_score);
  if (!Number.isFinite(score) || Math.abs(score) <= 0.05) return "tone-neutral";
  return score > 0 ? "tone-positive" : "tone-negative";
});
const sentimentDescription = computed(() => {
  const score = Number(sentiment.value?.average_sentiment_score);
  if (!Number.isFinite(score)) return "No scores available";
  if (score > 0.05) return "Positive text signal";
  if (score < -0.05) return "Negative text signal";
  return "Near neutral";
});

function formatPrice(value, currency = "USD") {
  if (value === null || value === undefined || value === "" || !Number.isFinite(Number(value))) return "—";
  return `${currency || ""} ${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`.trim();
}
function formatSigned(value) {
  if (value === null || value === undefined || value === "" || !Number.isFinite(Number(value))) return "—";
  const n = Number(value);
  return `${n > 0 ? "+" : ""}${n.toFixed(2)}`;
}
function formatSignedPercent(value) {
  if (value === null || value === undefined || value === "" || !Number.isFinite(Number(value))) return "—";
  const n = Number(value);
  return `${n > 0 ? "+" : ""}${n.toFixed(2)}%`;
}
function formatDate(value) {
  if (!value) return "Unavailable";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? "Unavailable" : d.toLocaleString();
}
function formatScore(value) {
  return value === null || value === undefined || !Number.isFinite(Number(value)) ? "—" : Number(value).toFixed(4);
}

async function loadQuote(targetSymbol = symbol.value, requestId = activeRequest) {
  if (!targetSymbol) return;
  quoteLoading.value = true;
  quoteError.value = "";
  try {
    const result = await getLatestQuote(targetSymbol);
    if (requestId !== activeRequest) return;
    quote.value = result;
  } catch (error) {
    if (requestId !== activeRequest) return;
    console.error(`Unable to load quote for ${targetSymbol}:`, error);
    quote.value = null;
    quoteError.value = error?.response?.data?.detail || `Latest available quote is unavailable for ${targetSymbol}.`;
  } finally {
    if (requestId === activeRequest) quoteLoading.value = false;
  }
}

async function refreshQuote() {
  if (quoteLoading.value) return;
  await loadQuote(symbol.value, activeRequest);
}

function refreshVisibleQuote() {
  // Stored data polling does not itself fetch new Yahoo Finance quotes.
  if (document.visibilityState !== "visible" || !stock.value || quoteLoading.value) {
    return;
  }
  void loadQuote(symbol.value, activeRequest);
}

onMounted(() => {
  quotePollTimer = window.setInterval(refreshVisibleQuote, QUOTE_POLL_MS);
  document.addEventListener("visibilitychange", refreshVisibleQuote);
});

onBeforeUnmount(() => {
  if (quotePollTimer !== null) window.clearInterval(quotePollTimer);
  document.removeEventListener("visibilitychange", refreshVisibleQuote);
  activeRequest += 1;
});

async function refreshSentiment() {
  // Do not pass the click event as a stock symbol. Always use the route symbol.
  await loadSentiment(symbol.value, activeRequest);
}

async function loadSentiment(targetSymbol = symbol.value, requestId = activeRequest) {
  // Defensive guard: a Vue click event is not a valid stock symbol.
  if (typeof targetSymbol !== "string") targetSymbol = symbol.value;
  targetSymbol = targetSymbol.trim().toUpperCase();
  if (!targetSymbol) return;
  sentimentLoading.value = true;
  sentimentError.value = "";
  try {
    const result = await getStockSentiment(targetSymbol, 50);
    if (requestId !== activeRequest) return;
    sentiment.value = result;
  } catch (error) {
    if (requestId !== activeRequest) return;
    console.error(`Unable to load sentiment for ${targetSymbol}:`, error);
    sentiment.value = null;
    sentimentError.value = error?.response?.data?.error || `News sentiment is unavailable for ${targetSymbol}.`;
  } finally {
    if (requestId === activeRequest) sentimentLoading.value = false;
  }
}

async function loadStock() {
  const targetSymbol = symbol.value;
  const requestId = ++activeRequest;
  stock.value = null;
  quote.value = null;
  sentiment.value = null;
  pageError.value = "";
  quoteError.value = "";
  sentimentError.value = "";
  loading.value = true;

  if (!targetSymbol) {
    pageError.value = "A stock symbol was not supplied in the page address.";
    loading.value = false;
    return;
  }

  try {
    const response = await getStocks();
    if (requestId !== activeRequest) return;
    const records = Array.isArray(response) ? response : response?.results || [];
    const match = records.find((item) => String(item.symbol || "").toUpperCase() === targetSymbol);
    if (!match) {
      pageError.value = `${targetSymbol} was not found in the available stock catalogue.`;
      return;
    }

    stock.value = match;
    loading.value = false;
    await Promise.all([
      loadQuote(targetSymbol, requestId),
      loadSentiment(targetSymbol, requestId),
    ]);
  } catch (error) {
    if (requestId !== activeRequest) return;
    console.error(`Unable to load stock record for ${targetSymbol}:`, error);
    pageError.value = error?.response?.data?.detail || "Unable to load the stock catalogue. Check the Django API and try again.";
  } finally {
    if (requestId === activeRequest) loading.value = false;
  }
}

watch(symbol, loadStock, { immediate: true });
</script>

<style scoped>
.research-page {
  max-width: 1480px;
  margin: 0 auto;
  padding-bottom: 34px;
  color: var(--text-primary, #17263d);
}
.research-topline,
.stock-hero,
.hero-actions,
.stock-heading,
.section-heading,
.research-section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}
.research-topline { margin-bottom: 18px; }
.back-link { color: #2563eb; font-size: 13px; font-weight: 700; text-decoration: none; }
.back-link:hover { text-decoration: underline; }
.workspace-label, .eyebrow { color: #2563eb; font-size: 11px; font-weight: 800; letter-spacing: .13em; }
.stock-hero { align-items: flex-start; padding: 26px; margin-bottom: 20px; border: 1px solid #dbe5f2; border-radius: 16px; background: linear-gradient(115deg, #101f36, #1d4776); color: #fff; box-shadow: 0 16px 36px rgba(15, 35, 65, .12); }
.stock-heading { justify-content: flex-start; min-width: 0; }
.symbol-tile { display: grid; place-items: center; min-width: 64px; height: 64px; padding: 0 8px; border: 1px solid rgba(255,255,255,.24); border-radius: 14px; background: rgba(255,255,255,.12); font-size: 15px; font-weight: 850; overflow-wrap: anywhere; }
.stock-heading-copy { min-width: 0; }
.stock-heading-copy .eyebrow { margin: 0 0 7px; color: #9fc5ff; }
.stock-heading h1 { margin: 0; color: #fff; font-size: clamp(24px, 3vw, 34px); letter-spacing: -.035em; overflow-wrap: anywhere; }
.stock-subtitle { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 0; color: #c6d4e6; font-size: 13px; }
.catalog-badge { padding: 7px 10px; border: 1px solid rgba(255,255,255,.22); border-radius: 999px; color: #dceaff; font-size: 12px; font-weight: 700; white-space: nowrap; }
.hero-actions { flex-wrap: wrap; justify-content: flex-end; }
.secondary-button, .primary-button { min-height: 40px; padding: 9px 13px; border: 1px solid #d4deeb; border-radius: 9px; background: #fff; color: #1d4ed8; font: inherit; font-size: 13px; font-weight: 700; cursor: pointer; }
.secondary-button:disabled, .primary-button:disabled { opacity: .55; cursor: wait; }
.primary-button { margin-top: 10px; border-color: #2563eb; background: #2563eb; color: #fff; }
.quote-panel, .sentiment-panel { margin-bottom: 22px; overflow: hidden; border: 1px solid var(--border, #dfe7f1); border-radius: 14px; background: var(--surface, #fff); box-shadow: 0 8px 22px rgba(26, 48, 82, .05); }
.quote-main { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(180px, .7fr); gap: 22px; padding: 24px; }
.field-label, .quote-meta-grid span, .sentiment-stat span { display: block; margin-bottom: 8px; color: var(--text-muted, #71829b); font-size: 12px; font-weight: 600; }
.quote-price { display: block; color: var(--text-primary, #17263d); font-size: clamp(30px, 4vw, 42px); letter-spacing: -.04em; line-height: 1.1; }
.quote-caption { display: block; margin-top: 8px; color: var(--text-muted, #71829b); font-size: 13px; }
.change-block { display: flex; flex-direction: column; align-items: flex-start; justify-content: center; }
.change-block strong { font-size: 27px; line-height: 1.2; }
.change-block span:last-child { margin-top: 5px; font-size: 14px; font-weight: 700; }
.tone-positive { color: #07845d !important; }
.tone-negative { color: #dc2626 !important; }
.tone-neutral { color: #66758b !important; }
.quote-meta-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; padding: 0 24px 20px; }
.quote-meta-grid > div { min-width: 0; padding: 13px; border: 1px solid #e4ebf4; border-radius: 9px; background: #f8fafc; }
.quote-meta-grid span { margin-bottom: 6px; font-size: 11px; }
.quote-meta-grid strong { display: block; color: var(--text-primary, #17263d); font-size: 12px; line-height: 1.45; overflow-wrap: anywhere; }
.data-note { margin: 0; padding: 12px 24px 16px; border-top: 1px solid #edf1f6; color: var(--text-muted, #71829b); font-size: 11px; line-height: 1.5; }
.quote-state, .sentiment-state, .state-card { padding: 22px 24px; color: var(--text-muted, #71829b); font-size: 13px; line-height: 1.6; }
.quote-error, .state-error { color: #b91c1c; }
.text-action { margin-left: 8px; border: 0; background: transparent; color: #2563eb; font: inherit; font-weight: 700; cursor: pointer; }
.section-heading { align-items: flex-start; padding: 22px 24px 16px; }
.section-heading .eyebrow, .research-section-heading .eyebrow { margin: 0 0 7px; }
.section-heading h2, .research-section-heading h2 { margin: 0; color: var(--text-primary, #17263d); font-size: 20px; letter-spacing: -.025em; }
.section-heading .muted, .research-section-heading p:last-child { margin: 6px 0 0; color: var(--text-muted, #71829b); font-size: 13px; line-height: 1.55; }
.sentiment-summary { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; padding: 0 24px 20px; }
.sentiment-stat { min-width: 0; padding: 16px; border: 1px solid #e4ebf4; border-radius: 10px; background: #f8fafc; }
.sentiment-stat strong { display: block; color: var(--text-primary, #17263d); font-size: 23px; line-height: 1.25; overflow-wrap: anywhere; }
.sentiment-stat small { display: block; margin-top: 5px; color: var(--text-muted, #71829b); font-size: 11px; }
.distribution-list { display: grid; gap: 13px; padding: 2px 24px 20px; }
.distribution-row { display: grid; grid-template-columns: 95px minmax(80px, 1fr) 100px; align-items: center; gap: 12px; }
.distribution-name { display: flex; align-items: center; gap: 8px; color: #475569; font-size: 12px; }
.distribution-dot { width: 8px; height: 8px; border-radius: 50%; }
.distribution-dot.positive, .distribution-track span.positive { background: #16a34a; }
.distribution-dot.neutral, .distribution-track span.neutral { background: #9ca3af; }
.distribution-dot.negative, .distribution-track span.negative { background: #dc2626; }
.distribution-track { height: 8px; overflow: hidden; border-radius: 999px; background: #e5e7eb; }
.distribution-track span { display: block; height: 100%; border-radius: inherit; }
.distribution-row > strong { color: #334155; font-size: 12px; text-align: right; white-space: nowrap; }
.distribution-row > strong small { color: #8793a5; font-weight: 400; }
.sentiment-footnote { margin: 0; padding: 13px 24px; border-top: 1px solid #edf1f6; color: var(--text-muted, #71829b); font-size: 11px; }
.research-section-heading { justify-content: flex-start; margin: 30px 0 12px; }
.explainability-heading { margin-top: 34px; }
.research-disclaimer { margin: 18px 0 0; color: var(--text-muted, #71829b); font-size: 11px; line-height: 1.6; }
.loading-mark { width: 22px; height: 22px; border: 3px solid #dbeafe; border-top-color: #2563eb; border-radius: 50%; animation: spin .8s linear infinite; }
.state-card { display: flex; align-items: center; gap: 14px; min-height: 100px; border: 1px solid #dfe7f1; border-radius: 12px; background: #fff; }
.state-card strong { color: #17263d; font-size: 15px; }
.state-card p { margin: 5px 0 0; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (max-width: 1000px) {
  .quote-meta-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 700px) {
  .research-topline, .stock-hero, .hero-actions, .section-heading { align-items: flex-start; flex-direction: column; }
  .workspace-label { display: none; }
  .stock-hero { padding: 20px; }
  .hero-actions { width: 100%; }
  .quote-main { grid-template-columns: 1fr; padding: 20px; }
  .quote-meta-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); padding: 0 20px 18px; }
  .sentiment-summary { grid-template-columns: 1fr; padding: 0 20px 18px; }
  .section-heading { padding: 20px 20px 14px; }
  .distribution-list { padding-left: 20px; padding-right: 20px; }
  .distribution-row { grid-template-columns: 82px minmax(40px, 1fr) 82px; gap: 8px; }
}
</style>
