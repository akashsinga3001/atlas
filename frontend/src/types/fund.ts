export type FlowType = "deposit" | "withdrawal"

export interface CashFlow {
  id: number
  flow_type: FlowType
  amount: number
  flow_date: string
  note: string | null
}

export interface CashFlowCreate {
  flow_type: FlowType
  amount: number
  flow_date: string
  note?: string
}
