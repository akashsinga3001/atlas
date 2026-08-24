import { apiClient } from "./client"
import { unwrap } from "./unwrap"
import type { CashFlow, CashFlowCreate } from "@/types/fund"

export function fetchCashFlows() {
  return unwrap<CashFlow[]>(() => apiClient.get("/fund/cashflow"))
}

export function createCashFlow(request: CashFlowCreate) {
  return unwrap<CashFlow>(() => apiClient.post("/fund/cashflow", request))
}
