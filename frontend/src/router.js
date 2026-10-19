
import { createRouter, createWebHistory } from "vue-router";

import AppLayout from "./components/layout/AppLayout.vue";

const routes = [
  {
    path: "/",
    component: AppLayout,
    children: [
      {
        path: "",
        name: "Dashboard",
        component: () => import("./views/Dashboard.vue"),
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
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
