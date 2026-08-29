<template>
  <div class="mx-auto flex max-w-[var(--content-max-width)] flex-col gap-4">
    <JobsPanel @trigger="triggering = $event" />
    <JobTriggerModal v-if="triggering" :job="triggering" @close="triggering = null" />
  </div>
</template>

<script>
import { usePageHeaderStore } from "@/stores/pageHeader"
import JobTriggerModal from "@/components/operations/JobTriggerModal.vue"
import JobsPanel from "@/components/operations/JobsPanel.vue"

export default {
  name: "JobsView",
  components: { JobsPanel, JobTriggerModal },
  data() {
    return { triggering: null }
  },
  created() {
    usePageHeaderStore().set("Jobs", "Trading and data-pipeline background operations")
  },
}
</script>
