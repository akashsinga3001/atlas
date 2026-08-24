<template>
  <div class="mx-auto flex max-w-[var(--content-max-width)] flex-col gap-5">
    <div>
      <h1 class="text-xl font-semibold tracking-tight">Operations</h1>
      <p class="mt-1 text-sm text-[var(--color-text-tertiary)]">Trigger jobs on demand, manage what's on the schedule.</p>
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
        <JobsPanel v-if="activeTab === 'jobs'" @trigger="openTrigger" />
        <SchedulePanel v-else @create="openCreate" @edit="openEdit" />
      </div>
    </BaseCard>

    <JobTriggerModal v-if="triggeringJob" :job="triggeringJob" @close="triggeringJob = null" />
    <ScheduleEntryModal v-if="showScheduleModal" :entry="editingEntry" @close="closeScheduleModal" />
  </div>
</template>

<script>
import { CalendarClock, ListChecks } from "@lucide/vue"
import { useJobsStore } from "@/stores/jobs"
import { useScheduleStore } from "@/stores/schedule"
import BaseCard from "@/components/primitives/BaseCard.vue"
import JobsPanel from "@/components/operations/JobsPanel.vue"
import JobTriggerModal from "@/components/operations/JobTriggerModal.vue"
import SchedulePanel from "@/components/operations/SchedulePanel.vue"
import ScheduleEntryModal from "@/components/operations/ScheduleEntryModal.vue"

const POLL_INTERVAL_MS = 5000

export default {
  name: "OperationsView",
  components: { BaseCard, JobsPanel, JobTriggerModal, SchedulePanel, ScheduleEntryModal },
  data() {
    return {
      activeTab: "jobs",
      triggeringJob: null,
      showScheduleModal: false,
      editingEntry: null,
      pollHandle: null,
    }
  },
  computed: {
    tabs() {
      return [
        { id: "jobs", label: "Jobs", icon: ListChecks },
        { id: "schedule", label: "Schedule", icon: CalendarClock },
      ]
    },
  },
  created() {
    useJobsStore().fetch()
    useScheduleStore().fetch()
    // Jobs run async via Celery — poll while this screen is open so triggered/queued/running
    // states resolve without a manual refresh, mirroring the old app's 5s job polling.
    this.pollHandle = setInterval(() => useJobsStore().fetch(), POLL_INTERVAL_MS)
  },
  beforeUnmount() {
    if (this.pollHandle) clearInterval(this.pollHandle)
  },
  methods: {
    openTrigger(job) {
      this.triggeringJob = job
    },
    openCreate() {
      this.editingEntry = null
      this.showScheduleModal = true
    },
    openEdit(entry) {
      this.editingEntry = entry
      this.showScheduleModal = true
    },
    closeScheduleModal() {
      this.showScheduleModal = false
      this.editingEntry = null
    },
  },
}
</script>
