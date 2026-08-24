<template>
  <div>
    <LoadingState v-if="resource.status === 'loading'" />
    <ErrorState v-else-if="resource.status === 'error' && !resource.data" :message="resource.error" @retry="$emit('retry')" />
    <EmptyState v-else-if="!runs.length" title="No runs yet" />
    <table v-else class="w-full text-sm">
      <thead>
        <tr class="border-b border-[var(--color-border)] text-left">
          <th class="label-caps pb-3 font-normal">Version</th>
          <th class="label-caps pb-3 font-normal">Status</th>
          <th class="label-caps pb-3 font-normal">Started</th>
          <th class="label-caps pb-3 font-normal">Signals</th>
          <th class="label-caps pb-3 font-normal">Error</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="run in runs" :key="run.id" class="border-b border-[var(--color-border)] last:border-0">
          <td class="font-mono-nums py-3.5">v{{ run.version }}</td>
          <td class="py-3.5"><StatusPill :label="run.status" :tone="statusTone(run.status)" /></td>
          <td class="py-3.5 text-[var(--color-text-secondary)]">{{ formatDateTime(run.started_at) }}</td>
          <td class="font-mono-nums py-3.5">{{ run.signal_count ?? "—" }}</td>
          <td class="max-w-xs truncate py-3.5 text-[var(--color-negative)]" :title="run.error_message ?? ''">{{ run.error_message ?? "—" }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import StatusPill from "@/components/primitives/StatusPill.vue"
import { formatDateTime } from "@/utils/format"

const STATUS_TONE = { COMPLETED: "positive", RUNNING: "live", PENDING: "inactive", FAILED: "error" }

export default {
  name: "RunHistoryPanel",
  components: { EmptyState, ErrorState, LoadingState, StatusPill },
  props: {
    resource: {
      type: Object,
      required: true,
    },
  },
  emits: ["retry"],
  computed: {
    runs() {
      return this.resource.data ?? []
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
