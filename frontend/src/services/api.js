import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json",
  },
});


// ============================================================
// STOCKS
// ============================================================

export const getStocks = async () => {
  const response = await api.get("/stocks/");

  return response.data;
};


// ============================================================
// HISTORICAL PRICES
// ============================================================

export const getHistoricalPrices = async (
  stockId,
  startDate,
  endDate
) => {
  const response = await api.get(
    "/historical-prices/",
    {
      params: {
        stock: stockId,
        start_date: startDate,
        end_date: endDate,
      },
    }
  );

  return response.data;
};


// ============================================================
// BENCHMARK COMPARISON
// ============================================================

export const getBenchmarkComparison = async (
  startDate,
  endDate,
  sector = ""
) => {
  const response = await api.get(
    "/benchmark-comparison/",
    {
      params: {
        start_date: startDate,
        end_date: endDate,
        sector,
      },
    }
  );

  return response.data;
};

export const getFundamentals = async (
  symbol,
  periodType = ""
) => {
  const response = await api.get("/fundamentals/", {
    params: {
      symbol,
      period_type: periodType,
    },
  });

  return response.data;
};

export const getRiskMetrics = async (
  symbol,
  startDate = "",
  endDate = ""
) => {
  const response = await api.get("/risk-metrics/", {
    params: {
      symbol,
      start_date: startDate,
      end_date: endDate,
    },
  });

  return response.data;
};

export default api;