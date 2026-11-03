/**
 * Small, dependency-free helpers shared by the research-health UI and tests.
 * No provider calls and no filesystem or database access.
 */
export function parseResearchSymbols(raw) {
  const query = String(raw ?? "").trim().toUpperCase();
  if (!query) return "";
  const tokens = query.split(",").map((symbol) => symbol.trim());
  if (tokens.length > 20 || tokens.some((symbol) => !/^[A-Z0-9.^=-]{1,20}$/.test(symbol))) {
    throw new Error("Enter 1–20 valid comma-separated stock symbols.");
  }
  return [...new Set(tokens)].join(",");
}

export function formatReadinessDate(value) {
  if (!value) return "Unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Unavailable" : date.toLocaleString();
}

export function sessionContextLabel(context) {
  if (context?.regular_session_state === "regular_hours") return "Regular hours (approx.)";
  if (context?.regular_session_state === "outside_regular_hours") return "Outside regular hours";
  return "Unknown";
}

export const readinessFlagLabels = Object.freeze({
  insufficient_history: "Insufficient price history",
  missing_price_history: "Missing price history",
  stale_price_history: "Old historical prices",
  future_price_date: "Future-dated price",
  invalid_ohlc_rows: "Invalid OHLC data",
  missing_quote: "No stored quote",
  stale_quote: "Old quote source",
  invalid_quote_timestamp: "Invalid quote timestamp",
  annual_fundamentals_unavailable: "Annual statements",
  quarterly_fundamentals_unavailable: "Quarterly statements",
  news_articles_unavailable: "News articles",
  news_publication_dates_unavailable: "News publication dates",
});

export function readableReadinessFlag(flag) {
  const value = String(flag ?? "");
  return readinessFlagLabels[value] || value.replaceAll("_", " ");
}
