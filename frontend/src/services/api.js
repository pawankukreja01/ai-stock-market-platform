import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});


// STOCKS
export const getStocks = async () => {
  const response = await api.get("/stocks/");
  return response.data;
};


export const getStockCatalog = async ({
  search = "",
  market = "",
  exchange = "",
  sector = "",
  page = 1,
  pageSize = 24,
} = {}) => {
  const params = {
    page,
    page_size: pageSize,
  };

  if (search.trim()) params.search = search.trim();
  if (market) params.market = market;
  if (exchange) params.exchange = exchange;
  if (sector.trim()) params.sector = sector.trim();

  const response = await api.get("/stocks/", { params });
  return response.data;
};

export const getPopularStocks = async ({
  market = "",
  pageSize = 100,
} = {}) => {
  const params = {
    page: 1,
    page_size: pageSize,
  };

  if (market) params.market = market;

  const response = await api.get("/stocks/popular/", { params });
  return response.data;
};

// ============================================================
// LATEST STOCK QUOTES
// ============================================================

export const getLatestQuote = async (symbol) => {
  const normalizedSymbol = String(symbol ?? "").trim();

  if (!normalizedSymbol) {
    throw new Error("A stock symbol is required.");
  }

  const response = await api.get(
    `/quotes/${encodeURIComponent(normalizedSymbol)}/`
  );

  return response.data;
};

// Authenticated, stored-data-only research readiness report.
export const getResearchReadiness = async (symbols = "") => {
  const response = await api.get("/research-readiness/", {
    params: symbols ? { symbols } : {},
  });
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
export const getBenchmarkComparison = async (startDate, endDate, sector = "", exchange = "") => {
  const response = await api.get("/benchmark-comparison/", {
    params: { start_date: startDate, end_date: endDate, sector, exchange },
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


/* ============================================================
   AUTHENTICATION
   ============================================================ */

let csrfTokenPromise = null;

const getCookie = (name) => {
  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${name}=`));

  return cookie ? decodeURIComponent(cookie.split("=").slice(1).join("=")) : null;
};

export const getCsrfToken = async () => {
  const existingToken = getCookie("csrftoken");

  if (existingToken) {
    return existingToken;
  }

  if (!csrfTokenPromise) {
    csrfTokenPromise = api
      .get("/auth/csrf/")
      .then((response) => response.data.csrfToken)
      .finally(() => {
        csrfTokenPromise = null;
      });
  }

  return csrfTokenPromise;
};

// Django session authentication requires CSRF protection for every write,
// not just login and profile updates. GET requests (including the token
// bootstrap endpoint) are deliberately excluded to avoid recursion.
const csrfProtectedMethods = new Set(["post", "put", "patch", "delete"]);

api.interceptors.request.use(async (config) => {
  if (csrfProtectedMethods.has(String(config.method || "get").toLowerCase())) {
    const token = await getCsrfToken();
    config.headers.set("X-CSRFToken", token);
  }

  return config;
});

const authPost = async (url, payload = {}) => {
  const csrfToken = await getCsrfToken();

  const response = await api.post(url, payload, {
    headers: {
      "X-CSRFToken": csrfToken,
    },
  });

  return response.data;
};

export const registerUser = async ({
  name,
  email,
  password,
  password_confirm,
}) => {
  return authPost("/auth/register/", {
    name,
    email,
    password,
    password_confirm,
  });
};

export const loginUser = async ({ email, password }) => {
  return authPost("/auth/login/", {
    email,
    password,
  });
};



export const verifyEmail = async (token) => {
  return authPost("/auth/verify-email/", { token });
};

export const resendVerificationEmail = async (email) => {
  return authPost("/auth/resend-verification/", { email });
};

export const requestPasswordReset = async (email) => {
  return authPost("/auth/password-reset/", { email });
};

export const confirmPasswordReset = async ({
  uid,
  token,
  password,
  password_confirm,
}) => {
  return authPost("/auth/password-reset/confirm/", {
    uid,
    token,
    password,
    password_confirm,
  });
};

export const getCurrentUser = async () => {
  const response = await api.get("/auth/me/");
  return response.data;
};



export const updateProfile = async (payload) => {
  const csrfToken = await getCsrfToken();

  const response = await api.patch(
    "/auth/profile/",
    payload,
    {
      headers: {
        "X-CSRFToken": csrfToken,
      },
      withCredentials: true,
    }
  );

  return response.data;
};

export const uploadProfilePicture = async (file) => {
  const csrfToken = await getCsrfToken();
  const formData = new FormData();

  formData.append("profile_picture", file);

  const response = await api.post(
    "/auth/profile/picture/",
    formData,
    {
      headers: {
        "X-CSRFToken": csrfToken,
        "Content-Type": undefined,
      },
      withCredentials: true,
    }
  );

  return response.data;
};



export const logoutUser = async () => {
  return authPost("/auth/logout/");
};


/**
 * STOCK RECOMMENDATIONS
 */


export const getStockRecommendations = async ({
  budget,
  currency = "USD",
  risk_tolerance = "moderate",
  horizon_months = 12,
  market = "",
  max_candidates = 10,
} = {}) => {
  const params = {
    budget,
    currency,
    risk_tolerance,
    horizon_months,
    max_candidates,
  };

  if (market) params.market = market;

  const response = await api.get("/recommendations/", { params });
  return response.data;
};
