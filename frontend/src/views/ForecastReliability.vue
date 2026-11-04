<template>
  <div class="reliability">
    <header class="intro">
      <p class="eyebrow">HISTORICAL RESEARCH · NOT LIVE ACCURACY</p>
      <h1>Model reliability scorecard</h1>
      <p>Compare historical prediction errors with simple forecasts, directional bias and uncertainty. No model has demonstrated dependable future outperformance.</p>
    </header>
    <p v-if="loading" role="status">Loading historical research evidence…</p>
    <p v-else-if="error" role="alert" class="error">{{ error }}</p>
    <template v-else-if="report">
      <div class="scope">
        <span><b>Research cutoff:</b> {{ report.as_of }}</span>
        <span><b>Forecast horizon:</b> {{ report.horizon }} trading sessions</span>
        <span><b>Live API default:</b> {{ modelLabel(report.live_model) }}</span>
      </div>
      <section class="warning">
        <strong>Experimental evidence only — not a trading signal.</strong>
        <p>These scores come from the separate restored research database and already-inspected development folds, not live forecasts or the Docker preview. A winning result on one stock does not prove future performance.</p>
      </section>
      <div class="filter">
        <label for="model-reliability-symbol">Stock to inspect</label>
        <select id="model-reliability-symbol" v-model="symbol">
          <option v-for="item in report.stocks" :key="item.symbol" :value="item.symbol">{{ item.symbol }}</option>
        </select>
      </div>
      <template v-if="stock">
        <div class="stats">
          <article><small>Strongest simple baseline MAE</small><strong>{{ percent(stock.baseline.mae_percent) }}</strong><small>{{ baselineLabel(stock.baseline.name) }}</small></article>
          <article><small>Held-out historical forecasts</small><strong>{{ stock.oos_observations.toLocaleString() }}</strong><small>{{ stock.folds }} chronological folds</small></article>
          <article><small>Verified prediction interval coverage</small><strong>Not measured</strong><small>Evidence not supplied in historical reports</small></article>
        </div>
        <section class="results">
          <h2>{{ stock.symbol }} · historical model comparison</h2>
          <p>Mean absolute error (MAE) and RMSE are percentage points of *return* error, not stock-price accuracy. Lower is better.</p>
          <div class="scroll">
            <table>
              <thead>
                <tr><th scope="col">Model</th><th scope="col">MAE</th><th scope="col">RMSE</th><th scope="col">vs best baseline</th><th scope="col">Balanced direction</th><th scope="col">Downside specificity</th><th scope="col">Predicted upward</th></tr>
              </thead>
              <tbody>
                <tr v-for="model in stock.models" :key="model.key">
                  <th scope="row">{{ modelLabel(model.key) }}<small v-if="model.key === report.live_model">Current API default</small></th>
                  <td>{{ percent(model.mae_percent) }}</td>
                  <td>{{ percent(model.rmse_percent) }}</td>
                  <td :class="model.improvement_vs_best_baseline_pp > 0 ? 'positive' : 'negative'">{{ delta(model.improvement_vs_best_baseline_pp) }}</td>
                  <td>{{ percent(model.balanced_directional_accuracy_percent) }}</td>
                  <td>{{ percent(model.negative_specificity_percent) }}</td>
                  <td>{{ percent(model.predicted_positive_percent) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p class="footnote">Positive change versus the baseline means smaller historical error. Choosing a winning model on these folds would invalidate their use as an independent test.</p>
        </section>
        <section class="results">
          <h2>Uncertainty and limitations</h2>
          <p>{{ report.uncertainty_note }}</p>
          <p>Returns use next-session-close entry and an unadjusted close-price basis. Dividends, transaction costs, slippage and taxes are excluded. Predictions must remain experimental until validated on untouched or real future data.</p>
          <router-link to="/forecast-performance">See prospective forecast tracking</router-link>
        </section>
      </template>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { getForecastReliability } from "../services/api";
import { modelLabel, baselineLabel, percent, delta } from "../utils/reliabilityScorecard.js";

const report = ref(null);
const loading = ref(true);
const error = ref("");
const symbol = ref("");
const stock = computed(() => report.value?.stocks?.find(item => item.symbol === symbol.value) || null);

onMounted(async () => {
  try {
    const data = await getForecastReliability();
    if (data?.kind !== "historical_research_snapshot" ||
        data?.promotion_approved !== false || !Array.isArray(data.stocks)) {
      throw new Error("Research report is missing required provenance");
    }
    report.value = data;
    symbol.value = data.stocks[0]?.symbol || "";
  } catch {
    error.value = "Could not load the historical reliability scorecard.";
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.reliability{max-width:1250px;margin:auto;color:#17243a;padding-bottom:48px}
.intro{background:linear-gradient(120deg,#fff,#edf4ff);border:1px solid #dce7f5;border-radius:16px;padding:28px}
.intro h1{font-size:clamp(26px,3vw,37px);margin:7px 0}
.intro p{line-height:1.6;color:#53637a;max-width:800px}
.intro .eyebrow{color:#1d4ed8;font-size:11px;letter-spacing:.12em;font-weight:800}
.scope{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0}
.scope span{background:white;border:1px solid #dce7f5;padding:10px;border-radius:8px;font-size:13px}
.warning{background:#fff7e9;border-left:4px solid #b45309;padding:16px 20px;border-radius:8px}
.warning p{line-height:1.6;margin-bottom:0}
.filter{display:flex;align-items:center;gap:14px;margin:20px 0;font-weight:700}
.filter select{border:1px solid #cbd5e1;border-radius:8px;background:white;color:inherit;padding:10px;font:inherit}
.stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
.stats article,.results{background:white;border:1px solid #e2e8f0;border-radius:12px;padding:19px}
.stats article{display:flex;flex-direction:column;gap:8px}
.stats small{font-size:12px;color:#64748b}
.stats strong{font-size:clamp(18px,2.5vw,25px)}
.results{margin-top:20px}
.results h2{font-size:20px;margin:0 0 10px}
.results p{color:#53637a;line-height:1.6}
.scroll{overflow:auto}
table{border-collapse:collapse;min-width:850px;width:100%;font-size:13px}
th,td{padding:13px 10px;text-align:left;border-bottom:1px solid #e2e8f0;font-variant-numeric:tabular-nums;white-space:nowrap}
thead th{background:#f3f7fb;color:#53637a}
tbody th small{display:block;color:#64748b;font-size:11px;margin-top:6px}
.positive{color:#166534;font-weight:700}
.negative,.error{color:#b91c1c;font-weight:700}
.footnote{font-size:12px}
.results a{font-weight:700;color:#1d4ed8}
@media(max-width:700px){.stats{grid-template-columns:1fr}.intro{padding:18px}}
</style>
