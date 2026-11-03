// These flags contain no credentials or personal information.
// A pending sign-out prevents private route restoration after a failed API
// call. Local storage synchronizes tabs; session storage is a fallback.
export const PENDING_LOGOUT_KEY = "marketpulse.pending-signout";
export const SESSION_EXPIRY_KEY = "marketpulse.session-expiry";

function stores() {
  if (typeof window === "undefined") return [];
  const available = [];
  for (const name of ["localStorage", "sessionStorage"]) {
    try {
      const value = window[name];
      if (value) available.push(value);
    } catch {
      // Private browsing can forbid even reading browser storage.
    }
  }
  return available;
}

function read(key) {
  for (const store of stores()) {
    try {
      const value = store.getItem(key);
      if (value !== null) return value;
    } catch {
      // Try the next permitted storage mechanism.
    }
  }
  return null;
}

function write(key, value) {
  for (const store of stores()) {
    try {
      store.setItem(key, value);
      return true;
    } catch {
      // Quota errors/private browsing can reject writes.
    }
  }
  return false;
}

function remove(key) {
  for (const store of stores()) {
    try { store.removeItem(key); }
    catch { /* Denied storage must not crash logout. */ }
  }
}

export function logoutPending() {
  return read(PENDING_LOGOUT_KEY) === "1";
}

export function markLogoutPending() {
  write(PENDING_LOGOUT_KEY, "1");
  remove(SESSION_EXPIRY_KEY);
}

export function clearLogoutPending() {
  remove(PENDING_LOGOUT_KEY);
}

export function recordSessionExpiry(isoDate) {
  const millis = Date.parse(isoDate);
  if (!Number.isFinite(millis)) return null;
  write(SESSION_EXPIRY_KEY, String(millis));
  return millis;
}

export function savedSessionExpiry() {
  const raw = read(SESSION_EXPIRY_KEY);
  if (!raw) return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

export function clearSessionExpiry() {
  remove(SESSION_EXPIRY_KEY);
}

export function sessionIsPastDeadline(isoDate, atMillis = Date.now()) {
  const deadline = Date.parse(isoDate);
  return !Number.isFinite(deadline) || deadline <= atMillis;
}
