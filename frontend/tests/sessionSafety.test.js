import { test } from "node:test";
import assert from "node:assert/strict";

import {
  PENDING_LOGOUT_KEY, SESSION_EXPIRY_KEY, markLogoutPending,
  clearLogoutPending, logoutPending, recordSessionExpiry,
  savedSessionExpiry, clearSessionExpiry, sessionIsPastDeadline,
} from "../src/utils/sessionSafety.js";

function fakeWindow() {
  const map = new Map();
  return {
    localStorage: {
      getItem: key => map.has(key) ? map.get(key) : null,
      setItem: (key, value) => map.set(key, String(value)),
      removeItem: key => map.delete(key),
    },
  };
}

test("failed signout state is stored and survives a simulated reload", () => {
  globalThis.window = fakeWindow();
  try {
    assert.equal(logoutPending(), false);
    markLogoutPending();
    assert.equal(logoutPending(), true);
    assert.equal(window.localStorage.getItem(PENDING_LOGOUT_KEY), "1");
    clearLogoutPending();
    assert.equal(logoutPending(), false);
  } finally {
    delete globalThis.window;
  }
});

test("marking a pending logout clears stale session deadline", () => {
  globalThis.window = fakeWindow();
  try {
    recordSessionExpiry("2026-11-04T12:00:00+00:00");
    assert.ok(savedSessionExpiry());
    markLogoutPending();
    assert.equal(savedSessionExpiry(), null);
    assert.equal(window.localStorage.getItem(SESSION_EXPIRY_KEY), null);
  } finally {
    delete globalThis.window;
  }
});

test("only parseable server expiry can authorize a session", () => {
  globalThis.window = fakeWindow();
  try {
    assert.equal(recordSessionExpiry("invalid"), null);
    assert.equal(savedSessionExpiry(), null);
    assert.equal(sessionIsPastDeadline("invalid"), true);
    assert.equal(sessionIsPastDeadline("2026-11-04T12:00:00Z", Date.parse("2026-11-04T12:00:00Z")), true);
    assert.equal(sessionIsPastDeadline("2026-11-04T12:00:00Z", Date.parse("2026-11-04T11:00:00Z")), false);
    clearSessionExpiry();
    assert.equal(savedSessionExpiry(), null);
  } finally {
    delete globalThis.window;
  }
});

test("unavailable browser storage does not raise uncaught exceptions", () => {
  globalThis.window = Object.defineProperty({}, "localStorage", {
    get: () => { throw new Error("Storage denied"); },
  });
  try {
    assert.doesNotThrow(markLogoutPending);
    assert.equal(logoutPending(), false);
  } finally {
    delete globalThis.window;
  }
});
