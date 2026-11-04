<template>
  <div class="forecast-page">
    <header class="forecast-intro">
      <p class="eyebrow">RESEARCH ACCOUNTABILITY</p>
      <h1>Prospective forecast performance</h1>
      <p>Track predictions recorded before future price outcomes exist. This report compares actual returns against the model and a zero-return baseline, with no invented results.</p>
    </header>
    <div class="forecast-filter">
      <label for="forecast-symbol">Stock symbol (optional)</label>
      <input id="forecast-symbol" v-model="symbol" type="search" placeholder="AAPL or ABF.L" @keydown.enter.prevent="load" />
      <button type="button" :disabled="loading" @click="load">{{ loading ? "Checking…" : "Check results" }}</button>
    </div>
    <div v-if="error" class="forecast-error" role="alert">{{ error }}</div>
    <div v-if="loading && !data" class="forecast-info">Loading stored results…</div>
    <template v-if="data">
      <section class="forecast-stats" aria-label="Forecast evaluation summary">
        <article><span>Recorded forecasts</span><strong>{{ data.issued }}</strong><small>Most recent 1,000</small></article>
        <article><span>Evaluated</span><strong>{{ data.metrics.evaluated }}</strong><small>Future exits observed</small></article>
        <article><span>Awaiting future outcomes</span><strong>{{ data.pending }}</strong><small>No simulated future prices</small></article>
        <article>
          <span>Model MAE</span>
          <strong>{{ percentage(data.metrics.mae) }}</strong>
          <small>Absolute return prediction error</small>
        </article>
        <article>
          <span>Zero-return baseline MAE</span>
          <strong>{{ percentage(data.metrics.zero_return_baseline_mae) }}</strong>
          <small>Same evaluated predictions</small>
        </article>
        <article><span>Direction accuracy</span><strong>{{ percentage(data.metrics.direction_accuracy) }}</strong><small>On evaluated forecasts only</small></article>
      </section>
      <section class="forecast-explanation">
        <h2>What these figures mean</h2>
        <p v-if="!data.metrics.evaluated">No forecasts have matured yet. Prediction accuracy cannot be established until future trading sessions occur and an authorized offline evaluation records the outcomes.</p>
        <p v-else-if="data.metrics.beats_zero_baseline === true">The model currently has a lower average absolute error than the zero-return baseline on these recorded outcomes. This is not proof of trading profitability or future superiority.</p>
        <p v-else>The model has not beaten the zero-return baseline on these recorded outcomes. Its forecasts should not be treated as reliable trading signals.</p>
        <p>Target definition: buy at the next observed session's close after the forecast signal, then measure the return to the close after the forecast horizon. Dividends, costs and slippage are excluded. No past predictions are retroactively manufactured.</p>
        <p><strong>Scope:</strong> Research-only. New forecasts can only be captured intentionally by an authorized staff user on the protected restored test database. This page itself is read-only.</p>
      </section>
    </template>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { getProspectiveResults } from "../services/api";

const symbol = ref("");
const data = ref(null);
const loading = ref(false);
const error = ref("");
const percentage = value => value === null || value === undefined
  ? "Not yet available" : (Number(value) * 100).toFixed(2) + "%";
async function load() {
  if (loading.value) return;
  const clean = symbol.value.trim().toUpperCase();
  if (clean && !/^[A-Z0-9.^=-]{1,20}$/.test(clean)) {
    error.value = "Enter a valid stock ticker.";
    return;
  }
  loading.value = true;
  error.value = "";
  try {
    data.value = await getProspectiveResults(clean);
  } catch (exc) {
    error.value = exc?.response?.data?.detail || "Unable to load stored forecasts.";
  } finally {
    loading.value = false;
  }
}
load();
</script>

<style scoped>
.forecast-page{max-width:1250px;margin:0 auto;color:#17243a}
.forecast-intro{background:linear-gradient(120deg,#fff,#edf4ff);border:1px solid #dbe7f5;padding:27px;border-radius:16px}
.forecast-intro h1{font-size:clamp(26px,3vw,38px);margin:0 0 10px;letter-spacing:-.03em}
.forecast-intro p{max-width:850px;line-height:1.65;color:#53637a}
.forecast-intro p.eyebrow{font-size:11px;letter-spacing:.12em;font-weight:800;color:#1d4ed8;margin:0 0 10px}
.forecast-filter{margin:22px 0;display:flex;align-items:center;gap:12px;flex-wrap:wrap;background:#fff;border:1px solid #e2e8f0;border-radius:11px;padding:16px}
.forecast-filter label{font-size:13px;font-weight:700}
.forecast-filter input{border:1px solid #cbd5e1;border-radius:7px;padding:10px;min-width:180px;flex:1}
.forecast-filter button{background:#1d4ed8;color:#fff;border:0;border-radius:8px;padding:11px 16px;font-weight:700;cursor:pointer}
.forecast-filter button:disabled{opacity:.5;cursor:not-allowed}
.forecast-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
.forecast-stats article{padding:19px;background:#fff;border:1px solid #e2e8f0;border-radius:12px;display:flex;flex-direction:column;gap:8px}
.forecast-stats span,.forecast-stats small{color:#64748b;font-size:12px}
.forecast-stats strong{font-size:clamp(19px,2.5vw,27px);overflow-wrap:anywhere}
.forecast-explanation{margin:22px 0;background:#f0f6ff;border-radius:13px;padding:20px;color:#4f6176;line-height:1.7}
.forecast-explanation h2{font-size:20px;color:#1e293b;margin:0}
.forecast-error,.forecast-info{padding:15px;border:1px solid #e2e8f0;border-radius:9px;background:#fff}
.forecast-error{border-color:#fecaca;color:#b91c1c}
@media(max-width:740px){.forecast-stats{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:440px){.forecast-stats{grid-template-columns:1fr}}
</style>
