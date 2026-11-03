import { getCurrentUser, logoutUser } from "../services/api";
import {
  clearLogoutPending, clearSessionExpiry, logoutPending, markLogoutPending,
} from "./sessionSafety.js";

// The browser must not treat a redirect as proof of server-side logout.
// Only a successful logout POST followed by an unauthenticated /me
// response may unlock ordinary guest navigation. Pending flags survive
// reload and synchronize between tabs without storing sensitive tokens.
async function serverReportsAnonymous() {
  try {
    await getCurrentUser();
    return false;
  } catch (err) {
    return err?.response?.status === 401 || err?.response?.status === 403;
  }
}

export async function confirmServerLogout() {
  markLogoutPending();
  try {
    await logoutUser();
  } catch {
    // This may already be an expired session. Confirm with the server.
    if (!(await serverReportsAnonymous())) return false;
  }
  if (!(await serverReportsAnonymous())) return false;
  clearSessionExpiry();
  clearLogoutPending();
  return true;
}

export async function resolvePendingLogout() {
  if (!logoutPending()) return true;
  return confirmServerLogout();
}
