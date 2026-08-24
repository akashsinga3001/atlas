import { defineStore } from "pinia"

import { activateVersion, createVersion, fetchRunHistory, fetchVersionHistory } from "@/services/api/strategies"
import { loadResource } from "@/stores/helpers/resource"
import { createResourceState } from "@/types/resource"
import type { ResourceState } from "@/types/resource"
import type { StrategyRun, StrategyVersion } from "@/types/strategy"

export const useStrategyDetailStore = defineStore("strategyDetail", {
  state: (): { strategyId: number | null; versions: ResourceState<StrategyVersion[]>; runs: ResourceState<StrategyRun[]> } => ({
    strategyId: null,
    versions: createResourceState<StrategyVersion[]>(),
    runs: createResourceState<StrategyRun[]>(),
  }),
  actions: {
    /** Resets both resources and loads fresh data for a strategy — call on route enter and on param change (beforeRouteUpdate), never just created(). */
    async loadFor(strategyId: number) {
      this.strategyId = strategyId
      this.versions = createResourceState<StrategyVersion[]>()
      this.runs = createResourceState<StrategyRun[]>()
      await Promise.all([this.fetchVersions(), this.fetchRuns()])
    },
    async fetchVersions() {
      if (this.strategyId === null) return
      await loadResource(this.versions, () => fetchVersionHistory(this.strategyId as number))
    },
    async fetchRuns() {
      if (this.strategyId === null) return
      await loadResource(this.runs, () => fetchRunHistory(this.strategyId as number))
    },
    async createDraft(config: Record<string, unknown>) {
      if (this.strategyId === null) return { error: true, data: null, message: "No strategy selected" }
      const result = await createVersion(this.strategyId, config)
      if (!result.error) await this.fetchVersions()
      return result
    },
    async activate(versionId: number) {
      if (this.strategyId === null) return { error: true, data: null, message: "No strategy selected" }
      const result = await activateVersion(this.strategyId, versionId)
      if (!result.error) await this.fetchVersions()
      return result
    },
  },
})
