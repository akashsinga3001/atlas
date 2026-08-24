import { createRouter, createWebHistory } from "vue-router"

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "dashboard",
      component: () => import("@/views/DashboardView.vue"),
    },
    {
      path: "/strategies",
      name: "strategies",
      component: () => import("@/views/StrategiesView.vue"),
    },
    {
      path: "/strategies/:id",
      name: "strategy-detail",
      component: () => import("@/views/StrategyDetailView.vue"),
    },
    {
      path: "/positions",
      name: "positions",
      component: () => import("@/views/PositionsView.vue"),
    },
    {
      path: "/performance",
      name: "performance",
      component: () => import("@/views/PerformanceView.vue"),
    },
    {
      path: "/operations",
      name: "operations",
      component: () => import("@/views/OperationsView.vue"),
    },
    {
      path: "/signals/:id",
      name: "signal-detail",
      component: () => import("@/views/SignalDetailView.vue"),
    },
  ],
})

export default router
