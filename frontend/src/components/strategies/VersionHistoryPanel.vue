<template>
  <div>
    <LoadingState v-if="resource.status === 'loading'" />
    <ErrorState v-else-if="resource.status === 'error' && !resource.data" :message="resource.error" @retry="$emit('retry')" />
    <EmptyState v-else-if="!versions.length" title="No versions yet" />
    <table v-else class="w-full text-sm">
      <thead>
        <tr class="border-b border-[var(--color-border)] text-left">
          <th class="label-caps pb-2 font-normal">Version</th>
          <th class="label-caps pb-2 font-normal">Status</th>
          <th class="label-caps pb-2 font-normal">Created</th>
          <th class="label-caps pb-2 font-normal"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="version in versions" :key="version.id" class="border-b border-[var(--color-border)] last:border-0">
          <td class="font-mono-nums py-2.5">v{{ version.version }}</td>
          <td class="py-2.5">
            <StatusPill v-if="version.is_active" label="Active" tone="live" />
            <StatusPill v-else label="Inactive" tone="inactive" />
          </td>
          <td class="py-2.5 text-[var(--color-text-secondary)]">{{ formatDateTime(version.created_at) }}</td>
          <td class="py-2.5 text-right">
            <BaseButton v-if="!version.is_active" variant="secondary" size="sm" :icon="Check" @click="$emit('activate', version.id)">Activate</BaseButton>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import { Check } from "@lucide/vue"
import BaseButton from "@/components/primitives/BaseButton.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import StatusPill from "@/components/primitives/StatusPill.vue"
import { formatDateTime } from "@/utils/format"

export default {
  name: "VersionHistoryPanel",
  components: { BaseButton, EmptyState, ErrorState, LoadingState, StatusPill },
  props: {
    resource: {
      type: Object,
      required: true,
    },
  },
  emits: ["retry", "activate"],
  data() {
    return { Check }
  },
  computed: {
    versions() {
      return this.resource.data ?? []
    },
  },
  methods: {
    formatDateTime,
  },
}
</script>
