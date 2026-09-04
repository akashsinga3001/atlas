<template>
  <div class="flex flex-col gap-4">
    <LoadingState v-if="store.resource.status === 'loading'" />
    <ErrorState v-else-if="store.resource.status === 'error' && !store.resource.data" :message="store.resource.error" @retry="store.fetch" />
    <EmptyState v-else-if="!store.jobs.length" title="No jobs registered" />

    <BaseCard v-for="group in groupedJobs" :key="group.name" :title="group.label" :icon="group.icon">
      <div class="overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr>
              <th>Job</th>
              <th>Schedule</th>
              <th>Status</th>
              <th>Last run</th>
              <th class="num">Duration</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="job in group.jobs" :key="job.name">
              <td>
                <p class="font-medium text-[var(--color-text-primary)]">{{ job.display_name }}</p>
                <p class="text-[11px] text-[var(--color-text-tertiary)]">{{ job.description }}</p>
              </td>
              <td class="font-mono-nums text-[var(--color-text-secondary)]">{{ job.schedule }}</td>
              <td><StatusPill v-if="job.last_run_status" :label="job.last_run_status" :tone="statusTone(job.last_run_status)" /><span v-else class="text-[var(--color-text-tertiary)]">Never run</span></td>
              <td class="text-[var(--color-text-secondary)]">{{ job.last_run_at ? formatDateTime(job.last_run_at) : "—" }}</td>
              <td class="num font-mono-nums">{{ job.last_run_duration != null ? `${job.last_run_duration?.toFixed(1)}s` : "—" }}</td>
              <td class="text-right"><BaseButton variant="secondary" size="sm" :icon="Play" @click="$emit('trigger', job)">Run now</BaseButton></td>
            </tr>
          </tbody>
        </table>
      </div>
    </BaseCard>
  </div>
</template>

<script>
import { Cpu, Play, Waypoints } from "@lucide/vue"
import BaseButton from "@/components/primitives/BaseButton.vue"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import StatusPill from "@/components/primitives/StatusPill.vue"
import { useJobsStore } from "@/stores/jobs"
import { formatDateTime } from "@/utils/format"

const STATUS_TONE = { queued: "warning", running: "live", success: "positive", failure: "error", stale: "inactive" }
const GROUPS = [
  { name: "trading", label: "Trading", icon: Cpu },
  { name: "data_pipeline", label: "Data pipeline", icon: Waypoints },
]

export default {
  name: "JobsPanel",
  components: { BaseButton, BaseCard, EmptyState, ErrorState, LoadingState, StatusPill },
  emits: ["trigger"],
  data() {
    return { Play }
  },
  computed: {
    store() {
      return useJobsStore()
    },
    groupedJobs() {
      return GROUPS.map((g) => ({ ...g, jobs: this.store.jobs.filter((j) => j.group === g.name) })).filter((g) => g.jobs.length)
    },
  },
  created() {
    if (this.store.resource.status === "idle") this.store.fetch()
  },
  methods: {
    formatDateTime,
    statusTone(status) {
      return STATUS_TONE[status] ?? "inactive"
    },
  },
}
</script>
