
<template>
  <section class="xai-panel">
    <div class="panel-header">
      <div>
        <h2>Prediction Explainability</h2>
        <p>
          Understand which market features influence the model's
          predicted return for {{ symbol }}.
        </p>
      </div>

      <span class="model-tag">SHAP · Explainable AI</span>
    </div>

    <div class="controls">
      <div class="control-field">
        <label for="xai-horizon">Forecast horizon</label>
        <select id="xai-horizon" v-model="selectedHorizon">
          <option value="1">1 day</option>
          <option value="5">5 days</option>
          <option value="20">1 month</option>
          <option value="60">3 months</option>
          <option value="126">6 months</option>
          <option value="252">1 year</option>
        </select>
      </div>

      <div class="control-field">
        <label for="xai-model">ML model</label>
        <select id="xai-model" v-model="selectedModel">
          <option value="random_forest">Random Forest</option>
          <option value="xgboost">XGBoost</option>
          <option value="linear_regression">Linear Regression</option>
        </select>
      </div>

      <button
        type="button"
        :disabled="loading"
        @click="loadExplanation"
      >
        {{ loading ? "Analyzing..." : "Generate explanation" }}
      </button>
    </div>

    <div v-if="loading" class="state-message">
      Training the selected model and calculating SHAP values.
      This can take some time.
    </div>

    <div v-else-if="error" class="state-message error">
      <p>{{ error }}</p>
      <button type="button" class="retry-button" @click="loadExplanation">
        Try again
      </button>
    </div>

    <template v-else-if="result">
      <div class="summary-grid">
        <div class="summary-card">
          <span>Predicted return</span>
          <strong :class="returnClass(result.prediction.return)">
            {{ formatPercent(result.prediction.return) }}
          </strong>
          <small>{{ result.horizon_label }} forecast</small>
        </div>

        <div class="summary-card">
          <span>SHAP baseline</span>
          <strong>
            {{ formatPercent(result.explainability.baseline_return) }}
          </strong>
          <small>Reference model output</small>
        </div>

        <div class="summary-card">
          <span>Estimated price</span>
          <strong>
            {{ formatPrice(result.prediction.estimated_price) }}
          </strong>
          <small>
            Current: {{ formatPrice(result.prediction.current_price) }}
          </small>
        </div>
      </div>

      <div
        v-if="!result.explainability.available"
        class="state-message error"
      >
        The forecast was generated, but SHAP explanations were unavailable.
        {{ result.explainability.message || "" }}
      </div>

      <template v-else>
        <div class="chart-card">
          <div class="chart-title">
            <div>
              <h3>What influenced this prediction?</h3>
              <p>
                Local SHAP contributions for the latest observation.
                Positive values push the prediction above its baseline;
                negative values push it below.
              </p>
            </div>
          </div>

          <div ref="localChart" class="plot"></div>

          <p class="chart-note">
            Contributions are expressed in percentage points of predicted
            return, not stock-price percentage changes.
          </p>
        </div>

        <div class="chart-card">
          <div class="chart-title">
            <div>
              <h3>Most influential features overall</h3>
              <p>
                Mean absolute SHAP values across
                {{ result.explainability.global_evaluation_rows }}
                sampled evaluation observations.
              </p>
            </div>
          </div>

          <div ref="globalChart" class="plot"></div>
        </div>

        <div class="consistency">
          <div>
            <strong>Explanation consistency check</strong>
            <p>
              The baseline plus the local SHAP contributions should
              reconstruct the model output within numerical tolerance.
            </p>
          </div>
          <strong class="consistency-value">
            {{ formatScientific(result.explainability.additivity_difference) }}
          </strong>
        </div>
      </template>

      <p class="disclaimer">
        SHAP explains how the model uses its input features; it does not
        establish causation or guarantee future market performance.
      </p>
    </template>
  </section>
</template>

<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";
import Plotly from "plotly.js-finance-dist-min";

import { getMLReturnPrediction } from "../services/api";

const props = defineProps({
  symbol: {
    type: String,
    required: true,
  },
});

const selectedHorizon = ref("5");
const selectedModel = ref("random_forest");

const loading = ref(false);
const error = ref("");
const result = ref(null);

const localChart = ref(null);
const globalChart = ref(null);

let requestId = 0;

const localContributions = computed(
  () => result.value?.explainability?.local_feature_contributions || []
);

const globalImportance = computed(
  () => result.value?.explainability?.global_feature_importance || []
);

function formatPercent(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) {
    return "—";
  }

  const percent = Number(value) * 100;
  return `${percent > 0 ? "+" : ""}${percent.toFixed(2)}%`;
}

function formatPrice(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) {
    return "—";
  }

  return `$${Number(value).toFixed(2)}`;
}

function formatScientific(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) {
    return "—";
  }

  return Number(value).toExponential(2);
}

function returnClass(value) {
  if (value > 0) return "positive";
  if (value < 0) return "negative";
  return "neutral";
}

function chartLayout(title, height = 390) {
  return {
    title: {
      text: title,
      font: { size: 13, color: "#374151" },
      x: 0,
      xanchor: "left",
    },
    autosize: true,
    height,
    margin: { l: 155, r: 25, t: 42, b: 55 },
    paper_bgcolor: "#ffffff",
    plot_bgcolor: "#ffffff",
    font: {
      family: "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
      size: 12,
      color: "#374151",
    },
    xaxis: {
      zeroline: true,
      zerolinecolor: "#6b7280",
      zerolinewidth: 1,
      gridcolor: "#e5e7eb",
      title: { text: "Percentage points" },
    },
    yaxis: {
      autorange: "reversed",
      automargin: true,
    },
    showlegend: false,
  };
}

async function renderCharts() {
  await nextTick();

  if (!result.value?.explainability?.available) return;

  if (localChart.value && localContributions.value.length) {
    const items = localContributions.value.slice(0, 12);

    await Plotly.react(
      localChart.value,
      [
        {
          type: "bar",
          orientation: "h",
          y: items.map((item) => item.feature),
          x: items.map((item) => item.contribution_percentage_points),
          marker: {
            color: items.map((item) =>
              item.shap_value >= 0 ? "#16a34a" : "#dc2626"
            ),
          },
          hovertemplate:
            "%{y}<br>Contribution: %{x:.5f} percentage points<extra></extra>",
        },
      ],
      chartLayout("Impact relative to baseline", Math.max(340, items.length * 32)),
      {
        responsive: true,
        displayModeBar: false,
      }
    );
  }

  if (globalChart.value && globalImportance.value.length) {
    const items = globalImportance.value.slice(0, 10);

    await Plotly.react(
      globalChart.value,
      [
        {
          type: "bar",
          orientation: "h",
          y: items.map((item) => item.feature),
          x: items.map(
            (item) =>
              item.mean_absolute_contribution_percentage_points
          ),
          marker: { color: "#536dfe" },
          hovertemplate:
            "%{y}<br>Mean absolute contribution: %{x:.5f} pp<extra></extra>",
        },
      ],
      chartLayout("Mean absolute SHAP contribution", Math.max(320, items.length * 34)),
      {
        responsive: true,
        displayModeBar: false,
      }
    );
  }
}


async function loadExplanation() {
  const symbol = props.symbol?.trim().toUpperCase();

  if (!symbol) return;

  const currentRequest = ++requestId;

  loading.value = true;
  error.value = "";
  result.value = null;

  try {
    const response = await getMLReturnPrediction(
      symbol,
      Number(selectedHorizon.value),
      selectedModel.value,
      0.9
    );

    if (currentRequest !== requestId) return;

    result.value = response;

    // Make the result section and chart containers render first.
    loading.value = false;
    await nextTick();

    // Now Plotly can access the actual chart elements.
    if (response.explainability?.available) {
      await renderCharts();
    }
  } catch (err) {
    if (currentRequest !== requestId) return;

    console.error("Failed to generate SHAP explanation:", err);

    error.value =
      err.response?.data?.error ||
      "Unable to generate the forecast explanation. Check the Django server and try again.";
  } finally {
    if (currentRequest === requestId) {
      loading.value = false;
    }
  }
}


function resizeCharts() {
  if (localChart.value) Plotly.Plots.resize(localChart.value);
  if (globalChart.value) Plotly.Plots.resize(globalChart.value);
}

watch(
  () => props.symbol,
  () => loadExplanation()
);

onMounted(() => {
  window.addEventListener("resize", resizeCharts);
  loadExplanation();
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", resizeCharts);

  if (localChart.value) Plotly.purge(localChart.value);
  if (globalChart.value) Plotly.purge(globalChart.value);
});
</script>

<style scoped>
.xai-panel {
  margin-top: 30px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 24px;
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
}

.panel-header h2 {
  margin: 0;
  font-size: 21px;
  color: #111827;
}

.panel-header p,
.chart-title p,
.consistency p {
  margin: 8px 0 0;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.6;
}

.model-tag {
  display: inline-block;
  background: #eef2ff;
  color: #4338ca;
  padding: 7px 10px;
  border-radius: 7px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.controls {
  display: flex;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 14px;
  padding: 20px 24px;
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
}

.control-field {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.control-field label {
  color: #6b7280;
  font-size: 12px;
}

.control-field select {
  min-width: 155px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 10px 12px;
  background: #ffffff;
  color: #111827;
  font-size: 13px;
}

.controls button,
.retry-button {
  border: none;
  border-radius: 8px;
  padding: 11px 16px;
  background: #1f2937;
  color: #ffffff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.controls button:disabled {
  opacity: 0.6;
  cursor: wait;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  padding: 22px 24px 0;
}

.summary-card {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 19px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 11px;
}

.summary-card span,
.summary-card small {
  color: #6b7280;
  font-size: 12px;
  line-height: 1.5;
}

.summary-card strong {
  font-size: 23px;
  overflow-wrap: anywhere;
}

.positive {
  color: #15803d;
}

.negative {
  color: #b91c1c;
}

.neutral {
  color: #374151;
}

.chart-card {
  margin: 22px 24px 0;
  padding: 22px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 11px;
}

.chart-title h3 {
  margin: 0;
  font-size: 17px;
  color: #111827;
}

.plot {
  width: 100%;
  min-height: 320px;
}

.chart-note,
.disclaimer {
  color: #6b7280;
  font-size: 12px;
  line-height: 1.6;
}

.chart-note {
  margin: 8px 0 0;
}

.consistency {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin: 22px 24px 0;
  padding: 18px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 11px;
}

.consistency p {
  max-width: 650px;
}

.consistency-value {
  color: #15803d;
  font-size: 15px;
  white-space: nowrap;
}

.state-message {
  padding: 28px 24px;
  color: #6b7280;
  line-height: 1.6;
}

.error {
  color: #b91c1c;
}

.disclaimer {
  margin: 22px 24px;
}

@media (max-width: 760px) {
  .panel-header {
    flex-direction: column;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .chart-card {
    padding: 12px;
    margin-left: 12px;
    margin-right: 12px;
  }

  .consistency {
    align-items: flex-start;
    flex-direction: column;
    margin-left: 12px;
    margin-right: 12px;
  }

  .controls {
    padding: 16px;
  }

  .control-field,
  .control-field select {
    width: 100%;
  }
}
</style>
