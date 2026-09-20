<template>
  <section class="chart-card">
    <div class="chart-header">
      <div>
        <h2>{{ symbol }} Price History</h2>
        <p>OHLC candlestick chart with trading volume</p>
      </div>

      <div class="period-buttons">
        <button
          v-for="period in periods"
          :key="period.value"
          type="button"
          :class="{ active: selectedPeriod === period.value }"
          @click="changePeriod(period.value)"
        >
          {{ period.label }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="chart-message">
      Loading market data...
    </div>

    <div v-if="error" class="chart-message error">
      {{ error }}
    </div>

    <div v-if="!loading && !error && prices.length === 0" class="chart-message">
      No historical market data available.
    </div>

    <!--
      Keep the chart containers mounted in the DOM.
      Plotly needs these elements to exist before rendering.
    -->
    <div class="chart-container">
      <div
        ref="priceChartElement"
        class="price-chart"
      ></div>

      <div
        ref="volumeChartElement"
        class="volume-chart"
      ></div>
    </div>
  </section>
</template>

<script setup>
import {
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";

import Plotly from "plotly.js-dist-min";

import { getHistoricalPrices } from "../../services/api";

const props = defineProps({
  stockId: {
    type: Number,
    required: true,
  },

  symbol: {
    type: String,
    required: true,
  },
});

const priceChartElement = ref(null);
const volumeChartElement = ref(null);

const prices = ref([]);
const loading = ref(false);
const error = ref("");

const selectedPeriod = ref("1y");

const periods = [
  { label: "1M", value: "1m" },
  { label: "3M", value: "3m" },
  { label: "6M", value: "6m" },
  { label: "1Y", value: "1y" },
  { label: "3Y", value: "3y" },
  { label: "5Y", value: "5y" },
  { label: "10Y", value: "10y" },
];

const getStartDate = (period) => {
  const today = new Date();
  const start = new Date(today);

  if (period === "1m") {
    start.setMonth(start.getMonth() - 1);
  } else if (period === "3m") {
    start.setMonth(start.getMonth() - 3);
  } else if (period === "6m") {
    start.setMonth(start.getMonth() - 6);
  } else if (period === "1y") {
    start.setFullYear(start.getFullYear() - 1);
  } else if (period === "3y") {
    start.setFullYear(start.getFullYear() - 3);
  } else if (period === "5y") {
    start.setFullYear(start.getFullYear() - 5);
  } else if (period === "10y") {
    start.setFullYear(start.getFullYear() - 10);
  }

  return start.toISOString().split("T")[0];
};

const getEndDate = () => {
  return new Date().toISOString().split("T")[0];
};

const loadPrices = async () => {
  try {
    loading.value = true;
    error.value = "";

    const startDate = getStartDate(selectedPeriod.value);
    const endDate = getEndDate();

    console.log(
      `Loading ${props.symbol} data:`,
      startDate,
      "to",
      endDate
    );

    const data = await getHistoricalPrices(
      props.stockId,
      startDate,
      endDate
    );

    console.log("Historical API response:", data);
    console.log("Number of records:", data.length);

    prices.value = data;

    /*
     * Wait for Vue to finish updating the component.
     * The Plotly containers are always mounted, so they
     * should now be available.
     */
    await nextTick();

    renderCharts();
  } catch (err) {
    console.error(
      "Historical market data loading failed:",
      err
    );

    error.value =
      "Unable to load historical market data.";
  } finally {
    loading.value = false;
  }
};

const renderCharts = async () => {
  if (!priceChartElement.value) {
    console.error("Price chart container was not found.");
    return;
  }

  if (!volumeChartElement.value) {
    console.error("Volume chart container was not found.");
    return;
  }

  if (!prices.value.length) {
    console.warn("No prices available for charts.");
    return;
  }

  const dates = prices.value.map(
    (item) => item.date
  );

  const openPrices = prices.value.map(
    (item) => Number(item.open_price)
  );

  const highPrices = prices.value.map(
    (item) => Number(item.high_price)
  );

  const lowPrices = prices.value.map(
    (item) => Number(item.low_price)
  );

  const closePrices = prices.value.map(
    (item) => Number(item.close_price)
  );

  const volumes = prices.value.map(
    (item) => Number(item.volume)
  );

  console.log(
    "Rendering charts with",
    prices.value.length,
    "records."
  );

  /*
   * =========================================================
   * CANDLESTICK CHART
   * =========================================================
   */

  const candlestickTrace = {
    x: dates,

    open: openPrices,
    high: highPrices,
    low: lowPrices,
    close: closePrices,

    type: "candlestick",

    name: props.symbol,

    increasing: {
      line: {
        color: "#16a34a",
      },
    },

    decreasing: {
      line: {
        color: "#dc2626",
      },
    },

    hovertemplate:
      "<b>%{x}</b><br>" +
      "Open: $%{open:.2f}<br>" +
      "High: $%{high:.2f}<br>" +
      "Low: $%{low:.2f}<br>" +
      "Close: $%{close:.2f}" +
      "<extra></extra>",
  };

  const priceLayout = {
    autosize: true,

    margin: {
      l: 70,
      r: 30,
      t: 20,
      b: 20,
    },

    paper_bgcolor: "#ffffff",
    plot_bgcolor: "#ffffff",

    xaxis: {
      type: "date",

      showgrid: true,

      showticklabels: false,

      rangeslider: {
        visible: false,
      },
    },

    yaxis: {
      title: "Price (USD)",

      tickprefix: "$",

      showgrid: true,

      fixedrange: false,
    },

    hovermode: "x unified",

    showlegend: false,
  };

  /*
   * =========================================================
   * VOLUME CHART
   * =========================================================
   */

  const volumeColors = closePrices.map(
    (close, index) => {
      if (index === 0) {
        return "#9ca3af";
      }

      return close >= closePrices[index - 1]
        ? "#16a34a"
        : "#dc2626";
    }
  );

  const volumeTrace = {
    x: dates,

    y: volumes,

    type: "bar",

    name: "Volume",

    marker: {
      color: volumeColors,
    },

    hovertemplate:
      "<b>%{x}</b><br>" +
      "Volume: %{y:,}" +
      "<extra></extra>",
  };

  const volumeLayout = {
    autosize: true,

    margin: {
      l: 70,
      r: 30,
      t: 5,
      b: 50,
    },

    paper_bgcolor: "#ffffff",
    plot_bgcolor: "#ffffff",

    xaxis: {
      type: "date",

      showgrid: true,

      rangeslider: {
        visible: true,
      },
    },

    yaxis: {
      title: "Volume",

      showgrid: true,

      tickformat: "~s",
    },

    showlegend: false,
  };

  const chartConfig = {
    responsive: true,

    displaylogo: false,

    scrollZoom: true,

    modeBarButtonsToRemove: [
      "lasso2d",
      "select2d",
    ],
  };

  try {
    /*
     * Use react instead of newPlot.
     * This safely updates an existing Plotly chart
     * when the user changes 1M / 3M / 1Y etc.
     */

    await Plotly.react(
      priceChartElement.value,
      [candlestickTrace],
      priceLayout,
      chartConfig
    );

    await Plotly.react(
      volumeChartElement.value,
      [volumeTrace],
      volumeLayout,
      chartConfig
    );

    console.log(
      "Candlestick and volume charts rendered successfully."
    );
  } catch (err) {
    console.error(
      "Plotly chart rendering failed:",
      err
    );

    error.value =
      "The market data loaded, but the charts could not be rendered.";
  }
};

const changePeriod = (period) => {
  if (selectedPeriod.value === period) {
    return;
  }

  selectedPeriod.value = period;
};

watch(selectedPeriod, () => {
  loadPrices();
});

watch(
  () => props.stockId,
  () => {
    loadPrices();
  }
);

onMounted(() => {
  loadPrices();
});

onBeforeUnmount(() => {
  if (priceChartElement.value) {
    Plotly.purge(priceChartElement.value);
  }

  if (volumeChartElement.value) {
    Plotly.purge(volumeChartElement.value);
  }
});
</script>

<style scoped>
.chart-card {
  margin-top: 30px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  overflow: hidden;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  padding: 22px;
  border-bottom: 1px solid #e5e7eb;
}

.chart-header h2 {
  margin: 0;
  font-size: 20px;
}

.chart-header p {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 14px;
}

.period-buttons {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.period-buttons button {
  border: 1px solid #d1d5db;
  background: white;
  color: #374151;
  padding: 7px 11px;
  border-radius: 7px;
  cursor: pointer;
  font-size: 13px;
}

.period-buttons button:hover {
  background: #f3f4f6;
}

.period-buttons button.active {
  background: #111827;
  color: white;
  border-color: #111827;
}

.chart-container {
  width: 100%;
  padding: 10px;
  background: white;
}

.price-chart {
  width: 100%;
  height: 500px;
}

.volume-chart {
  width: 100%;
  height: 220px;
}

.chart-message {
  padding: 20px;
  text-align: center;
  color: #6b7280;
}

.chart-message.error {
  color: #b91c1c;
  background: #fef2f2;
}

@media (max-width: 800px) {
  .chart-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .price-chart {
    height: 400px;
  }

  .volume-chart {
    height: 180px;
  }
}
</style>