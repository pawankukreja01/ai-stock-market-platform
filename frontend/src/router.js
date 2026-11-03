import { createRouter, createWebHistory } from "vue-router";
import { getCurrentUser } from "./services/api";
import AppLayout from "./components/layout/AppLayout.vue";
import { logoutPending, markLogoutPending, recordSessionExpiry, sessionIsPastDeadline } from "./utils/sessionSafety.js";
import { resolvePendingLogout } from "./utils/logoutFlow.js";

const routes = [
  {
    path: "/login",
    name: "Login",
    component: () => import("./views/auth/Login.vue"),
    meta: { guestOnly: true },
  },
  {
    path: "/register",
    name: "Register",
    component: () => import("./views/auth/Register.vue"),
    meta: { guestOnly: true },
  },
  {
    path: "/verify-email",
    name: "VerifyEmail",
    component: () => import("./views/auth/VerifyEmail.vue"),
  },
  {
    path: "/forgot-password",
    name: "ForgotPassword",
    component: () => import("./views/auth/ForgotPassword.vue"),
  },
  {
    path: "/reset-password/:uid/:token",
    name: "ResetPassword",
    component: () => import("./views/auth/ResetPassword.vue"),
  },
  {
    path: "/",
    component: AppLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: "",
        name: "Dashboard",
        component: () => import("./views/Dashboard.vue"),
      },
      {
        path: "profile",
        name: "Profile",
        component: () => import("./views/Profile.vue"),
      },
      {
        path: "discover",
        name: "DiscoverStocks",
        component: () => import("./views/DiscoverStocks.vue"),
      },
      {
        path: "stocks/:symbol",
        name: "StockResearch",
        component: () => import("./views/StockResearch.vue"),
        props: true,
      },
      {
        path: "research-health",
        name: "ResearchHealth",
        component: () => import("./views/ResearchHealth.vue"),
      },
      {
        path: "screener",
        name: "StockScreener",
        component: () => import("./views/StockScreener.vue"),
      },
      {
        path: "portfolio",
        name: "Portfolio",
        component: () => import("./views/Portfolio.vue"),
      },
      {
        path: "investment-simulator",
        name: "InvestmentSimulator",
        component: () => import("./views/InvestmentSimulator.vue"),
      },
      {
        path: "alerts",
        name: "Alerts",
        component: () => import("./views/Alerts.vue"),
      },
      {
        path: "recommendations",
        name: "Recommendations",
        component: () => import("./views/Recommendations.vue"),
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach(async (to) => {
  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth);
  const guestOnly = to.meta.guestOnly === true;

  // Public verification/reset pages do not need an unnecessary /me request.
  if (!requiresAuth && !guestOnly) return true;

  // A failed sign-out MUST NOT be overridden by a stale Django cookie.
  // Recheck the server, but never unblock a protected route until resolved.
  if (logoutPending()) {
    const resolved = await resolvePendingLogout();
    if (!resolved) return requiresAuth ? "/login" : true;
  }

  let user = null;
  try {
    const response = await getCurrentUser();
    const expiresAt = response?.session?.expires_at;
    if (response?.user && expiresAt && !sessionIsPastDeadline(expiresAt)) {
      user = response.user;
      recordSessionExpiry(expiresAt);
    } else if (response?.user) {
      // Any legacy or malformed session without a server deadline is denied.
      markLogoutPending();
      return requiresAuth ? "/login" : true;
    }
  } catch {
    user = null;
  }

  if (guestOnly && user) return "/";
  if (requiresAuth && !user) return "/login";

  return true;
});

export default router;