<template>
  <div class="health-page">
    <header class="health-hero">
      <div><p class="eyebrow">LOCAL RESEARCH · DATA QUALITY</p><h1>Research health</h1>
        <p>Check whether stored prices, quotes, fundamentals, and news are available before using a stock's research. No live Yahoo requests or database changes.</p>
      </div>
      <span class="health-tag">Stored data only</span>
    </header>
    <section class="health-filter">
      <div><label for="health-symbols">Symbols (optional)</label>
        <input id="health-symbols" v-model="symbols" type="text" autocomplete="off" placeholder="AAPL, MSFT, NVDA, ABF.L" @keydown.enter.prevent="load" />
        <small>Up to 20 comma-separated symbols. Leave blank to inspect the first 12 active stocks.</small>
      </div>
      <button type="button" :disabled="loading" @click="load">{{ loading ? "Checking…" : "Check stored data" }}</button>
    </section>
    <section v-if="error" class="health-error" role="alert"><strong>Unable to check data</strong><p>{{ error }}</p></section>
    <section v-if="loading && !report" class="health-empty" role="status">Inspecting locally stored records…</section>
    <template v-if="report">
      <div class="health-stats">
        <article><span>Stocks checked</span><strong>{{ report.summary.stocks }}</strong><small>Local records only</small></article>
        <article><span>Need attention</span><strong :class="{ warn: report.summary.stocks_needing_attention }">{{ report.summary.stocks_needing_attention }}</strong><small>Quality or freshness flags</small></article>
        <article><span>No quarterly statements</span><strong>{{ report.summary.stocks_with_no_quarterly_statements }}</strong><small>Availability, not a risk score</small></article>
        <article><span>No stored news</span><strong>{{ report.summary.stocks_with_no_news_articles }}</strong><small>Not a sentiment signal</small></article>
      </div>
      <div class="health-heading"><h2>Coverage by stock</h2><span>Checked {{ displayDate(report.as_of_utc) }}</span></div>
      <p v-if="!report.stocks.length" class="health-empty">No active stocks available for this check.</p>
      <div v-else class="health-grid">
        <article v-for="stock in report.stocks" :key="stock.symbol" class="health-stock">
          <header>
            <div><router-link :to="'/stocks/' + encodeURIComponent(stock.symbol)">{{ stock.symbol }}</router-link><small>{{ stock.exchange || "Unknown exchange" }}</small></div>
            <span :class="stock.status === 'ok' ? 'good' : 'attention'">{{ stock.status === "ok" ? "No quality flags" : "Needs attention" }}</span>
          </header>
          <dl>
            <div><dt>Price records</dt><dd>{{ number(stock.price_observations) }}</dd></div>
            <div><dt>Latest price</dt><dd>{{ stock.latest_price_date || "Unavailable" }}</dd></div>
            <div><dt>Quote source time</dt><dd>{{ displayDate(stock.quote_source_timestamp) }}</dd></div>
            <div><dt>Session (approx.)</dt><dd>{{ sessionLabel(stock.session_context) }}</dd></div>
            <div><dt>Annual / quarterly</dt><dd>{{ stock.annual_statement_count }} / {{ stock.quarterly_statement_count }}</dd></div>
            <div><dt>News records</dt><dd>{{ number(stock.news_article_count) }}</dd></div>
          </dl>
          <div class="health-notes">
            <p v-if="stock.flags.length" class="attention-text"><strong>Attention:</strong> {{ stock.flags.map(readable).join(" · ") }}</p>
            <p v-else class="good-text">No source freshness or OHLC quality warnings under current thresholds.</p>
            <p v-if="stock.availability_gaps.length"><strong>Unavailable:</strong> {{ stock.availability_gaps.map(readable).join(" · ") }}</p>
          </div>
        </article>
      </div>
      <footer class="health-footer">
        <p>Session times are weekday approximations, not exchange holiday or early-close calendars. Missing financial data does not prove a stock is risky. The report makes no external provider requests.</p>
        <p><strong>Forecast warning:</strong> Existing machine-learning models have not demonstrated dependable superiority over simple baselines. These diagnostics are not investment advice or proof of trading readiness.</p>
      </footer>
    </template>
  </div>
</template>
<script setup>
import { ref } from "vue";
import { getResearchReadiness } from "../services/api";
import { parseResearchSymbols, formatReadinessDate, sessionContextLabel, readableReadinessFlag } from "../utils/researchHealth.js";

const symbols = ref("");
const loading = ref(false);
const error = ref("");
const report = ref(null);
const readable = readableReadinessFlag;
const number = (value) => Number.isFinite(Number(value)) ? Number(value).toLocaleString() : "Unavailable";
const displayDate = formatReadinessDate;
const sessionLabel = sessionContextLabel;
async function load() {
  if (loading.value) return;
  let query;
  try {
    query = parseResearchSymbols(symbols.value);
  } catch (exc) {
    error.value = exc.message;
    return;
  }
  loading.value = true;
  error.value = "";
  try {
    report.value = await getResearchReadiness(query);
  } catch (err) {
    error.value = err?.response?.data?.detail || "Check the backend connection and sign-in session.";
  } finally {
    loading.value = false;
  }
}
load();
</script>
<style scoped>
.health-page{max-width:1350px;margin:auto;color:#152238}
.health-hero{padding:28px;border:1px solid #dfe8f5;border-radius:17px;background:linear-gradient(115deg,#fff,#eff6ff);display:flex;justify-content:space-between;gap:20px;align-items:center}
.eyebrow{font-size:11px;font-weight:800;letter-spacing:.12em;color:#2563eb;margin:0 0 8px}
.health-hero h1{font-size:clamp(27px,3.5vw,39px);letter-spacing:-.035em;margin:0 0 10px}
.health-hero p{color:#53647a;line-height:1.6;margin:0;max-width:740px}
.health-tag{white-space:nowrap;padding:8px 11px;border-radius:30px;background:#e8f9f1;color:#176e4c;font-size:12px;font-weight:700}
.health-filter{margin:20px 0;padding:20px;display:flex;align-items:flex-end;flex-wrap:wrap;gap:16px;border:1px solid #e3eaf3;border-radius:13px;background:#fff}
.health-filter>div{flex:1 1 300px}.health-filter label{display:block;font-size:13px;font-weight:700;margin-bottom:8px}
.health-filter input{display:block;width:100%;padding:12px;border:1px solid #c4d0df;border-radius:8px}
.health-filter small{display:block;margin-top:7px;color:#64748b;font-size:12px}
.health-filter button{background:#1d4ed8;border:0;color:#fff;border-radius:9px;padding:12px 17px;font-weight:700;cursor:pointer}
.health-filter button:disabled{opacity:.5;cursor:not-allowed}
.health-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}
.health-stats article{display:flex;flex-direction:column;gap:9px;border:1px solid #e1e8f2;border-radius:13px;background:#fff;padding:19px}
.health-stats span,.health-stats small{font-size:12px;color:#64748b}
.health-stats strong{font-size:28px;letter-spacing:-.04em}.health-stats strong.warn{color:#b45309}
.health-heading{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:28px 0 15px}
.health-heading h2{font-size:22px;margin:0}.health-heading span{font-size:12px;color:#64748b}
.health-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
.health-stock{border:1px solid #dfe7f0;border-radius:13px;background:#fff;overflow:hidden}
.health-stock header{padding:18px;display:flex;align-items:center;justify-content:space-between;gap:8px;border-bottom:1px solid #edf2f7}
.health-stock header div{display:flex;flex-direction:column;gap:5px}.health-stock header a{font-size:18px;font-weight:800;color:#1d4ed8;text-decoration:none}
.health-stock header a:hover{text-decoration:underline}.health-stock small{color:#64748b;font-size:12px}
.health-stock header span{font-size:11px;font-weight:700;border-radius:30px;padding:7px 9px;white-space:nowrap}
.good{background:#e5f8ee;color:#176e4c}.attention{background:#fff2da;color:#a16207}
.health-stock dl{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));padding:18px;gap:16px;margin:0}
.health-stock dt{font-size:11px;color:#64748b;margin-bottom:6px}.health-stock dd{font-size:13px;font-weight:700;margin:0;overflow-wrap:anywhere}
.health-notes{padding:12px 18px;border-top:1px solid #edf2f7;color:#56647a;font-size:12px;line-height:1.5}
.health-notes p{margin:6px 0}.attention-text{color:#9a5d0c}.good-text{color:#176e4c}
.health-footer{background:#edf4fc;border-radius:12px;padding:18px 21px;margin:27px 0;color:#526176;font-size:12px;line-height:1.7}
.health-footer p{margin:5px 0}
.health-error,.health-empty{border-radius:12px;border:1px solid #e3eaf3;padding:20px;background:#fff;color:#56647a}
.health-error{color:#b91c1c;border-color:#fecaca;margin-bottom:15px}
@media(max-width:900px){.health-stats{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:700px){.health-grid{grid-template-columns:1fr}.health-hero{padding:20px;flex-wrap:wrap}.health-heading{flex-wrap:wrap}}
@media(max-width:430px){.health-stock header{flex-wrap:wrap}}
</style>