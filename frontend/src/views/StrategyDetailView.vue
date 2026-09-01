<template>
  <div class="mx-auto flex max-w-[var(--content-max-width)] flex-col gap-4">
    <div v-if="!strategy">
      <EmptyState title="Strategy not found" />
    </div>
    <template v-else>
      <div>
        <router-link to="/strategies" class="inline-flex items-center gap-1 text-xs text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)]">
          <ArrowLeft :size="12" />
          Strategies
        </router-link>
        <div class="mt-2 flex items-center justify-between">
          <div class="flex items-center gap-2.5">
            <h1 class="font-display text-xl font-bold tracking-tight text-[var(--color-text-primary)]">{{ strategy.name }}</h1>
            <span v-if="strategy.code === 'dummy'" class="label-caps rounded-[var(--radius-sm)] bg-[var(--color-inactive-bg)] px-1.5 py-0.5">Test strategy</span>
          </div>
          <div class="flex items-center gap-2">
            <StatusPill :label="`${strategy.open_positions_count} open`" tone="inactive" />
            <BaseButton
              :variant="strategy.is_active ? 'secondary' : 'primary'"
              size="sm"
              :icon="strategy.is_active ? PowerOff : Power"
              :loading="togglingActive"
              @click="toggleActive"
            >
              {{ strategy.is_active ? "Disable" : "Enable" }}
            </BaseButton>
          </div>
        </div>
      </div>

      <!-- State strip: the strategy's tangible run state at a glance, ahead of the tabbed
           detail below — a live/idle sense before the visitor picks a tab. -->
      <div class="surface-2 flex items-center gap-6 overflow-x-auto rounded-[var(--radius-lg)] px-5 py-3.5" :class="strategy.is_active ? 'strategy-strip-active' : ''">
        <StatusPill :label="strategy.is_active ? 'Active' : 'Disabled'" :tone="strategy.is_active ? 'live' : 'inactive'" />
        <div class="h-8 w-px shrink-0" style="background: var(--color-border)" />
        <MetricTile label="Last run" :value="strategy.last_run_at ? formatDateTime(strategy.last_run_at) : 'Never'" />
        <MetricTile label="Last status" :value="strategy.last_run_status ?? '—'" :tone="strategy.last_run_status === 'FAILED' ? 'negative' : 'neutral'" />
        <MetricTile label="Open positions" :value="String(strategy.open_positions_count)" />
      </div>

      <BaseCard :padded="false">
        <nav class="flex border-b border-[var(--color-border)] px-4">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            type="button"
            class="flex items-center gap-1.5 border-b-2 px-3 py-3 text-[12.5px] font-medium transition-colors"
            :class="activeTab === tab.id ? 'border-[var(--color-accent)] text-[var(--color-text-primary)]' : 'border-transparent text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)]'"
            @click="activeTab = tab.id"
          >
            <component :is="tab.icon" :size="13" />
            {{ tab.label }}
          </button>
        </nav>

        <div class="p-4">
          <div v-if="activeTab === 'overview'" class="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
            <MetricTile label="Status" :value="strategy.is_active ? 'Enabled' : 'Disabled'" />
            <MetricTile label="Active version" :value="strategy.active_version ? `v${strategy.active_version.version}` : '—'" />
            <MetricTile label="Last run" :value="strategy.last_run_at ? formatDateTime(strategy.last_run_at) : 'Never'" />
            <MetricTile label="Last status" :value="strategy.last_run_status ?? '—'" />
            <MetricTile label="Open positions" :value="String(strategy.open_positions_count)" />
            <MetricTile label="Execution engine" :value="strategy.active_version?.implementation_class ?? '—'" />
          </div>

          <div v-else-if="activeTab === 'versions'">
            <VersionHistoryPanel :resource="detailStore.versions" @retry="detailStore.fetchVersions" @activate="activateVersion" />
          </div>

          <RunHistoryPanel v-else-if="activeTab === 'runs'" :resource="detailStore.runs" @retry="detailStore.fetchRuns" />

          <SignalsPanel v-else-if="activeTab === 'signals'" :strategy-name="strategy.name" />

          <StrategyPositionsPanel v-else-if="activeTab === 'positions'" :strategy-id="strategy.id" />

          <div v-else-if="activeTab === 'config'">
            <ConfigFieldForm v-if="strategy.has_config_schema" v-model="draftConfig" :fields="strategy.config_fields" />
            <textarea
              v-else
              v-model="rawConfigText"
              rows="12"
              class="font-mono-nums w-full rounded-[var(--radius-sm)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2.5 py-1.5 text-xs text-[var(--color-text-primary)] focus:border-[var(--color-accent)] focus:outline-none"
            />
            <div class="mt-4 flex items-center gap-3">
              <BaseButton variant="primary" size="sm" :icon="Save" @click="saveDraft">Save as new draft version</BaseButton>
              <span v-if="saveMessage" class="text-xs text-[var(--color-text-tertiary)]">{{ saveMessage }}</span>
            </div>
          </div>
        </div>
      </BaseCard>
    </template>
  </div>
</template>

<script>
import { ArrowLeft, History, LayoutGrid, Power, PowerOff, Radar, Save, SlidersHorizontal, Wallet } from "@lucide/vue"
import { usePageHeaderStore } from "@/stores/pageHeader"
import { useStrategiesStore } from "@/stores/strategies"
import { useStrategyDetailStore } from "@/stores/strategyDetail"
import BaseButton from "@/components/primitives/BaseButton.vue"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import MetricTile from "@/components/primitives/MetricTile.vue"
import StatusPill from "@/components/primitives/StatusPill.vue"
import ConfigFieldForm from "@/components/strategies/ConfigFieldForm.vue"
import RunHistoryPanel from "@/components/strategies/RunHistoryPanel.vue"
import SignalsPanel from "@/components/strategies/SignalsPanel.vue"
import StrategyPositionsPanel from "@/components/strategies/StrategyPositionsPanel.vue"
import VersionHistoryPanel from "@/components/strategies/VersionHistoryPanel.vue"
import { formatDateTime } from "@/utils/format"

export default {
  name: "StrategyDetailView",
  components: { BaseButton, BaseCard, EmptyState, MetricTile, StatusPill, ConfigFieldForm, RunHistoryPanel, SignalsPanel, StrategyPositionsPanel, VersionHistoryPanel, ArrowLeft },
  data() {
    return {
      activeTab: "overview",
      tabs: [
        { id: "overview", label: "Overview", icon: LayoutGrid },
        { id: "versions", label: "Versions", icon: SlidersHorizontal },
        { id: "runs", label: "Runs", icon: History },
        { id: "signals", label: "Signals", icon: Radar },
        { id: "positions", label: "Positions", icon: Wallet },
        { id: "config", label: "Configuration", icon: SlidersHorizontal },
      ],
      draftConfig: {},
      rawConfigText: "",
      saveMessage: "",
      togglingActive: false,
      Save,
      Power,
      PowerOff,
    }
  },
  computed: {
    strategiesStore() {
      return useStrategiesStore()
    },
    detailStore() {
      return useStrategyDetailStore()
    },
    strategyId() {
      return Number(this.$route.params.id)
    },
    strategy() {
      return this.strategiesStore.strategies.find((s) => s.id === this.strategyId) ?? null
    },
  },
  watch: {
    strategy() {
      this.resetDraftFromActiveVersion()
      if (this.strategy) usePageHeaderStore().set(this.strategy.name, this.strategy.code)
    },
  },
  created() {
    usePageHeaderStore().set("Strategy detail")
    if (this.strategiesStore.resource.status === "idle") this.strategiesStore.fetch()
    this.detailStore.loadFor(this.strategyId)
    this.resetDraftFromActiveVersion()
  },
  async beforeRouteUpdate(to) {
    await this.detailStore.loadFor(Number(to.params.id))
  },
  methods: {
    formatDateTime,
    resetDraftFromActiveVersion() {
      const config = this.strategy?.active_version?.config ?? {}
      this.draftConfig = { ...config }
      this.rawConfigText = JSON.stringify(config, null, 2)
    },
    async saveDraft() {
      let config = this.draftConfig
      if (!this.strategy.has_config_schema) {
        try {
          config = JSON.parse(this.rawConfigText)
        } catch {
          this.saveMessage = "Invalid JSON — fix before saving."
          return
        }
      }
      const result = await this.detailStore.createDraft(config)
      this.saveMessage = result.error ? result.message ?? "Failed to save draft." : "Draft version created."
    },
    async activateVersion(versionId) {
      await this.detailStore.activate(versionId)
      await this.strategiesStore.fetch()
    },
    async toggleActive() {
      this.togglingActive = true
      await this.strategiesStore.setActive(this.strategy.id, !this.strategy.is_active)
      this.togglingActive = false
    },
  },
}
</script>

<style scoped>
.strategy-strip-active {
  box-shadow: inset 0 1px 0 var(--highlight-subtle), inset 3px 0 0 var(--color-live);
}
</style>
