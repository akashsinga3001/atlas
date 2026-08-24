<template>
  <BaseCard title="Needs attention" :icon="AlertTriangle">
    <ul v-if="items.length" class="flex flex-col gap-2">
      <li
        v-for="item in items"
        :key="item.id"
        class="flex items-center gap-2.5 rounded-[var(--radius-sm)] border px-3 py-2.5 text-xs"
        :class="item.tone === 'error' ? 'border-[var(--color-error-border)] bg-[var(--color-error-bg)] text-[var(--color-error)]' : 'border-[var(--color-warning-border)] bg-[var(--color-warning-bg)] text-[var(--color-warning)]'"
      >
        <component :is="item.tone === 'error' ? XCircle : AlertTriangle" :size="14" class="shrink-0" />
        {{ item.message }}
      </li>
    </ul>
    <div v-else class="flex items-center gap-2 text-xs text-[var(--color-positive)]">
      <CheckCircle2 :size="14" />
      All clear — no strategies, breakers, or allocations need attention.
    </div>
  </BaseCard>
</template>

<script>
import { AlertTriangle, CheckCircle2, XCircle } from "@lucide/vue"
import BaseCard from "@/components/primitives/BaseCard.vue"

export default {
  name: "AttentionFeed",
  components: { BaseCard, CheckCircle2, XCircle },
  props: {
    items: {
      type: Array,
      required: true,
    },
  },
  data() {
    return { AlertTriangle }
  },
}
</script>
