<template>
  <div>
    <div class="mb-4 flex items-center justify-end gap-2">
      <BaseButton variant="secondary" size="sm" :icon="RefreshCw" @click="resync">Resync to Redis</BaseButton>
      <BaseButton variant="primary" size="sm" :icon="Plus" @click="$emit('create')">New entry</BaseButton>
    </div>

    <LoadingState v-if="store.resource.status === 'loading'" />
    <ErrorState v-else-if="store.resource.status === 'error' && !store.resource.data" :message="store.resource.error" @retry="store.fetch" />
    <EmptyState v-else-if="!store.entries.length" title="No schedule entries" />
    <table v-else class="w-full text-sm">
      <thead>
        <tr class="border-b border-[var(--color-border)] text-left">
          <th class="label-caps pb-3.5 font-normal">Name</th>
          <th class="label-caps pb-3.5 font-normal">Task</th>
          <th class="label-caps pb-3.5 font-normal">Cron</th>
          <th class="label-caps pb-3.5 font-normal">Enabled</th>
          <th class="label-caps pb-3.5 font-normal"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="entry in store.entries" :key="entry.id" class="border-b border-[var(--color-border)] last:border-0">
          <td class="py-4">
            <div class="flex items-center gap-3">
              <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--radius-sm)] bg-[var(--color-surface-alt)]">
                <CalendarClock :size="14" class="text-[var(--color-text-tertiary)]" />
              </div>
              <div>
                <p class="font-medium text-[var(--color-text-primary)]">{{ entry.name }}</p>
                <p class="label-caps mt-0.5">{{ entry.group }}</p>
              </div>
            </div>
          </td>
          <td class="font-mono-nums py-4 text-xs text-[var(--color-text-secondary)]">{{ entry.task }}</td>
          <td class="font-mono-nums py-4 text-xs text-[var(--color-text-secondary)]">{{ entry.minute }} {{ entry.hour }} {{ entry.day_of_month }} {{ entry.month_of_year }} {{ entry.day_of_week }}</td>
          <td class="py-4">
            <button type="button" class="relative h-5 w-9 rounded-full transition-colors" :class="entry.enabled ? 'bg-[var(--color-positive)]' : 'bg-[var(--color-inactive-bg)]'" @click="toggle(entry)">
              <span class="absolute top-0.5 h-4 w-4 rounded-full bg-[var(--color-bg)] transition-all" :class="entry.enabled ? 'left-4' : 'left-0.5'" />
            </button>
          </td>
          <td class="py-4 text-right">
            <BaseButton variant="ghost" size="sm" :icon="Pencil" @click="$emit('edit', entry)">Edit</BaseButton>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import { CalendarClock, Pencil, Plus, RefreshCw } from "@lucide/vue"
import BaseButton from "@/components/primitives/BaseButton.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import { useScheduleStore } from "@/stores/schedule"

export default {
  name: "SchedulePanel",
  components: { BaseButton, EmptyState, ErrorState, LoadingState, CalendarClock },
  emits: ["create", "edit"],
  data() {
    return { RefreshCw, Plus, Pencil }
  },
  computed: {
    store() {
      return useScheduleStore()
    },
  },
  methods: {
    toggle(entry) {
      this.store.toggle(entry.id, !entry.enabled)
    },
    resync() {
      this.store.resync()
    },
  },
}
</script>
