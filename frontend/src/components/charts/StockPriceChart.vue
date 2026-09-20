<template>
  <section class="chart-card">
    <div class="chart-header">
      <div>
        <h2>{{ symbol }} Price History</h2>

        <p>
          OHLC candlestick chart with moving averages,
          Bollinger Bands, volume, RSI, MACD, Stochastic,
          ATR and ROC
        </p>
      </div>

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

    <div
      v-if="loading"
      class="chart-message"
    >
      Loading market data...
    </div>

    <div
      v-if="error"
      class="chart-message error"
    >
      {{ error }}
    </div>

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

    <div class="chart-container">
      <div
        ref="priceChartElement"
        class="price-chart"
      ></div>

      <div
        ref="volumeChartElement"
        class="volume-chart"
      ></div>

      <div
        ref="rsiChartElement"
        class="rsi-chart"
      ></div>

      <div
        ref="macdChartElement"
        class="macd-chart"
      ></div>

      <div
        ref="stochasticChartElement"
        class="stochastic-chart"
      ></div>

      <div
        ref="atrChartElement"
        class="atr-chart"
      ></div>

      <div
        ref="rocChartElement"
        class="roc-chart"
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

const priceChartElement =
  ref(null);

const volumeChartElement =
  ref(null);

const rsiChartElement =
  ref(null);

const macdChartElement =
  ref(null);

const stochasticChartElement =
  ref(null);

const atrChartElement =
  ref(null);

const rocChartElement =
  ref(null);

const prices = ref([]);

const loading = ref(false);

const error = ref("");

const selectedPeriod =
  ref("1y");

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

const calculateSMA = (
  values,
  period
) => {
  return values.map(
    (_, index) => {
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

const calculateEMA = (
  values,
  period
) => {
  const ema =
    new Array(
      values.length
    ).fill(null);

  if (
    values.length < period
  ) {
    return ema;
  }

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

  const multiplier =
    2 / (period + 1);

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

  let averageGain =
    gains / period;

  let averageLoss =
    losses / period;

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

  rsi[period] =
    calculateRSIValue();

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

const calculateBollingerBands = (
  values,
  period = 20,
  standardDeviations = 2
) => {
  const middleBand =
    new Array(
      values.length
    ).fill(null);

  const upperBand =
    new Array(
      values.length
    ).fill(null);

  const lowerBand =
    new Array(
      values.length
    ).fill(null);

  for (
    let i = period - 1;
    i < values.length;
    i++
  ) {
    const window =
      values.slice(
        i - period + 1,
        i + 1
      );

    const mean =
      window.reduce(
        (
          total,
          value
        ) => total + value,
        0
      ) / period;

    const squaredDifferences =
      window.map(
        (value) =>
          Math.pow(
            value - mean,
            2
          )
      );

    const variance =
      squaredDifferences.reduce(
        (
          total,
          value
        ) => total + value,
        0
      ) / period;

    const standardDeviation =
      Math.sqrt(
        variance
      );

    middleBand[i] =
      mean;

    upperBand[i] =
      mean +
      standardDeviations *
        standardDeviation;

    lowerBand[i] =
      mean -
      standardDeviations *
        standardDeviation;
  }

  return {
    middleBand,
    upperBand,
    lowerBand,
  };
};

const calculateStochastic = (
  highValues,
  lowValues,
  closeValues,
  period = 14,
  signalPeriod = 3
) => {
  const percentK =
    new Array(
      closeValues.length
    ).fill(null);

  const percentD =
    new Array(
      closeValues.length
    ).fill(null);

  for (
    let i = period - 1;
    i < closeValues.length;
    i++
  ) {
    const highWindow =
      highValues.slice(
        i - period + 1,
        i + 1
      );

    const lowWindow =
      lowValues.slice(
        i - period + 1,
        i + 1
      );

    const highestHigh =
      Math.max(
        ...highWindow
      );

    const lowestLow =
      Math.min(
        ...lowWindow
      );

    const range =
      highestHigh -
      lowestLow;

    if (
      range === 0
    ) {
      percentK[i] = 0;
      continue;
    }

    percentK[i] =
      (
        (
          closeValues[i] -
          lowestLow
        ) /
        range
      ) *
      100;
  }

  for (
    let i = signalPeriod - 1;
    i < percentK.length;
    i++
  ) {
    const window =
      percentK.slice(
        i - signalPeriod + 1,
        i + 1
      );

    if (
      window.some(
        (value) =>
          value === null
      )
    ) {
      continue;
    }

    const sum =
      window.reduce(
        (
          total,
          value
        ) => total + value,
        0
      );

    percentD[i] =
      sum / signalPeriod;
  }

  return {
    percentK,
    percentD,
  };
};

const calculateATR = (
  highValues,
  lowValues,
  closeValues,
  period = 14
) => {
  const trueRanges =
    new Array(
      closeValues.length
    ).fill(null);

  const atr =
    new Array(
      closeValues.length
    ).fill(null);

  if (
    closeValues.length === 0
  ) {
    return atr;
  }

  trueRanges[0] =
    highValues[0] -
    lowValues[0];

  for (
    let i = 1;
    i < closeValues.length;
    i++
  ) {
    const highLow =
      highValues[i] -
      lowValues[i];

    const highPreviousClose =
      Math.abs(
        highValues[i] -
        closeValues[i - 1]
      );

    const lowPreviousClose =
      Math.abs(
        lowValues[i] -
        closeValues[i - 1]
      );

    trueRanges[i] =
      Math.max(
        highLow,
        highPreviousClose,
        lowPreviousClose
      );
  }

  if (
    closeValues.length >= period
  ) {
    const firstWindow =
      trueRanges.slice(
        0,
        period
      );

    const firstATR =
      firstWindow.reduce(
        (
          total,
          value
        ) => total + value,
        0
      ) / period;

    atr[period - 1] =
      firstATR;

    for (
      let i = period;
      i < closeValues.length;
      i++
    ) {
      atr[i] =
        (
          atr[i - 1] *
            (period - 1) +
          trueRanges[i]
        ) / period;
    }
  }

  return atr;
};

const calculateROC = (
  values,
  period = 12
) => {
  const roc =
    new Array(
      values.length
    ).fill(null);

  if (
    values.length <= period
  ) {
    return roc;
  }

  for (
    let i = period;
    i < values.length;
    i++
  ) {
    const previousPrice =
      values[i - period];

    if (
      previousPrice === 0
    ) {
      continue;
    }

    roc[i] =
      (
        (
          values[i] -
          previousPrice
        ) /
        previousPrice
      ) *
      100;
  }

  return roc;
};

const calculateMACD = (
  values
) => {
  const ema12 =
    calculateEMA(
      values,
      12
    );

  const ema26 =
    calculateEMA(
      values,
      26
    );

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

  const firstMacdIndex =
    macdLine.findIndex(
      (value) =>
        value !== null
    );

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

const renderCharts = async () => {
  if (
    !priceChartElement.value ||
    !volumeChartElement.value ||
    !rsiChartElement.value ||
    !macdChartElement.value ||
    !stochasticChartElement.value ||
    !atrChartElement.value ||
    !rocChartElement.value
  ) {
    console.error(
      "One or more chart containers were not found."
    );

    return;
  }

  if (
    !prices.value.length
  ) {
    console.warn(
      "No prices available for charts."
    );

    return;
  }

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

  const bollinger =
    calculateBollingerBands(
      closePrices,
      20,
      2
    );

  const rsi14 =
    calculateRSI(
      closePrices,
      14
    );

  const stochastic =
    calculateStochastic(
      highPrices,
      lowPrices,
      closePrices,
      14,
      3
    );

  const atr14 =
    calculateATR(
      highPrices,
      lowPrices,
      closePrices,
      14
    );

  const roc12 =
    calculateROC(
      closePrices,
      12
    );

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

  console.log(
    "Chart points:",
    closePrices.length
  );

  console.log(
    "Bollinger Band points:",
    bollinger.middleBand.filter(
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
    "Stochastic %K points:",
    stochastic.percentK.filter(
      (value) =>
        value !== null
    ).length
  );

  console.log(
    "Stochastic %D points:",
    stochastic.percentD.filter(
      (value) =>
        value !== null
    ).length
  );

  console.log(
    "ATR 14 points:",
    atr14.filter(
      (value) =>
        value !== null
    ).length
  );

  console.log(
    "ROC 12 points:",
    roc12.filter(
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

  const bollingerUpperTrace = {
    x: dates,

    y: bollinger.upperBand,

    type: "scatter",

    mode: "lines",

    name: "BB Upper",

    line: {
      width: 1.2,

      color: "#6b7280",

      dash: "dot",
    },

    connectgaps: false,

    hovertemplate:
      "<b>%{x}</b><br>" +
      "BB Upper: $%{y:.2f}" +
      "<extra></extra>",
  };

  const bollingerMiddleTrace = {
    x: dates,

    y: bollinger.middleBand,

    type: "scatter",

    mode: "lines",

    name: "BB Middle",

    line: {
      width: 1.2,

      color: "#111827",
    },

    connectgaps: false,

    hovertemplate:
      "<b>%{x}</b><br>" +
      "BB Middle: $%{y:.2f}" +
      "<extra></extra>",
  };

  const bollingerLowerTrace = {
    x: dates,

    y: bollinger.lowerBand,

    type: "scatter",

    mode: "lines",

    name: "BB Lower",

    line: {
      width: 1.2,

      color: "#6b7280",

      dash: "dot",
    },

    connectgaps: false,

    hovertemplate:
      "<b>%{x}</b><br>" +
      "BB Lower: $%{y:.2f}" +
      "<extra></extra>",
  };

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

  const stochasticKTrace = {
    x: dates,

    y: stochastic.percentK,

    type: "scatter",

    mode: "lines",

    name: "%K",

    line: {
      width: 2,

      color: "#2563eb",
    },

    connectgaps: false,

    hovertemplate:
      "<b>%{x}</b><br>" +
      "%K: %{y:.2f}" +
      "<extra></extra>",
  };

  const stochasticDTrace = {
    x: dates,

    y: stochastic.percentD,

    type: "scatter",

    mode: "lines",

    name: "%D",

    line: {
      width: 2,

      color: "#f59e0b",
    },

    connectgaps: false,

    hovertemplate:
      "<b>%{x}</b><br>" +
      "%D: %{y:.2f}" +
      "<extra></extra>",
  };

  const stochasticLayout = {
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
      title: "Stochastic",

      range: [0, 100],

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

    shapes: [
      {
        type: "line",

        xref: "paper",

        x0: 0,

        x1: 1,

        y0: 80,

        y1: 80,

        line: {
          width: 1,

          dash: "dash",

          color: "#dc2626",
        },
      },

      {
        type: "line",

        xref: "paper",

        x0: 0,

        x1: 1,

        y0: 20,

        y1: 20,

        line: {
          width: 1,

          dash: "dash",

          color: "#16a34a",
        },
      },
    ],
  };

  const atrTrace = {
    x: dates,

    y: atr14,

    type: "scatter",

    mode: "lines",

    name: "ATR 14",

    line: {
      width: 2,

      color: "#7c3aed",
    },

    connectgaps: false,

    hovertemplate:
      "<b>%{x}</b><br>" +
      "ATR 14: %{y:.2f}" +
      "<extra></extra>",
  };

  const atrLayout = {
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
      title: "ATR",

      showgrid: true,

      fixedrange: false,

      tickprefix: "$",
    },

    hovermode:
      "x unified",

    showlegend: false,
  };

  const rocTrace = {
    x: dates,

    y: roc12,

    type: "scatter",

    mode: "lines",

    name: "ROC 12",

    line: {
      width: 2,

      color: "#0891b2",
    },

    connectgaps: false,

    hovertemplate:
      "<b>%{x}</b><br>" +
      "ROC 12: %{y:.2f}%" +
      "<extra></extra>",
  };

  const rocLayout = {
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
      title: "ROC (%)",

      showgrid: true,

      fixedrange: false,

      ticksuffix: "%",
    },

    hovermode:
      "x unified",

    showlegend: false,

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
    await Plotly.react(
      priceChartElement.value,

      [
        candlestickTrace,

        bollingerLowerTrace,

        bollingerUpperTrace,

        bollingerMiddleTrace,

        sma20Trace,

        sma50Trace,

        sma200Trace,
      ],

      priceLayout,

      chartConfig
    );

    await Plotly.react(
      volumeChartElement.value,

      [volumeTrace],

      volumeLayout,

      chartConfig
    );

    await Plotly.react(
      rsiChartElement.value,

      [rsiTrace],

      rsiLayout,

      chartConfig
    );

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

    await Plotly.react(
      stochasticChartElement.value,

      [
        stochasticKTrace,

        stochasticDTrace,
      ],

      stochasticLayout,

      chartConfig
    );

    await Plotly.react(
      atrChartElement.value,

      [atrTrace],

      atrLayout,

      chartConfig
    );

    await Plotly.react(
      rocChartElement.value,

      [rocTrace],

      rocLayout,

      chartConfig
    );

    console.log(
      "Candlestick, SMA, Bollinger Bands, volume, RSI, MACD, Stochastic, ATR and ROC charts rendered successfully."
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

watch(
  selectedPeriod,
  () => {
    loadPrices();
  }
);

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
  if (
    priceChartElement.value
  ) {
    Plotly.purge(
      priceChartElement.value
    );
  }

  if (
    volumeChartElement.value
  ) {
    Plotly.purge(
      volumeChartElement.value
    );
  }

  if (
    rsiChartElement.value
  ) {
    Plotly.purge(
      rsiChartElement.value
    );
  }

  if (
    macdChartElement.value
  ) {
    Plotly.purge(
      macdChartElement.value
    );
  }

  if (
    stochasticChartElement.value
  ) {
    Plotly.purge(
      stochasticChartElement.value
    );
  }

  if (
    atrChartElement.value
  ) {
    Plotly.purge(
      atrChartElement.value
    );
  }

  if (
    rocChartElement.value
  ) {
    Plotly.purge(
      rocChartElement.value
    );
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

.rsi-chart {
  width: 100%;

  height: 260px;
}

.macd-chart {
  width: 100%;

  height: 280px;
}

.stochastic-chart {
  width: 100%;

  height: 280px;
}

.atr-chart {
  width: 100%;

  height: 280px;
}

.roc-chart {
  width: 100%;

  height: 280px;
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

  .rsi-chart {
    height: 220px;
  }

  .macd-chart {
    height: 240px;
  }

  .stochastic-chart {
    height: 240px;
  }

  .atr-chart {
    height: 240px;
  }

  .roc-chart {
    height: 240px;
  }
}
</style>