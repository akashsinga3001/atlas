<template>
  <BaseCard title="Schedule entries" :icon="CalendarClock">
    <template #header-actions>
      <div class="flex items-center gap-2">
        <BaseButton variant="secondary" size="sm" :icon="RefreshCw" @click="resync">Resync</BaseButton>
        <BaseButton variant="primary" size="sm" :icon="Plus" @click="$emit('create')">New entry</BaseButton>
      </div>
    </template>

    <LoadingState v-if="store.resource.status === 'loading'" />
    <ErrorState v-else-if="store.resource.status === 'error' && !store.resource.data" :message="store.resource.error" @retry="store.fetch" />
    <EmptyState v-else-if="!store.entries.length" title="No schedule entries" />
    <div v-else class="overflow-x-auto">
      <table class="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Group</th>
            <th>Task</th>
            <th>Cron</th>
            <th>Enabled</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="entry in store.entries" :key="entry.id">
            <td class="whitespace-nowrap font-medium">{{ entry.name }}</td>
            <td><span class="label-caps">{{ entry.group }}</span></td>
            <td class="font-mono-nums whitespace-nowrap text-[var(--color-text-secondary)]">{{ entry.task }}</td>
            <td class="font-mono-nums whitespace-nowrap text-[var(--color-text-secondary)]">{{ entry.minute }} {{ entry.hour }} {{ entry.day_of_month }} {{ entry.month_of_year }} {{ entry.day_of_week }}</td>
            <td>
              <button type="button" class="relative h-5 w-9 rounded-full transition-colors" :class="entry.enabled ? 'bg-[var(--color-positive)]' : 'bg-[var(--color-border-strong)]'" @click="toggle(entry)">
                <span class="absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all" style="box-shadow: 0 1px 3px rgba(20, 21, 26, 0.25)" :class="entry.enabled ? 'left-4' : 'left-0.5'" />
              </button>
            </td>
            <td class="text-right">
              <div class="flex justify-end gap-1">
                <BaseButton variant="ghost" size="sm" :icon="Pencil" @click="$emit('edit', entry)">Edit</BaseButton>
                <BaseButton variant="ghost" size="sm" :icon="Trash2" @click="confirmingDelete = entry">Delete</BaseButton>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Teleported to <body> — see ScheduleEntryModal.vue for why: a fixed-position modal
         nested inside a BaseCard gets trapped inside it by animate-fade's resting transform. -->
    <Teleport to="body">
    <div v-if="confirmingDelete" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" @click.self="confirmingDelete = null">
      <div class="w-full max-w-sm rounded-[var(--radius-lg)] bg-[var(--color-overlay)] p-6" style="box-shadow: var(--shadow-overlay)">
        <h3 class="text-[15px] font-semibold text-[var(--color-text-primary)]">Delete schedule entry?</h3>
        <p class="mt-2 text-[13px] leading-relaxed text-[var(--color-text-secondary)]">
          <span class="font-medium text-[var(--color-text-primary)]">{{ confirmingDelete.name }}</span> will stop running immediately. This can't be undone.
        </p>
        <div class="mt-5 flex justify-end gap-2">
          <BaseButton variant="ghost" size="sm" @click="confirmingDelete = null">Cancel</BaseButton>
          <BaseButton variant="danger" size="sm" :loading="removing" @click="remove">Delete</BaseButton>
        </div>
      </div>
    </div>
    </Teleport>
  </BaseCard>
</template>

<script>
import { CalendarClock, Pencil, Plus, RefreshCw, Trash2 } from "@lucide/vue"
import BaseButton from "@/components/primitives/BaseButton.vue"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import { useScheduleStore } from "@/stores/schedule"

export default {
  name: "SchedulePanel",
  components: { BaseButton, BaseCard, EmptyState, ErrorState, LoadingState },
  emits: ["create", "edit"],
  data() {
    return { CalendarClock, RefreshCw, Plus, Pencil, Trash2, confirmingDelete: null, removing: false }
  },
  computed: {
    store() {
      return useScheduleStore()
    },
  },
  created() {
    if (this.store.resource.status === "idle") this.store.fetch()
  },
  methods: {
    toggle(entry) {
      this.store.toggle(entry.id, !entry.enabled)
    },
    resync() {
      this.store.resync()
    },
    async remove() {
      this.removing = true
      await this.store.remove(this.confirmingDelete.id)
      this.removing = false
      this.confirmingDelete = null
    },
  },
}
</script>
