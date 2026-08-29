<template>
  <div class="mx-auto flex max-w-[var(--content-max-width)] flex-col gap-4">
    <SchedulePanel @create="showCreate = true" @edit="editing = $event" />
    <ScheduleEntryModal v-if="showCreate || editing" :entry="editing" @close="close" />
  </div>
</template>

<script>
import { usePageHeaderStore } from "@/stores/pageHeader"
import ScheduleEntryModal from "@/components/operations/ScheduleEntryModal.vue"
import SchedulePanel from "@/components/operations/SchedulePanel.vue"

export default {
  name: "SchedulesView",
  components: { SchedulePanel, ScheduleEntryModal },
  data() {
    return { showCreate: false, editing: null }
  },
  created() {
    usePageHeaderStore().set("Schedules", "When jobs execute")
  },
  methods: {
    close() {
      this.showCreate = false
      this.editing = null
    },
  },
}
</script>
