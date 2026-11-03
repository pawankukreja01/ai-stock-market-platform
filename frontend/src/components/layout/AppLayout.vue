<template>
  <div class="app-layout">
    <aside class="sidebar">
      <router-link
        to="/"
        class="brand brand-link"
        aria-label="MarketPulse home"
      >
        <span class="brand-mark" aria-hidden="true">M</span>
        <span class="brand-copy">
          <strong>MarketPulse</strong>
          <small>AI market intelligence</small>
        </span>
      </router-link>

      <p class="navigation-label">WORKSPACE</p>
      <nav class="navigation" aria-label="Main navigation">
        <router-link
          to="/"
          exact-active-class="router-link-exact-active"
        >
          Dashboard
        </router-link>

        <router-link
          to="/profile"
          exact-active-class="router-link-exact-active"
        >
          My Profile
        </router-link>

        <router-link
          to="/recommendations"
          exact-active-class="router-link-exact-active"
        >
          Recommendations
        </router-link>

        <router-link
          to="/discover"
          exact-active-class="router-link-exact-active"
        >
          Discover Stocks
        </router-link>

        <router-link
          to="/portfolio"
          exact-active-class="router-link-exact-active"
        >
          Portfolio
        </router-link>

        <router-link
          to="/research-health"
          exact-active-class="router-link-exact-active"
        >
          Research Health
        </router-link>

        <router-link
          to="/screener"
          exact-active-class="router-link-exact-active"
        >
          Stock Screener
        </router-link>

        <router-link
          to="/investment-simulator"
          exact-active-class="router-link-exact-active"
        >
          Investment Simulator
        </router-link>

        <router-link
          to="/alerts"
          class="alerts-nav-link"
          exact-active-class="router-link-exact-active"
        >
          <span>Alerts &amp; Notifications</span>

          <span
            v-if="unreadAlertCount > 0"
            class="unread-count"
            :aria-label="`${unreadAlertCount} unread alerts`"
          >
            {{ unreadAlertCount > 99 ? "99+" : unreadAlertCount }}
          </span>
        </router-link>
      </nav>

      <button
        class="logout-button"
        type="button"
        :disabled="logoutInProgress"
        @click="handleLogout"
      >
        <span aria-hidden="true">↪</span>
        Log out
      </button>
    </aside>

    <div class="main-area">
      <header class="topbar">
        <div class="topbar-heading">
          <p class="topbar-eyebrow">INVESTMENT RESEARCH WORKSPACE</p>
          <h1>Market Intelligence</h1>
        </div>

        <div class="topbar-right">
          <span class="market-context">
            <span class="market-context-dot" aria-hidden="true"></span>
            US &amp; UK Markets
          </span>
        </div>
      </header>

      <main class="content">
        <router-view />
      </main>
    </div>

    <div v-if="logoutInProgress" class="session-overlay" role="status" aria-live="polite">
      <section class="session-modal">
        <h2>Securing your session</h2>
        <p>Signing out and checking that your account is no longer accessible.</p>
      </section>
    </div>

    <!-- Inactivity warning modal -->
    <div
      v-if="showInactivityWarning"
      class="session-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="session-warning-title"
    >
      <section class="session-modal">
        <div class="session-icon" aria-hidden="true">
          ⏱
        </div>

        <h2 id="session-warning-title">
          Are you still there?
        </h2>

        <p>
          You've been inactive for a while. For your security,
          you'll be logged out soon.
        </p>

        <div class="countdown-container">
          <span>Automatic logout in</span>

          <strong class="countdown">
            {{ countdownMinutes }}:{{ countdownSeconds }}
          </strong>
        </div>

        <p v-if="sessionError" class="session-error">
          {{ sessionError }}
        </p>

        <button
          type="button"
          class="stay-button"
          :disabled="checkingSession || logoutInProgress"
          @click="handleStayLoggedIn"
        >
          {{
            checkingSession
              ? "Checking session..."
              : "Stay logged in"
          }}
        </button>

        <button
          type="button"
          class="session-logout-button"
          :disabled="logoutInProgress"
          @click="handleLogout"
        >
          Log out now
        </button>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from "vue";
import { useRouter } from "vue-router";
import { confirmSessionActivity, getAlertEvents, getCurrentUser } from "../../services/api";
import { confirmServerLogout } from "../../utils/logoutFlow.js";
import {
  logoutPending, markLogoutPending, recordSessionExpiry, savedSessionExpiry,
  sessionIsPastDeadline, PENDING_LOGOUT_KEY, SESSION_EXPIRY_KEY,
} from "../../utils/sessionSafety.js";

const router = useRouter();
const WARNING_SECONDS = 5 * 60;
const HEARTBEAT_MIN_GAP = 60 * 1000;
const unreadAlertCount = ref(0);
const showInactivityWarning = ref(false);
const checkingSession = ref(false);
const logoutInProgress = ref(false);
const sessionError = ref("");
const remainingSeconds = ref(0);
const countdownMinutes = computed(() => String(Math.floor(remainingSeconds.value / 60)).padStart(2, "0"));
const countdownSeconds = computed(() => String(remainingSeconds.value % 60).padStart(2, "0"));

let deadline = savedSessionExpiry();
let lastActivityCallAt = 0;
let lastUserInteractionAt = 0;
let heartbeatInFlight = false;
let closed = false;
let timerId = null;
let alertIntervalId = null;

function acceptDeadline(iso) {
  const newDeadline = recordSessionExpiry(iso);
  if (!newDeadline) return false;
  deadline = newDeadline;
  updateCountdown();
  return true;
}

function updateCountdown() {
  if (logoutInProgress.value || closed) return;
  // Don't treat tab reloading, visibility changes, page rendering, or
  // passive API responses as user activity.
  if (logoutPending()) {
    markLogoutPending();
    void router.replace("/login");
    return;
  }
  if (!deadline) {
    void forceLogout();
    return;
  }
  const seconds = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
  remainingSeconds.value = seconds;
  showInactivityWarning.value = seconds > 0 && seconds <= WARNING_SECONDS;
  if (seconds <= 0) void forceLogout();
}

async function forceLogout() {
  if (logoutInProgress.value) return;
  logoutInProgress.value = true;
  markLogoutPending(); // synchronous, persists if sign-out POST fails
  unreadAlertCount.value = 0;
  try {
    await confirmServerLogout();
  } finally {
    if (!closed) await router.replace("/login");
  }
}

async function handleLogout() {
  await forceLogout();
}

async function handleStayLoggedIn() {
  if (checkingSession.value || logoutInProgress.value) return;
  checkingSession.value = true;
  sessionError.value = "";
  try {
    const data = await confirmSessionActivity();
    if (!acceptDeadline(data?.session?.expires_at)) {
      throw new Error("No session expiration returned.");
    }
    lastActivityCallAt = Date.now();
  } catch {
    sessionError.value = "Your session could not be renewed. Please sign in again.";
    await forceLogout();
  } finally {
    checkingSession.value = false;
  }
}

function handleUserActivity() {
  if (logoutInProgress.value || checkingSession.value || heartbeatInFlight || closed) return;
  if (document.visibilityState === "hidden" || showInactivityWarning.value) return;
  const now = Date.now();
  if (now - lastUserInteractionAt < 1000) return;
  lastUserInteractionAt = now;
  if (!deadline || now >= deadline) {
    void forceLogout();
    return;
  }
  // A real pointer/key/scroll action is required before this POST.
  // Passive route checks, data refreshes and heartbeat timers never POST.
  if (now - lastActivityCallAt < HEARTBEAT_MIN_GAP) return;
  lastActivityCallAt = now;
  heartbeatInFlight = true;
  void (async () => {
    try {
      const data = await confirmSessionActivity();
      if (!acceptDeadline(data?.session?.expires_at)) {
        throw new Error("Missing expiry");
      }
    } catch {
      await forceLogout();
    } finally {
      heartbeatInFlight = false;
    }
  })();
}

async function refreshUnreadAlertCount() {
  if (logoutInProgress.value || document.visibilityState === "hidden") return;
  try {
    const result = await getAlertEvents({ unread: "true", limit: 1 });
    if (!logoutInProgress.value) {
      unreadAlertCount.value = Math.max(0, Number(result?.count ?? 0));
    }
  } catch {
    // Preserve last known count; this GET must not renew a session.
  }
}

function onStorage(event) {
  if (event.key === PENDING_LOGOUT_KEY && logoutPending()) {
    void router.replace("/login");
  }
  if (event.key === SESSION_EXPIRY_KEY) {
    const next = savedSessionExpiry();
    if (next) deadline = next;
    updateCountdown();
  }
}

function onVisible() {
  if (document.visibilityState === "visible") updateCountdown();
}

const activityEvents = ["pointerdown", "keydown", "touchstart", "scroll"];

onMounted(async () => {
  try {
    const result = await getCurrentUser();
    if (!result?.user || !result?.session?.expires_at ||
        sessionIsPastDeadline(result.session.expires_at)) {
      throw new Error("Session missing or expired");
    }
    if (!closed) acceptDeadline(result.session.expires_at);
  } catch {
    if (!closed) {
      await forceLogout();
      return;
    }
  }
  if (closed) return;
  for (const event of activityEvents) {
    window.addEventListener(event, handleUserActivity, { passive: true });
  }
  window.addEventListener("storage", onStorage);
  document.addEventListener("visibilitychange", onVisible);
  updateCountdown();
  timerId = window.setInterval(updateCountdown, 1000);
  void refreshUnreadAlertCount();
  alertIntervalId = window.setInterval(refreshUnreadAlertCount, 60_000);
});

onBeforeUnmount(() => {
  closed = true;
  if (timerId !== null) window.clearInterval(timerId);
  if (alertIntervalId !== null) window.clearInterval(alertIntervalId);
  for (const event of activityEvents) window.removeEventListener(event, handleUserActivity);
  window.removeEventListener("storage", onStorage);
  document.removeEventListener("visibilitychange", onVisible);
});
</script>

<style scoped>
.app-layout {
  min-height: 100vh;
  background: #f5f7fa;
}

.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 240px;
  height: 100vh;
  overflow-y: auto;
  background: #111827;
  color: white;
  padding: 24px 16px;
  box-sizing: border-box;
  z-index: 1000;
}

.brand {
  padding: 0 12px 30px;
}

.brand h2 {
  margin: 0;
  font-size: 22px;
}

.brand span {
  display: block;
  margin-top: 5px;
  font-size: 12px;
  color: #9ca3af;
}

.brand-link {
  display: block;
  color: white;
  text-decoration: none;
  border-radius: 8px;
}

.brand-link:hover h2 {
  color: #dbeafe;
}

.navigation {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.navigation a {
  display: block;
  padding: 11px 12px;
  border-radius: 8px;
  color: #d1d5db;
  text-decoration: none;
  font-size: 15px;
  transition: background 0.15s ease, color 0.15s ease;
}

.navigation a:hover,
.navigation a.router-link-exact-active {
  background: #1f2937;
  color: white;
}

.navigation a.alerts-nav-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.logout-button {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  margin-top: 24px;
  padding: 11px 12px;
  border: 1px solid #374151;
  border-radius: 8px;
  background: transparent;
  color: #fca5a5;
  font-size: 15px;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.logout-button:hover {
  background: #7f1d1d;
  color: white;
}

.logout-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.unread-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  border-radius: 999px;
  background: #dc2626;
  color: #fff;
  font-size: 11px;
  font-weight: 800;
  line-height: 1;
  flex-shrink: 0;
}

.main-area {
  margin-left: 240px;
  width: calc(100% - 240px);
  min-width: 0;
  min-height: 100vh;
}

.topbar {
  min-height: 70px;
  background: white;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 30px;
  box-sizing: border-box;
}

.topbar h1 {
  margin: 0;
  font-size: 20px;
}

.topbar-right {
  font-size: 14px;
  color: #6b7280;
}

.content {
  padding: 30px;
}

/* Inactivity warning modal */

.session-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(15, 23, 42, 0.65);
}

.session-modal {
  width: 100%;
  max-width: 420px;
  padding: 30px;
  border-radius: 16px;
  background: #ffffff;
  color: #172033;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
  text-align: center;
}

.session-icon {
  margin-bottom: 14px;
  font-size: 34px;
}

.session-modal h2 {
  margin: 0 0 12px;
  font-size: 23px;
}

.session-modal > p {
  color: #697386;
  line-height: 1.6;
  font-size: 14px;
}

.countdown-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 22px 0;
  color: #475569;
  font-size: 14px;
}

.countdown {
  color: #dc2626;
  font-size: 30px;
  font-variant-numeric: tabular-nums;
}

.stay-button,
.session-logout-button {
  width: 100%;
  padding: 12px;
  border-radius: 9px;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.stay-button {
  border: 0;
  background: #2563eb;
  color: white;
}

.session-logout-button {
  margin-top: 10px;
  border: 1px solid #d6dce7;
  background: white;
  color: #475569;
}

.stay-button:disabled,
.session-logout-button:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.session-error {
  color: #b42318 !important;
}

@media (max-width: 640px) {
  .sidebar {
    width: 170px;
    padding: 20px 10px;
  }

  .brand {
    padding: 0 8px 24px;
  }

  .main-area {
    margin-left: 170px;
    width: calc(100% - 170px);
  }

  .content {
    padding: 14px;
  }

  .topbar {
    padding: 16px;
  }

  .topbar h1 {
    font-size: 17px;
  }

  .navigation a {
    font-size: 13px;
  }

  .session-modal {
    padding: 24px 20px;
  }
}


/* --------------------------------------------------------------------------
   MarketPulse workspace layout refresh
   Navigation destinations, session handling and API behavior are unchanged.
---------------------------------------------------------------------------- */
.app-layout {
  min-height: 100vh;
  background: #f4f7fb;
}

.sidebar {
  display: flex;
  flex-direction: column;
  width: 258px;
  padding: 26px 17px 20px;
  border-right: 1px solid rgb(148 163 184 / 12%);
  background:
    radial-gradient(circle at 0% 0%, rgb(37 99 235 / 18%), transparent 34%),
    linear-gradient(180deg, #0c1728 0%, #101d30 54%, #0b1422 100%);
  box-shadow: 8px 0 28px rgb(15 23 42 / 6%);
}

.brand.brand-link {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 48px;
  padding: 0 8px 0;
  margin-bottom: 32px;
}

.brand-mark {
  display: inline-flex !important;
  flex: 0 0 42px;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  margin: 0 !important;
  border: 1px solid rgb(191 219 254 / 26%);
  border-radius: 13px;
  background: linear-gradient(145deg, #3b82f6, #1d4ed8 70%, #1e40af);
  box-shadow: 0 7px 18px rgb(37 99 235 / 28%);
  color: #fff;
  font-size: 20px;
  font-weight: 850;
  letter-spacing: -0.06em;
}

.brand-copy {
  display: flex !important;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  margin: 0 !important;
}

.brand-copy strong {
  color: #f8fafc;
  font-size: 17px;
  font-weight: 760;
  letter-spacing: -0.035em;
  line-height: 1.1;
}

.brand-copy small {
  color: #91a4bd;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.045em;
  line-height: 1.2;
}

.navigation-label {
  margin: 0 11px 11px;
  color: #71849e;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.15em;
}

.navigation {
  gap: 5px;
}

.navigation a {
  position: relative;
  display: flex;
  align-items: center;
  min-height: 43px;
  padding: 10px 12px;
  border: 1px solid transparent;
  border-radius: 10px;
  color: #b8c5d6;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.005em;
  transition: background 150ms ease, color 150ms ease, border-color 150ms ease, transform 150ms ease;
}

.navigation a:hover {
  transform: translateX(2px);
  border-color: rgb(148 163 184 / 12%);
  background: rgb(148 163 184 / 9%);
  color: #fff;
}

.navigation a.router-link-exact-active {
  border-color: rgb(96 165 250 / 20%);
  background: linear-gradient(90deg, rgb(37 99 235 / 28%), rgb(37 99 235 / 12%));
  color: #eff6ff;
  box-shadow: inset 3px 0 0 #60a5fa;
}

.navigation a.alerts-nav-link {
  display: flex;
}

.unread-count {
  border: 1px solid rgb(254 202 202 / 20%);
  box-shadow: 0 2px 8px rgb(220 38 38 / 18%);
}

.logout-button {
  min-height: 43px;
  margin-top: auto;
  padding: 10px 12px;
  border-color: rgb(248 113 113 / 18%);
  border-radius: 10px;
  color: #fca5a5;
  font-size: 13px;
  font-weight: 650;
}

.logout-button:hover {
  background: rgb(127 29 29 / 45%);
  border-color: rgb(248 113 113 / 30%);
}

.main-area {
  min-height: 100vh;
  margin-left: 258px;
  width: calc(100% - 258px);
  background: #f4f7fb;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 50;
  min-height: 78px;
  padding: 14px clamp(22px, 3vw, 42px);
  border-bottom-color: #e6ebf2;
  background: rgb(255 255 255 / 92%);
  box-shadow: 0 3px 14px rgb(15 23 42 / 3%);
  backdrop-filter: blur(14px);
}

.topbar-heading {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.topbar-eyebrow {
  margin: 0;
  color: #8a99ad;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.15em;
}

.topbar h1 {
  color: #17263b;
  font-size: 18px;
  font-weight: 750;
  letter-spacing: -0.025em;
}

.topbar-right {
  color: #64748b;
  font-size: 12px;
}

.market-context {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  padding: 8px 12px;
  border: 1px solid #e4eaf2;
  border-radius: 999px;
  background: #f8fafc;
  color: #475569;
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}

.market-context-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #3b82f6;
  box-shadow: 0 0 0 4px rgb(59 130 246 / 10%);
}

.content {
  width: 100%;
  max-width: 1700px;
  margin: 0 auto;
  padding: 30px clamp(20px, 3vw, 42px) 48px;
}

@media (max-width: 980px) and (min-width: 701px) {
  .sidebar {
    width: 220px;
    padding-right: 13px;
    padding-left: 13px;
  }

  .main-area {
    margin-left: 220px;
    width: calc(100% - 220px);
  }

  .content {
    padding-right: 22px;
    padding-left: 22px;
  }
}

@media (max-width: 700px) {
  .sidebar {
    position: relative;
    top: auto;
    right: auto;
    bottom: auto;
    width: 100%;
    height: auto;
    max-height: none;
    padding: 13px 15px 11px;
    overflow: visible;
    border-right: 0;
    border-bottom: 1px solid rgb(148 163 184 / 15%);
    box-shadow: 0 5px 18px rgb(15 23 42 / 8%);
  }

  .brand.brand-link {
    min-height: 40px;
    margin-bottom: 14px;
    padding: 0 3px;
  }

  .brand-mark {
    flex-basis: 36px;
    width: 36px;
    height: 36px;
    border-radius: 11px;
    font-size: 18px;
  }

  .brand-copy strong {
    font-size: 15px;
  }

  .navigation-label {
    display: none;
  }

  .navigation {
    flex-direction: row;
    gap: 6px;
    margin: 0 -2px;
    padding: 0 2px 5px;
    overflow-x: auto;
    overscroll-behavior-x: contain;
    scrollbar-width: thin;
  }

  .navigation a {
    flex: 0 0 auto;
    min-height: 36px;
    padding: 8px 10px;
    font-size: 11px;
    white-space: nowrap;
  }

  .navigation a:hover {
    transform: none;
  }

  .logout-button {
    width: 100%;
    min-height: 36px;
    margin-top: 8px;
    padding: 7px 10px;
  }

  .main-area {
    width: 100%;
    margin-left: 0;
    min-height: 0;
  }

  .topbar {
    position: relative;
    min-height: 66px;
    padding: 12px 17px;
  }

  .topbar-eyebrow {
    font-size: 8px;
  }

  .topbar h1 {
    font-size: 16px;
  }

  .market-context {
    padding: 7px 9px;
    font-size: 10px;
  }

  .content {
    padding: 18px 14px 32px;
  }
}

@media (max-width: 420px) {
  .topbar {
    align-items: flex-start;
    gap: 8px;
  }

  .topbar-right {
    align-self: center;
  }

  .market-context {
    gap: 6px;
    padding: 6px 8px;
    font-size: 9px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .navigation a,
  .logout-button {
    transition: none;
  }
}


/* Small-screen release fix: reclaim the space occupied by the desktop sidebar.
   Navigation remains keyboard accessible and horizontally scrollable. */
@media (max-width: 820px) {
  .app-layout { display: block; }
  .sidebar {
    position: sticky;
    top: 0;
    left: auto;
    bottom: auto;
    display: flex;
    flex-direction: row;
    align-items: center;
    flex-wrap: nowrap;
    gap: 12px;
    width: 100%;
    height: auto;
    min-height: 70px;
    padding: 10px 14px;
    overflow-x: auto;
    overflow-y: hidden;
    box-shadow: 0 5px 16px rgba(15,23,42,.12);
  }
  .brand.brand-link { flex: 0 0 auto; min-height: 40px; margin: 0; padding: 0; }
  .brand-mark { width: 38px; height: 38px; flex-basis: 38px; }
  .brand-copy small { display: none; }
  .navigation-label { display: none; }
  .navigation {
    display: flex;
    flex-direction: row;
    align-items: center;
    flex: 1 0 auto;
    width: auto;
    gap: 4px;
  }
  .navigation a { flex: 0 0 auto; min-height: 38px; white-space: nowrap; padding: 9px 11px; font-size: 13px; }
  .logout-button {
    flex: 0 0 auto;
    width: auto;
    margin: 0;
    padding: 9px 11px;
    white-space: nowrap;
    font-size: 13px;
  }
  .main-area { width: 100%; margin-left: 0; min-width: 0; }
  .topbar { min-height: 64px; padding: 12px 18px; }
  .content { padding: 18px; }
}
@media (max-width: 480px) {
  .brand-copy strong { display: none; }
  .sidebar { gap: 8px; padding: 8px 10px; }
  .topbar { gap: 8px; flex-wrap: wrap; padding: 12px; }
  .content { padding: 12px; }
}

</style>
