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
          <div class="flex items-center gap-3">
            <div class="icon-badge flex h-10 w-10 items-center justify-center rounded-[var(--radius-base)]">
              <Layers :size="18" class="text-[var(--color-accent)]" />
            </div>
            <h1 class="text-xl font-semibold tracking-tight">{{ strategy.name }}</h1>
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

      <BaseCard :padded="false">
        <nav class="flex border-b border-[var(--color-border)] px-5">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            type="button"
            class="flex items-center gap-1.5 border-b-2 px-3 py-3.5 text-[13px] font-medium transition-colors"
            :class="activeTab === tab.id ? 'border-[var(--color-accent)] text-[var(--color-text-primary)]' : 'border-transparent text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)]'"
            @click="activeTab = tab.id"
          >
            <component :is="tab.icon" :size="14" />
            {{ tab.label }}
          </button>
        </nav>

        <div class="p-5">
          <div v-if="activeTab === 'config'" class="grid grid-cols-1 gap-8 lg:grid-cols-2">
            <div>
              <h3 class="label-caps mb-4">Active config</h3>
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
            <div>
              <h3 class="label-caps mb-4">Version history</h3>
              <VersionHistoryPanel :resource="detailStore.versions" @retry="detailStore.fetchVersions" @activate="activateVersion" />
            </div>
          </div>

          <RunHistoryPanel v-else-if="activeTab === 'runs'" :resource="detailStore.runs" @retry="detailStore.fetchRuns" />

          <SignalsPanel v-else-if="activeTab === 'signals'" :strategy-name="strategy.name" />

          <StrategyPositionsPanel v-else-if="activeTab === 'positions'" :strategy-id="strategy.id" />
        </div>
      </BaseCard>
    </template>
  </div>
</template>

<script>
import { ArrowLeft, History, Layers, Power, PowerOff, Radar, Save, SlidersHorizontal, Wallet } from "@lucide/vue"
import { useStrategiesStore } from "@/stores/strategies"
import { useStrategyDetailStore } from "@/stores/strategyDetail"
import BaseButton from "@/components/primitives/BaseButton.vue"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import StatusPill from "@/components/primitives/StatusPill.vue"
import ConfigFieldForm from "@/components/strategies/ConfigFieldForm.vue"
import RunHistoryPanel from "@/components/strategies/RunHistoryPanel.vue"
import SignalsPanel from "@/components/strategies/SignalsPanel.vue"
import StrategyPositionsPanel from "@/components/strategies/StrategyPositionsPanel.vue"
import VersionHistoryPanel from "@/components/strategies/VersionHistoryPanel.vue"

export default {
  name: "StrategyDetailView",
  components: { BaseButton, BaseCard, EmptyState, StatusPill, ConfigFieldForm, RunHistoryPanel, SignalsPanel, StrategyPositionsPanel, VersionHistoryPanel, ArrowLeft, Layers },
  data() {
    return {
      activeTab: "config",
      tabs: [
        { id: "config", label: "Configuration", icon: SlidersHorizontal },
        { id: "runs", label: "Run history", icon: History },
        { id: "signals", label: "Signals", icon: Radar },
        { id: "positions", label: "Positions", icon: Wallet },
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
    // strategy is only available once strategiesStore resolves (a deep-link straight to this page
    // starts with it null), so the draft is reset here rather than solely in created()/beforeRouteUpdate.
    strategy() {
      this.resetDraftFromActiveVersion()
    },
  },
  created() {
    if (this.strategiesStore.resource.status === "idle") this.strategiesStore.fetch()
    this.detailStore.loadFor(this.strategyId)
    this.resetDraftFromActiveVersion()
  },
  // Vue Router reuses this component instance across param-only navigations, so mounted()/created()
  // won't re-fire — this hook is what actually resets per-strategy state on a direct id change.
  async beforeRouteUpdate(to) {
    await this.detailStore.loadFor(Number(to.params.id))
  },
  methods: {
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
