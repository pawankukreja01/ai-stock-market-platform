import { createRouter, createWebHistory } from "vue-router";

import AppLayout from "./components/layout/AppLayout.vue";
import Dashboard from "./views/Dashboard.vue";

const routes = [
  {
    path: "/",
    component: AppLayout,
    children: [
      {
        path: "",
        name: "Dashboard",
        component: Dashboard,
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;