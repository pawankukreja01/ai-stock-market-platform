import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json",
  },
});

// STOCKS
export const getStocks = async () => {
  const response = await api.get("/stocks/");
  return response.data;
};

// HISTORICAL PRICES
export const getHistoricalPrices = async (stockId, startDate, endDate) => {
  const response = await api.get("/historical-prices/", {
    params: {
      stock: stockId,
      start_date: startDate,
      end_date: endDate,
    },
  });
  return response.data;
};

// BENCHMARK COMPARISON
export const getBenchmarkComparison = async (startDate, endDate, sector = "") => {
  const response = await api.get("/benchmark-comparison/", {
    params: { start_date: startDate, end_date: endDate, sector },
  });
  return response.data;
};

// FUNDAMENTALS
export const getFundamentals = async (symbol, periodType = "") => {
  const response = await api.get("/fundamentals/", {
    params: { symbol, period_type: periodType },
  });
  return response.data;
};

// ML RETURN PREDICTION
export const getMLReturnPrediction = async (
  symbol,
  horizon = 5,
  model = "random_forest",
  confidence = 0.9
) => {
  const response = await api.get("/ml-prediction/", {
    params: { symbol, horizon, model, confidence },
  });
  return response.data;
};

// RISK METRICS
export const getRiskMetrics = async (symbol, startDate = "", endDate = "") => {
  const response = await api.get("/risk-metrics/", {
    params: { symbol, start_date: startDate, end_date: endDate },
  });
  return response.data;
};

// BACKTESTING
export const getBacktestResults = async (
  symbol,
  horizon = 5,
  model = "random_forest",
  transactionCostBps = 5,
  slippageBps = 5,
  threshold = 0
) => {
  const response = await api.get("/backtest/", {
    params: {
      symbol,
      horizon,
      model,
      transaction_cost_bps: transactionCostBps,
      slippage_bps: slippageBps,
      threshold,
    },
  });
  return response.data;
};

// NEWS SENTIMENT SUMMARY
export const getStockSentiment = async (symbol, limit = 50) => {
  const response = await api.get("/sentiment/", {
    params: { symbol, limit },
  });
  return response.data;
};

// STOCK SCREENER
export const getStockScreener = async (params = {}) => {
  const response = await api.get("/screener/", { params });
  return response.data;
};

// ============================================================
// PORTFOLIO MANAGEMENT
// ============================================================

export const getPortfolios = async () => {
  const response = await api.get("/portfolios/");
  return response.data;
};

export const createPortfolio = async (payload) => {
  const response = await api.post("/portfolios/", payload);
  return response.data;
};

export const getPortfolio = async (portfolioId) => {
  const response = await api.get(`/portfolios/${portfolioId}/`);
  return response.data;
};

export const updatePortfolio = async (portfolioId, payload) => {
  const response = await api.patch(
    `/portfolios/${portfolioId}/`,
    payload
  );
  return response.data;
};

export const deletePortfolio = async (portfolioId) => {
  const response = await api.delete(`/portfolios/${portfolioId}/`);
  return response.data;
};

export const getPortfolioHoldings = async (portfolioId) => {
  const response = await api.get(
    `/portfolios/${portfolioId}/holdings/`
  );
  return response.data;
};

export const createPortfolioHolding = async (
  portfolioId,
  payload
) => {
  const response = await api.post(
    `/portfolios/${portfolioId}/holdings/`,
    payload
  );
  return response.data;
};

export const updatePortfolioHolding = async (
  portfolioId,
  holdingId,
  payload
) => {
  const response = await api.patch(
    `/portfolios/${portfolioId}/holdings/${holdingId}/`,
    payload
  );
  return response.data;
};

export const deletePortfolioHolding = async (
  portfolioId,
  holdingId
) => {
  const response = await api.delete(
    `/portfolios/${portfolioId}/holdings/${holdingId}/`
  );
  return response.data;
};

export const getPortfolioAnalysis = async (portfolioId) => {
  const response = await api.get(
    `/portfolios/${portfolioId}/analysis/`
  );
  return response.data;
};

// ============================================================
// INVESTMENT SIMULATOR
// ============================================================

export const getInvestmentSimulation = async (params = {}) => {
  const response = await api.get("/investment-simulator/", { params });
  return response.data;
};

// ============================================================
// ALERTS
// ============================================================

export const getAlertRules = async (params = {}) => {
  const response = await api.get("/alerts/", { params });
  return response.data;
};

export const createAlertRule = async (payload) => {
  const response = await api.post("/alerts/", payload);
  return response.data;
};

export const updateAlertRule = async (ruleId, payload) => {
  const response = await api.patch(`/alerts/${ruleId}/`, payload);
  return response.data;
};

export const deleteAlertRule = async (ruleId) => {
  const response = await api.delete(`/alerts/${ruleId}/`);
  return response.data;
};

export const getAlertEvents = async (params = {}) => {
  const response = await api.get("/alerts/events/", { params });
  return response.data;
};

export const markAlertEventRead = async (eventId, isRead = true) => {
  const response = await api.post(`/alerts/events/${eventId}/read/`, {
    is_read: isRead,
  });
  return response.data;
};