<template>
  <div class="mx-auto flex max-w-[var(--content-max-width)] flex-col gap-4">
    <BaseCard title="Securities pipeline" :icon="Waypoints">
      <LoadingState v-if="jobsStore.resource.status === 'loading'" />
      <div v-else class="flex flex-col gap-0">
        <template v-for="(step, i) in securitiesPipeline" :key="step.name">
          <PipelineStep :job="findJob(step.name)" :label="step.label" />
          <div v-if="i < securitiesPipeline.length - 1" class="ml-4 h-4 w-px bg-[var(--color-border-strong)]" />
        </template>
      </div>
    </BaseCard>

    <BaseCard title="Options pipeline" :icon="Boxes">
      <LoadingState v-if="jobsStore.resource.status === 'loading'" />
      <div v-else class="flex flex-col gap-0">
        <PipelineStep :job="findJob('OPTION_CHAIN_IMPORT')" label="Option chain import" />
        <div class="ml-4 h-4 w-px bg-[var(--color-border-strong)]" />
        <PipelineStep :job="findJob('STRATEGY_EXECUTION')" label="Options strategy execution" />
      </div>
    </BaseCard>

    <BaseCard title="Broker connectivity" :icon="Link2">
      <LoadingState v-if="jobsStore.resource.status === 'loading'" />
      <PipelineStep v-else :job="findJob('KITE_TOKEN_REFRESH')" label="Kite token refresh" />
    </BaseCard>
  </div>
</template>

<script>
import { Boxes, Link2, Waypoints } from "@lucide/vue"
import { useJobsStore } from "@/stores/jobs"
import { usePageHeaderStore } from "@/stores/pageHeader"
import BaseCard from "@/components/primitives/BaseCard.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import PipelineStep from "@/components/operations/PipelineStep.vue"

const SECURITIES_PIPELINE = [
  { name: "SECURITIES_IMPORT", label: "Securities import" },
  { name: "SECURITIES_ENRICHMENT", label: "Enrichment" },
  { name: "OHLCV_IMPORT", label: "OHLCV import" },
  { name: "FEATURE_GENERATION", label: "Feature generation" },
  { name: "STRATEGY_EXECUTION", label: "Strategy execution" },
]

export default {
  name: "DataPipelineView",
  components: { BaseCard, LoadingState, PipelineStep },
  data() {
    return { Waypoints, Boxes, Link2, securitiesPipeline: SECURITIES_PIPELINE }
  },
  computed: {
    jobsStore() {
      return useJobsStore()
    },
  },
  created() {
    usePageHeaderStore().set("Data Pipeline", "Is Atlas's data current?")
    if (this.jobsStore.resource.status === "idle") this.jobsStore.fetch()
  },
  methods: {
    findJob(name) {
      return this.jobsStore.jobs.find((j) => j.name === name) ?? null
    },
  },
}
</script>
