import { test } from "node:test";
import assert from "node:assert/strict";

import { confirmServerLogout, resolvePendingLogout } from "../src/utils/logoutFlow.js";
import {
  clearLogoutPending, logoutPending, markLogoutPending,
} from "../src/utils/sessionSafety.js";

function setFakeStorage() {
  const map = new Map();
  globalThis.window = {
    localStorage: {
      getItem: (k) => map.has(k) ? map.get(k) : null,
      setItem: (k, v) => map.set(k, String(v)),
      removeItem: (k) => map.delete(k),
    },
  };
  return map;
}

function denied() {
  return Object.assign(new Error("Authentication required"), {
    response: { status: 403 },
  });
}

test("successful logout and anonymous response unlocks routes", async () => {
  setFakeStorage();
  try {
    let called = 0;
    const result = await confirmServerLogout({
      logout: async () => { called++; },
      currentUser: async () => { throw denied(); },
    });
    assert.equal(result, true);
    assert.equal(called, 1);
    assert.equal(logoutPending(), false);
  } finally {
    delete globalThis.window;
  }
});

test("failed logout with still-authenticated cookie remains locked", async () => {
  setFakeStorage();
  try {
    const result = await confirmServerLogout({
      logout: async () => { throw new Error("CSRF rejected"); },
      currentUser: async () => ({ user: { id: 1 } }),
    });
    assert.equal(result, false);
    assert.equal(logoutPending(), true);
  } finally {
    delete globalThis.window;
  }
});

test("server outage during confirmation must not claim success", async () => {
  setFakeStorage();
  try {
    const result = await confirmServerLogout({
      logout: async () => {},
      currentUser: async () => { throw new Error("Network unavailable"); },
    });
    assert.equal(result, false);
    assert.equal(logoutPending(), true);
  } finally {
    delete globalThis.window;
  }
});

test("an already-expired session is safely recognized as logged out", async () => {
  setFakeStorage();
  try {
    const result = await confirmServerLogout({
      logout: async () => { throw new Error("Logout failed"); },
      currentUser: async () => { throw denied(); },
    });
    assert.equal(result, true);
    assert.equal(logoutPending(), false);
  } finally {
    delete globalThis.window;
  }
});

test("pending signout prevents restoration unless server verifies it", async () => {
  setFakeStorage();
  try {
    markLogoutPending();
    const locked = await resolvePendingLogout({
      logout: async () => { throw new Error("Network unavailable"); },
      currentUser: async () => ({ user: { id: 1 } }),
    });
    assert.equal(locked, false);
    assert.equal(logoutPending(), true);

    const unlocked = await resolvePendingLogout({
      logout: async () => {},
      currentUser: async () => { throw denied(); },
    });
    assert.equal(unlocked, true);
    assert.equal(logoutPending(), false);
    clearLogoutPending();
  } finally {
    delete globalThis.window;
  }
});
