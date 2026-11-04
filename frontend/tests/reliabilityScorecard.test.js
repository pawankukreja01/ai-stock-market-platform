import test from "node:test";
import assert from "node:assert/strict";
import { modelLabel, baselineLabel, percent, delta } from "../src/utils/reliabilityScorecard.js";

test("model and baseline names remain understandable", () => {
  assert.equal(modelLabel("zero_anchor_ridge"), "Zero-anchor Ridge");
  assert.equal(baselineLabel("zero_return"), "Zero-return forecast");
});
test("missing uncertainty never appears as 0% accuracy", () => {
  assert.equal(percent(null), "Not measured");
  assert.equal(percent(undefined), "Not measured");
  assert.equal(percent(Number.NaN), "Not measured");
  assert.equal(delta(null), "Not measured");
});
test("baseline deltas distinguish improvements from losses", () => {
  assert.equal(delta(0.03104), "+0.031 pp");
  assert.equal(delta(-0.39512), "-0.395 pp");
  assert.equal(percent(54.0765), "54.08%");
});
