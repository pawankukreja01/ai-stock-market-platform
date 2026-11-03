// Session flags contain no credentials or personal information.
// A pending logout keeps protected routes blocked if the sign-out request
// fails due to a network error. The Django session remains authoritative.
export const PENDING_LOGOUT_KEY = "marketpulse.pending-signout";
export const SESSION_EXPIRY_KEY = "marketpulse.session-expiry";

function storage() {
  try { return typeof window === "undefined" ? null : window.localStorage; }
  catch { return null; }
}

export function logoutPending() {
  return storage()?.getItem(PENDING_LOGOUT_KEY) === "1";
}

export function markLogoutPending() {
  storage()?.setItem(PENDING_LOGOUT_KEY, "1");
  storage()?.removeItem(SESSION_EXPIRY_KEY);
}

export function clearLogoutPending() {
  storage()?.removeItem(PENDING_LOGOUT_KEY);
}

export function recordSessionExpiry(isoDate) {
  const millis = Date.parse(isoDate);
  if (!Number.isFinite(millis)) return null;
  storage()?.setItem(SESSION_EXPIRY_KEY, String(millis));
  return millis;
}

export function savedSessionExpiry() {
  const raw = storage()?.getItem(SESSION_EXPIRY_KEY);
  if (!raw) return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

export function clearSessionExpiry() {
  storage()?.removeItem(SESSION_EXPIRY_KEY);
}

export function sessionIsPastDeadline(isoDate, atMillis = Date.now()) {
  const deadline = Date.parse(isoDate);
  return !Number.isFinite(deadline) || deadline <= atMillis;
}
