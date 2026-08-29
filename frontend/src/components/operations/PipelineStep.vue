<template>
  <div class="flex items-center justify-between py-2">
    <div class="flex items-center gap-3">
      <span class="h-2 w-2 shrink-0 rounded-full" :class="dotClass" />
      <div>
        <p class="text-[13px] font-medium text-[var(--color-text-primary)]">{{ label }}</p>
        <p v-if="job?.last_run_error" class="text-[11px] text-[var(--color-error)]">{{ job.last_run_error }}</p>
      </div>
    </div>
    <div class="flex items-center gap-3 text-[12px]">
      <StatusPill v-if="job?.last_run_status" :label="job.last_run_status" :tone="statusTone" />
      <span class="text-[var(--color-text-tertiary)]">{{ job?.last_run_at ? formatDateTime(job.last_run_at) : "Never run" }}</span>
    </div>
  </div>
</template>

<script>
import StatusPill from "@/components/primitives/StatusPill.vue"
import { formatDateTime } from "@/utils/format"

const STATUS_TONE = { queued: "warning", running: "live", success: "positive", failure: "error", stale: "inactive" }

export default {
  name: "PipelineStep",
  components: { StatusPill },
  props: {
    job: {
      type: Object,
      default: null,
    },
    label: {
      type: String,
      required: true,
    },
  },
  computed: {
    statusTone() {
      return STATUS_TONE[this.job?.last_run_status] ?? "inactive"
    },
    dotClass() {
      if (!this.job?.last_run_status) return "bg-[var(--color-inactive)]"
      if (this.job.last_run_status === "failure") return "bg-[var(--color-risk-hot)]"
      if (this.job.last_run_status === "success") return "bg-[var(--color-risk-calm)]"
      return "bg-[var(--color-risk-elevated)]"
    },
  },
  methods: {
    formatDateTime,
  },
}
</script>
