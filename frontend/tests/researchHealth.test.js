import { test } from "node:test";
import assert from "node:assert/strict";

import {
  parseResearchSymbols,
  formatReadinessDate,
  sessionContextLabel,
  readableReadinessFlag,
} from "../src/utils/researchHealth.js";

test("empty stock selection means use the default catalogue", () => {
  assert.equal(parseResearchSymbols("   "), "");
});

test("symbols are normalized and duplicated symbols removed", () => {
  assert.equal(parseResearchSymbols("aapl, abf.l , AAPL"), "AAPL,ABF.L");
});

test("bad or excess symbols fail locally before requesting the API", () => {
  for (const bad of ["AAPL,,NVDA", "../etc/passwd", "AAPL;DROP", "ABC!".repeat(7), Array.from({length:21}, (_,i) => "T"+i).join(",")]) {
    assert.throws(() => parseResearchSymbols(bad));
  }
});

test("readiness flags describe data availability, not investment recommendations", () => {
  assert.equal(readableReadinessFlag("quarterly_fundamentals_unavailable"), "Quarterly statements");
  assert.equal(readableReadinessFlag("stale_quote"), "Old quote source");
});

test("unknown or invalid provider timestamp is not displayed as live", () => {
  assert.equal(formatReadinessDate(null), "Unavailable");
  assert.equal(formatReadinessDate("invalid"), "Unavailable");
});

test("session label never asserts exchange is actually open", () => {
  assert.equal(sessionContextLabel({regular_session_state:"regular_hours"}), "Regular hours (approx.)");
  assert.equal(sessionContextLabel({regular_session_state:"outside_regular_hours"}), "Outside regular hours");
  assert.equal(sessionContextLabel({}), "Unknown");
});
