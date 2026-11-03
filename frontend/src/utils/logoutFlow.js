import { getCurrentUser, logoutUser } from "../services/api.js";
import {
  clearLogoutPending, clearSessionExpiry, logoutPending, markLogoutPending,
} from "./sessionSafety.js";

// A redirect is not proof of logout. Only a server-confirmed anonymous
// response can release the persistent signout lock.
async function serverReportsAnonymous(currentUser) {
  try {
    await currentUser();
    return false;
  } catch (error) {
    return error?.response?.status === 401 || error?.response?.status === 403;
  }
}

export async function confirmServerLogout({
  logout = logoutUser,
  currentUser = getCurrentUser,
} = {}) {
  markLogoutPending();
  try {
    await logout();
  } catch {
    // The session might already have timed out. Check authoritatively.
    if (!(await serverReportsAnonymous(currentUser))) return false;
  }
  if (!(await serverReportsAnonymous(currentUser))) return false;
  clearSessionExpiry();
  clearLogoutPending();
  return true;
}

export async function resolvePendingLogout(dependencies = {}) {
  if (!logoutPending()) return true;
  return confirmServerLogout(dependencies);
}
