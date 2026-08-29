import { createRouter, createWebHistory } from "vue-router"

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "overview",
      component: () => import("@/views/OverviewView.vue"),
    },
    {
      path: "/trades",
      name: "trades",
      component: () => import("@/views/TradesView.vue"),
    },
    {
      path: "/trades/:id",
      name: "trade-detail",
      component: () => import("@/views/TradeDetailView.vue"),
    },
    {
      path: "/options",
      name: "options",
      component: () => import("@/views/OptionsView.vue"),
    },
    {
      path: "/options/:id",
      name: "options-detail",
      component: () => import("@/views/OptionsDetailView.vue"),
    },
    {
      path: "/signals",
      name: "signals",
      component: () => import("@/views/SignalsView.vue"),
    },
    {
      path: "/signals/:id",
      name: "signal-detail",
      component: () => import("@/views/SignalDetailView.vue"),
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
      path: "/portfolio",
      name: "portfolio",
      component: () => import("@/views/PortfolioView.vue"),
    },
    {
      path: "/fund",
      name: "fund",
      component: () => import("@/views/FundView.vue"),
    },
    {
      path: "/market",
      name: "market",
      component: () => import("@/views/MarketView.vue"),
    },
    {
      path: "/risk",
      name: "risk",
      component: () => import("@/views/RiskView.vue"),
    },
    {
      path: "/operations/jobs",
      name: "jobs",
      component: () => import("@/views/JobsView.vue"),
    },
    {
      path: "/operations/schedules",
      name: "schedules",
      component: () => import("@/views/SchedulesView.vue"),
    },
    {
      path: "/data-pipeline",
      name: "data-pipeline",
      component: () => import("@/views/DataPipelineView.vue"),
    },
  ],
})

export default router
