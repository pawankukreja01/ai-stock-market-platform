<template>
  <section class="chart-card">
    <!-- =====================================================
         CHART HEADER
         ===================================================== -->

    <div class="chart-header">
      <div>
        <h2>{{ symbol }} Price History</h2>

        <p>
          OHLC candlestick chart with moving averages,
          trading volume, RSI and MACD
        </p>
      </div>

      <!-- =====================================================
           PERIOD BUTTONS
           ===================================================== -->

      <div class="period-buttons">
        <button
          v-for="period in periods"
          :key="period.value"
          type="button"
          :class="{
            active: selectedPeriod === period.value
          }"
          @click="changePeriod(period.value)"
        >
          {{ period.label }}
        </button>
      </div>
    </div>


    <!-- =====================================================
         LOADING
         ===================================================== -->

    <div
      v-if="loading"
      class="chart-message"
    >
      Loading market data...
    </div>


    <!-- =====================================================
         ERROR
         ===================================================== -->

    <div
      v-if="error"
      class="chart-message error"
    >
      {{ error }}
    </div>


    <!-- =====================================================
         EMPTY STATE
         ===================================================== -->

    <div
      v-if="
        !loading &&
        !error &&
        prices.length === 0
      "
      class="chart-message"
    >
      No historical market data available.
    </div>


    <!-- =====================================================
         CHARTS
         ===================================================== -->

    <div class="chart-container">

      <!-- PRICE / CANDLESTICK CHART -->

      <div
        ref="priceChartElement"
        class="price-chart"
      ></div>


      <!-- VOLUME CHART -->

      <div
        ref="volumeChartElement"
        class="volume-chart"
      ></div>


      <!-- RSI CHART -->

      <div
        ref="rsiChartElement"
        class="rsi-chart"
      ></div>


      <!-- MACD CHART -->

      <div
        ref="macdChartElement"
        class="macd-chart"
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

import {
  getHistoricalPrices,
} from "../../services/api";


/*
 * =========================================================
 * PROPS
 * =========================================================
 */

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


/*
 * =========================================================
 * CHART REFERENCES
 * =========================================================
 */

const priceChartElement =
  ref(null);

const volumeChartElement =
  ref(null);

const rsiChartElement =
  ref(null);

const macdChartElement =
  ref(null);


/*
 * =========================================================
 * STATE
 * =========================================================
 */

const prices = ref([]);

const loading = ref(false);

const error = ref("");

const selectedPeriod =
  ref("1y");


/*
 * =========================================================
 * AVAILABLE PERIODS
 * =========================================================
 */

const periods = [
  {
    label: "1M",
    value: "1m",
  },

  {
    label: "3M",
    value: "3m",
  },

  {
    label: "6M",
    value: "6m",
  },

  {
    label: "1Y",
    value: "1y",
  },

  {
    label: "3Y",
    value: "3y",
  },

  {
    label: "5Y",
    value: "5y",
  },

  {
    label: "10Y",
    value: "10y",
  },
];


/*
 * =========================================================
 * DATE RANGE
 * =========================================================
 */

const getStartDate = (
  period
) => {

  const today =
    new Date();

  const start =
    new Date(today);


  if (
    period === "1m"
  ) {

    start.setMonth(
      start.getMonth() - 1
    );

  }

  else if (
    period === "3m"
  ) {

    start.setMonth(
      start.getMonth() - 3
    );

  }

  else if (
    period === "6m"
  ) {

    start.setMonth(
      start.getMonth() - 6
    );

  }

  else if (
    period === "1y"
  ) {

    start.setFullYear(
      start.getFullYear() - 1
    );

  }

  else if (
    period === "3y"
  ) {

    start.setFullYear(
      start.getFullYear() - 3
    );

  }

  else if (
    period === "5y"
  ) {

    start.setFullYear(
      start.getFullYear() - 5
    );

  }

  else if (
    period === "10y"
  ) {

    start.setFullYear(
      start.getFullYear() - 10
    );

  }


  return start
    .toISOString()
    .split("T")[0];
};


const getEndDate = () => {

  return new Date()
    .toISOString()
    .split("T")[0];

};


/*
 * =========================================================
 * SIMPLE MOVING AVERAGE
 * =========================================================
 */

const calculateSMA = (
  values,
  period
) => {

  return values.map(
    (_, index) => {

      /*
       * Not enough observations
       * to calculate the SMA.
       */

      if (
        index <
        period - 1
      ) {

        return null;

      }


      const window =
        values.slice(
          index - period + 1,
          index + 1
        );


      const sum =
        window.reduce(
          (
            total,
            value
          ) => total + value,
          0
        );


      return sum / period;

    }
  );

};


/*
 * =========================================================
 * EXPONENTIAL MOVING AVERAGE
 * =========================================================
 */

const calculateEMA = (
  values,
  period
) => {

  const ema =
    new Array(
      values.length
    ).fill(null);


  /*
   * Not enough observations.
   */

  if (
    values.length < period
  ) {

    return ema;

  }


  /*
   * First EMA value is based
   * on a simple moving average.
   */

  let sum = 0;


  for (
    let i = 0;
    i < period;
    i++
  ) {

    sum += values[i];

  }


  let previousEMA =
    sum / period;


  ema[period - 1] =
    previousEMA;


  /*
   * EMA multiplier.
   *
   * Formula:
   *
   * 2 / (period + 1)
   */

  const multiplier =
    2 / (period + 1);


  /*
   * Calculate remaining EMA values.
   */

  for (
    let i = period;
    i < values.length;
    i++
  ) {

    const currentEMA =
      (
        values[i] -
        previousEMA
      ) *
        multiplier +
      previousEMA;


    ema[i] =
      currentEMA;


    previousEMA =
      currentEMA;

  }


  return ema;

};


/*
 * =========================================================
 * RSI CALCULATION
 * =========================================================
 *
 * Standard RSI period = 14
 *
 * Uses Wilder's smoothing method.
 * =========================================================
 */

const calculateRSI = (
  values,
  period = 14
) => {

  const rsi =
    new Array(
      values.length
    ).fill(null);


  if (
    values.length <= period
  ) {

    return rsi;

  }


  /*
   * Initial gains and losses.
   */

  let gains = 0;

  let losses = 0;


  for (
    let i = 1;
    i <= period;
    i++
  ) {

    const change =
      values[i] -
      values[i - 1];


    if (
      change > 0
    ) {

      gains += change;

    }

    else {

      losses +=
        Math.abs(change);

    }

  }


  /*
   * Initial averages.
   */

  let averageGain =
    gains / period;

  let averageLoss =
    losses / period;


  /*
   * Calculate RSI value.
   */

  const calculateRSIValue =
    () => {

      if (
        averageLoss === 0
      ) {

        return 100;

      }


      const relativeStrength =
        averageGain /
        averageLoss;


      return (
        100 -
        100 /
          (1 + relativeStrength)
      );

    };


  /*
   * First RSI value.
   */

  rsi[period] =
    calculateRSIValue();


  /*
   * Wilder's smoothing.
   */

  for (
    let i = period + 1;
    i < values.length;
    i++
  ) {

    const change =
      values[i] -
      values[i - 1];


    const gain =
      change > 0
        ? change
        : 0;


    const loss =
      change < 0
        ? Math.abs(change)
        : 0;


    averageGain =
      (
        averageGain *
          (period - 1) +
        gain
      ) / period;


    averageLoss =
      (
        averageLoss *
          (period - 1) +
        loss
      ) / period;


    rsi[i] =
      calculateRSIValue();

  }


  return rsi;

};


/*
 * =========================================================
 * MACD CALCULATION
 * =========================================================
 *
 * Standard MACD:
 *
 * Fast EMA     = 12
 * Slow EMA     = 26
 * Signal EMA   = 9
 *
 * MACD Line:
 *
 * EMA 12 - EMA 26
 *
 * Histogram:
 *
 * MACD - Signal
 * =========================================================
 */

const calculateMACD = (
  values
) => {

  /*
   * Calculate fast EMA.
   */

  const ema12 =
    calculateEMA(
      values,
      12
    );


  /*
   * Calculate slow EMA.
   */

  const ema26 =
    calculateEMA(
      values,
      26
    );


  /*
   * ---------------------------------------------------------
   * MACD LINE
   * ---------------------------------------------------------
   */

  const macdLine =
    new Array(
      values.length
    ).fill(null);


  for (
    let i = 0;
    i < values.length;
    i++
  ) {

    if (
      ema12[i] === null ||
      ema26[i] === null
    ) {

      continue;

    }


    macdLine[i] =
      ema12[i] -
      ema26[i];

  }


  /*
   * ---------------------------------------------------------
   * SIGNAL LINE
   * ---------------------------------------------------------
   *
   * Signal = 9-period EMA of MACD.
   *
   * First we extract only valid
   * MACD values.
   */

  const validMacdValues =
    macdLine.filter(
      (value) =>
        value !== null
    );


  const signalValues =
    calculateEMA(
      validMacdValues,
      9
    );


  const signalLine =
    new Array(
      values.length
    ).fill(null);


  /*
   * Find first valid MACD index.
   */

  const firstMacdIndex =
    macdLine.findIndex(
      (value) =>
        value !== null
    );


  /*
   * Map signal values back
   * to original dates.
   */

  for (
    let i = 0;
    i < signalValues.length;
    i++
  ) {

    const originalIndex =
      firstMacdIndex + i;


    signalLine[
      originalIndex
    ] =
      signalValues[i];

  }


  /*
   * ---------------------------------------------------------
   * HISTOGRAM
   * ---------------------------------------------------------
   */

  const histogram =
    new Array(
      values.length
    ).fill(null);


  for (
    let i = 0;
    i < values.length;
    i++
  ) {

    if (
      macdLine[i] === null ||
      signalLine[i] === null
    ) {

      continue;

    }


    histogram[i] =
      macdLine[i] -
      signalLine[i];

  }


  return {
    macdLine,
    signalLine,
    histogram,
  };

};


/*
 * =========================================================
 * LOAD HISTORICAL DATA
 * =========================================================
 */

const loadPrices = async () => {

  try {

    loading.value = true;

    error.value = "";


    const startDate =
      getStartDate(
        selectedPeriod.value
      );


    const endDate =
      getEndDate();


    console.log(
      `Loading ${props.symbol} data:`,
      startDate,
      "to",
      endDate
    );


    /*
     * Request data from Django.
     */

    const data =
      await getHistoricalPrices(
        props.stockId,
        startDate,
        endDate
      );


    console.log(
      "Historical API response:",
      data
    );


    console.log(
      "Number of records:",
      data.length
    );


    prices.value =
      data;


    /*
     * Wait for Vue DOM update.
     */

    await nextTick();


    renderCharts();

  }

  catch (err) {

    console.error(
      "Historical market data loading failed:",
      err
    );


    error.value =
      "Unable to load historical market data.";

  }

  finally {

    loading.value = false;

  }

};


/*
 * =========================================================
 * RENDER CHARTS
 * =========================================================
 */

const renderCharts = async () => {

  /*
   * ---------------------------------------------------------
   * PRICE CHART CONTAINER
   * ---------------------------------------------------------
   */

  if (
    !priceChartElement.value
  ) {

    console.error(
      "Price chart container was not found."
    );

    return;

  }


  /*
   * ---------------------------------------------------------
   * VOLUME CHART CONTAINER
   * ---------------------------------------------------------
   */

  if (
    !volumeChartElement.value
  ) {

    console.error(
      "Volume chart container was not found."
    );

    return;

  }


  /*
   * ---------------------------------------------------------
   * RSI CHART CONTAINER
   * ---------------------------------------------------------
   */

  if (
    !rsiChartElement.value
  ) {

    console.error(
      "RSI chart container was not found."
    );

    return;

  }


  /*
   * ---------------------------------------------------------
   * MACD CHART CONTAINER
   * ---------------------------------------------------------
   */

  if (
    !macdChartElement.value
  ) {

    console.error(
      "MACD chart container was not found."
    );

    return;

  }


  /*
   * ---------------------------------------------------------
   * DATA CHECK
   * ---------------------------------------------------------
   */

  if (
    !prices.value.length
  ) {

    console.warn(
      "No prices available for charts."
    );

    return;

  }


  /*
   * =========================================================
   * PREPARE DATA
   * =========================================================
   */

  const dates =
    prices.value.map(
      (item) =>
        item.date
    );


  const openPrices =
    prices.value.map(
      (item) =>
        Number(
          item.open_price
        )
    );


  const highPrices =
    prices.value.map(
      (item) =>
        Number(
          item.high_price
        )
    );


  const lowPrices =
    prices.value.map(
      (item) =>
        Number(
          item.low_price
        )
    );


  const closePrices =
    prices.value.map(
      (item) =>
        Number(
          item.close_price
        )
    );


  const volumes =
    prices.value.map(
      (item) =>
        Number(
          item.volume
        )
    );


  /*
   * =========================================================
   * SMA CALCULATIONS
   * =========================================================
   */

  const sma20 =
    calculateSMA(
      closePrices,
      20
    );


  const sma50 =
    calculateSMA(
      closePrices,
      50
    );


  const sma200 =
    calculateSMA(
      closePrices,
      200
    );


  /*
   * =========================================================
   * RSI CALCULATION
   * =========================================================
   */

  const rsi14 =
    calculateRSI(
      closePrices,
      14
    );


  /*
   * =========================================================
   * MACD CALCULATION
   * =========================================================
   */

  const macd =
    calculateMACD(
      closePrices
    );


  const macdLine =
    macd.macdLine;


  const signalLine =
    macd.signalLine;


  const macdHistogram =
    macd.histogram;


  /*
   * =========================================================
   * DEBUG INFORMATION
   * =========================================================
   */

  console.log(
    "Chart points:",
    closePrices.length
  );


  console.log(
    "SMA 20 points:",
    sma20.filter(
      (value) =>
        value !== null
    ).length
  );


  console.log(
    "SMA 50 points:",
    sma50.filter(
      (value) =>
        value !== null
    ).length
  );


  console.log(
    "SMA 200 points:",
    sma200.filter(
      (value) =>
        value !== null
    ).length
  );


  console.log(
    "RSI 14 points:",
    rsi14.filter(
      (value) =>
        value !== null
    ).length
  );


  console.log(
    "MACD points:",
    macdLine.filter(
      (value) =>
        value !== null
    ).length
  );


  /*
   * =========================================================
   * CANDLESTICK TRACE
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

      fillcolor: "#16a34a",

    },


    decreasing: {

      line: {
        color: "#dc2626",
      },

      fillcolor: "#dc2626",

    },


    hovertemplate:
      "<b>%{x}</b><br>" +
      "Open: $%{open:.2f}<br>" +
      "High: $%{high:.2f}<br>" +
      "Low: $%{low:.2f}<br>" +
      "Close: $%{close:.2f}" +
      "<extra></extra>",

  };


  /*
   * =========================================================
   * SMA 20 TRACE
   * =========================================================
   */

  const sma20Trace = {

    x: dates,

    y: sma20,

    type: "scatter",

    mode: "lines",

    name: "SMA 20",


    line: {

      width: 1.5,

      color: "#2563eb",

    },


    connectgaps: false,


    hovertemplate:
      "<b>%{x}</b><br>" +
      "SMA 20: $%{y:.2f}" +
      "<extra></extra>",

  };


  /*
   * =========================================================
   * SMA 50 TRACE
   * =========================================================
   */

  const sma50Trace = {

    x: dates,

    y: sma50,

    type: "scatter",

    mode: "lines",

    name: "SMA 50",


    line: {

      width: 1.5,

      color: "#f59e0b",

    },


    connectgaps: false,


    hovertemplate:
      "<b>%{x}</b><br>" +
      "SMA 50: $%{y:.2f}" +
      "<extra></extra>",

  };


  /*
   * =========================================================
   * SMA 200 TRACE
   * =========================================================
   */

  const sma200Trace = {

    x: dates,

    y: sma200,

    type: "scatter",

    mode: "lines",

    name: "SMA 200",


    line: {

      width: 1.5,

      color: "#7c3aed",

    },


    connectgaps: false,


    hovertemplate:
      "<b>%{x}</b><br>" +
      "SMA 200: $%{y:.2f}" +
      "<extra></extra>",

  };


  /*
   * =========================================================
   * PRICE CHART LAYOUT
   * =========================================================
   */

  const priceLayout = {

    autosize: true,


    margin: {

      l: 70,

      r: 30,

      t: 50,

      b: 20,

    },


    paper_bgcolor:
      "#ffffff",

    plot_bgcolor:
      "#ffffff",


    xaxis: {

      type: "date",

      showgrid: true,

      showticklabels: false,


      rangeslider: {

        visible: false,

      },

    },


    yaxis: {

      title:
        "Price (USD)",

      tickprefix: "$",

      showgrid: true,

      fixedrange: false,

    },


    hovermode:
      "x unified",


    showlegend: true,


    legend: {

      orientation: "h",

      x: 0,

      y: 1.05,

    },

  };


  /*
   * =========================================================
   * VOLUME COLORS
   * =========================================================
   */

  const volumeColors =
    closePrices.map(
      (close, index) => {

        if (
          index === 0
        ) {

          return "#9ca3af";

        }


        return close >=
          closePrices[
            index - 1
          ]

          ? "#16a34a"

          : "#dc2626";

      }
    );


  /*
   * =========================================================
   * VOLUME TRACE
   * =========================================================
   */

  const volumeTrace = {

    x: dates,

    y: volumes,

    type: "bar",

    name: "Volume",


    marker: {

      color:
        volumeColors,

    },


    hovertemplate:
      "<b>%{x}</b><br>" +
      "Volume: %{y:,}" +
      "<extra></extra>",

  };


  /*
   * =========================================================
   * VOLUME LAYOUT
   * =========================================================
   */

  const volumeLayout = {

    autosize: true,


    margin: {

      l: 70,

      r: 30,

      t: 5,

      b: 50,

    },


    paper_bgcolor:
      "#ffffff",

    plot_bgcolor:
      "#ffffff",


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


  /*
   * =========================================================
   * RSI TRACE
   * =========================================================
   */

  const rsiTrace = {

    x: dates,

    y: rsi14,

    type: "scatter",

    mode: "lines",

    name: "RSI 14",


    line: {

      width: 2,

      color: "#2563eb",

    },


    connectgaps: false,


    hovertemplate:
      "<b>%{x}</b><br>" +
      "RSI 14: %{y:.2f}" +
      "<extra></extra>",

  };


  /*
   * =========================================================
   * RSI LAYOUT
   * =========================================================
   */

  const rsiLayout = {

    autosize: true,


    margin: {

      l: 70,

      r: 30,

      t: 30,

      b: 40,

    },


    paper_bgcolor:
      "#ffffff",

    plot_bgcolor:
      "#ffffff",


    xaxis: {

      type: "date",

      showgrid: true,

    },


    yaxis: {

      title: "RSI",

      range: [0, 100],

      showgrid: true,

      fixedrange: false,

    },


    hovermode:
      "x unified",


    showlegend: false,


    shapes: [

      /*
       * 70 level
       */

      {

        type: "line",

        xref: "paper",

        x0: 0,

        x1: 1,

        y0: 70,

        y1: 70,


        line: {

          width: 1,

          dash: "dash",

          color: "#dc2626",

        },

      },


      /*
       * 30 level
       */

      {

        type: "line",

        xref: "paper",

        x0: 0,

        x1: 1,

        y0: 30,

        y1: 30,


        line: {

          width: 1,

          dash: "dash",

          color: "#16a34a",

        },

      },


      /*
       * 50 level
       */

      {

        type: "line",

        xref: "paper",

        x0: 0,

        x1: 1,

        y0: 50,

        y1: 50,


        line: {

          width: 1,

          dash: "dot",

          color: "#9ca3af",

        },

      },

    ],

  };


  /*
   * =========================================================
   * MACD LINE TRACE
   * =========================================================
   */

  const macdLineTrace = {

    x: dates,

    y: macdLine,

    type: "scatter",

    mode: "lines",

    name: "MACD",


    line: {

      width: 2,

      color: "#2563eb",

    },


    connectgaps: false,


    hovertemplate:
      "<b>%{x}</b><br>" +
      "MACD: %{y:.4f}" +
      "<extra></extra>",

  };


  /*
   * =========================================================
   * MACD SIGNAL LINE TRACE
   * =========================================================
   */

  const signalLineTrace = {

    x: dates,

    y: signalLine,

    type: "scatter",

    mode: "lines",

    name: "Signal",


    line: {

      width: 2,

      color: "#f59e0b",

    },


    connectgaps: false,


    hovertemplate:
      "<b>%{x}</b><br>" +
      "Signal: %{y:.4f}" +
      "<extra></extra>",

  };


  /*
   * =========================================================
   * MACD HISTOGRAM COLORS
   * =========================================================
   */

  const macdHistogramColors =
    macdHistogram.map(
      (value) => {

        if (
          value === null
        ) {

          return "#9ca3af";

        }


        return value >= 0

          ? "#16a34a"

          : "#dc2626";

      }
    );


  /*
   * =========================================================
   * MACD HISTOGRAM TRACE
   * =========================================================
   */

  const macdHistogramTrace = {

    x: dates,

    y: macdHistogram,

    type: "bar",

    name: "Histogram",


    marker: {

      color:
        macdHistogramColors,

    },


    hovertemplate:
      "<b>%{x}</b><br>" +
      "Histogram: %{y:.4f}" +
      "<extra></extra>",

  };


  /*
   * =========================================================
   * MACD LAYOUT
   * =========================================================
   */

  const macdLayout = {

    autosize: true,


    margin: {

      l: 70,

      r: 30,

      t: 30,

      b: 40,

    },


    paper_bgcolor:
      "#ffffff",

    plot_bgcolor:
      "#ffffff",


    xaxis: {

      type: "date",

      showgrid: true,

    },


    yaxis: {

      title: "MACD",

      showgrid: true,

      fixedrange: false,

    },


    hovermode:
      "x unified",


    showlegend: true,


    legend: {

      orientation: "h",

      x: 0,

      y: 1.05,

    },


    /*
     * Zero reference line.
     */

    shapes: [

      {

        type: "line",

        xref: "paper",

        x0: 0,

        x1: 1,

        y0: 0,

        y1: 0,


        line: {

          width: 1,

          dash: "dot",

          color: "#6b7280",

        },

      },

    ],

  };


  /*
   * =========================================================
   * PLOTLY CONFIG
   * =========================================================
   */

  const chartConfig = {

    responsive: true,

    displaylogo: false,

    scrollZoom: true,


    modeBarButtonsToRemove: [

      "lasso2d",

      "select2d",

    ],

  };


  /*
   * =========================================================
   * RENDER PRICE CHART
   * =========================================================
   */

  try {

    await Plotly.react(

      priceChartElement.value,

      [

        candlestickTrace,

        sma20Trace,

        sma50Trace,

        sma200Trace,

      ],

      priceLayout,

      chartConfig

    );


    /*
     * =======================================================
     * RENDER VOLUME CHART
     * =======================================================
     */

    await Plotly.react(

      volumeChartElement.value,

      [volumeTrace],

      volumeLayout,

      chartConfig

    );


    /*
     * =======================================================
     * RENDER RSI CHART
     * =======================================================
     */

    await Plotly.react(

      rsiChartElement.value,

      [rsiTrace],

      rsiLayout,

      chartConfig

    );


    /*
     * =======================================================
     * RENDER MACD CHART
     * =======================================================
     */

    await Plotly.react(

      macdChartElement.value,

      [

        macdHistogramTrace,

        macdLineTrace,

        signalLineTrace,

      ],

      macdLayout,

      chartConfig

    );


    console.log(
      "Candlestick, SMA, volume, RSI and MACD charts rendered successfully."
    );

  }

  catch (err) {

    console.error(
      "Plotly chart rendering failed:",
      err
    );


    error.value =
      "The market data loaded, but the charts could not be rendered.";

  }

};


/*
 * =========================================================
 * PERIOD SELECTION
 * =========================================================
 */

const changePeriod = (
  period
) => {

  if (
    selectedPeriod.value ===
    period
  ) {

    return;

  }


  selectedPeriod.value =
    period;

};


/*
 * =========================================================
 * WATCH PERIOD
 * =========================================================
 */

watch(
  selectedPeriod,
  () => {

    loadPrices();

  }
);


/*
 * =========================================================
 * WATCH STOCK
 * =========================================================
 */

watch(
  () => props.stockId,
  () => {

    loadPrices();

  }
);


/*
 * =========================================================
 * COMPONENT MOUNT
 * =========================================================
 */

onMounted(() => {

  loadPrices();

});


/*
 * =========================================================
 * COMPONENT UNMOUNT
 * =========================================================
 */

onBeforeUnmount(() => {

  /*
   * Destroy price chart.
   */

  if (
    priceChartElement.value
  ) {

    Plotly.purge(
      priceChartElement.value
    );

  }


  /*
   * Destroy volume chart.
   */

  if (
    volumeChartElement.value
  ) {

    Plotly.purge(
      volumeChartElement.value
    );

  }


  /*
   * Destroy RSI chart.
   */

  if (
    rsiChartElement.value
  ) {

    Plotly.purge(
      rsiChartElement.value
    );

  }


  /*
   * Destroy MACD chart.
   */

  if (
    macdChartElement.value
  ) {

    Plotly.purge(
      macdChartElement.value
    );

  }

});
</script>


<style scoped>
/*
 * =========================================================
 * MAIN CHART CARD
 * =========================================================
 */

.chart-card {
  margin-top: 30px;

  background: white;

  border: 1px solid #e5e7eb;

  border-radius: 12px;

  overflow: hidden;
}


/*
 * =========================================================
 * HEADER
 * =========================================================
 */

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


/*
 * =========================================================
 * PERIOD BUTTONS
 * =========================================================
 */

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


/*
 * =========================================================
 * CHART CONTAINER
 * =========================================================
 */

.chart-container {
  width: 100%;

  padding: 10px;

  background: white;
}


/*
 * =========================================================
 * PRICE CHART
 * =========================================================
 */

.price-chart {
  width: 100%;

  height: 500px;
}


/*
 * =========================================================
 * VOLUME CHART
 * =========================================================
 */

.volume-chart {
  width: 100%;

  height: 220px;
}


/*
 * =========================================================
 * RSI CHART
 * =========================================================
 */

.rsi-chart {
  width: 100%;

  height: 260px;
}


/*
 * =========================================================
 * MACD CHART
 * =========================================================
 */

.macd-chart {
  width: 100%;

  height: 280px;
}


/*
 * =========================================================
 * MESSAGES
 * =========================================================
 */

.chart-message {
  padding: 20px;

  text-align: center;

  color: #6b7280;
}


.chart-message.error {
  color: #b91c1c;

  background: #fef2f2;
}


/*
 * =========================================================
 * MOBILE
 * =========================================================
 */

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


  .rsi-chart {
    height: 220px;
  }


  .macd-chart {
    height: 240px;
  }

}
</style>