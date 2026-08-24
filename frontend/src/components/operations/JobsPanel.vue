<template>
  <div>
    <LoadingState v-if="store.resource.status === 'loading'" />
    <ErrorState v-else-if="store.resource.status === 'error' && !store.resource.data" :message="store.resource.error" @retry="store.fetch" />
    <EmptyState v-else-if="!store.jobs.length" title="No jobs registered" />
    <table v-else class="w-full text-sm">
      <thead>
        <tr class="border-b border-[var(--color-border)] text-left">
          <th class="label-caps pb-3.5 font-normal">Job</th>
          <th class="label-caps pb-3.5 font-normal">Schedule</th>
          <th class="label-caps pb-3.5 font-normal">Last run</th>
          <th class="label-caps pb-3.5 font-normal"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="job in store.jobs" :key="job.name" class="border-b border-[var(--color-border)] last:border-0">
          <td class="py-4">
            <div class="flex items-center gap-3">
              <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--radius-sm)] bg-[var(--color-surface-alt)]">
                <Cog :size="14" class="text-[var(--color-text-tertiary)]" />
              </div>
              <div>
                <p class="font-medium text-[var(--color-text-primary)]">{{ job.display_name }}</p>
                <p class="text-xs text-[var(--color-text-tertiary)]">{{ job.description }}</p>
              </div>
            </div>
          </td>
          <td class="font-mono-nums py-4 text-xs text-[var(--color-text-secondary)]">{{ job.schedule }}</td>
          <td class="py-4">
            <div v-if="job.last_run_at" class="flex items-center gap-2">
              <StatusPill :label="job.last_run_status" :tone="statusTone(job.last_run_status)" />
              <span class="text-xs text-[var(--color-text-tertiary)]">{{ formatDateTime(job.last_run_at) }}</span>
            </div>
            <span v-else class="text-xs text-[var(--color-text-tertiary)]">Never run</span>
          </td>
          <td class="py-4 text-right">
            <BaseButton variant="secondary" size="sm" :icon="Play" @click="$emit('trigger', job)">Trigger</BaseButton>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import { Cog, Play } from "@lucide/vue"
import BaseButton from "@/components/primitives/BaseButton.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import StatusPill from "@/components/primitives/StatusPill.vue"
import { useJobsStore } from "@/stores/jobs"
import { formatDateTime } from "@/utils/format"

const STATUS_TONE = { queued: "warning", running: "live", success: "positive", failure: "error", stale: "inactive" }

export default {
  name: "JobsPanel",
  components: { BaseButton, EmptyState, ErrorState, LoadingState, StatusPill, Cog },
  emits: ["trigger"],
  data() {
    return { Play }
  },
  computed: {
    store() {
      return useJobsStore()
    },
  },
  methods: {
    formatDateTime,
    statusTone(status) {
      return STATUS_TONE[status] ?? "inactive"
    },
  },
}
</script>
