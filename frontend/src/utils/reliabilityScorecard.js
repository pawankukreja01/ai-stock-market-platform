const MODELS = {
  random_forest: "Random Forest",
  conservative_forest: "Conservative Forest",
  zero_anchor_ridge: "Zero-anchor Ridge",
  xgboost: "XGBoost",
};
const BASELINES = {
  zero_return: "Zero-return forecast",
  historical_mean: "Historical mean forecast",
  momentum: "Momentum forecast",
};
export const modelLabel = key => MODELS[key] || key;
export const baselineLabel = key => BASELINES[key] || key;
export const percent = value => Number.isFinite(value) ? `${value.toFixed(2)}%` : "Not measured";
export const delta = value => Number.isFinite(value)
  ? `${value > 0 ? "+" : ""}${value.toFixed(3)} pp`
  : "Not measured";
