<template>
  <BaseCard title="Cash flows" :icon="Landmark">
    <template #header-actions>
      <BaseButton variant="secondary" size="sm" :icon="Plus" @click="showModal = true">Record</BaseButton>
    </template>

    <LoadingState v-if="store.resource.status === 'loading'" />
    <ErrorState v-else-if="store.resource.status === 'error' && !store.resource.data" :message="store.resource.error" @retry="store.fetch" />
    <EmptyState v-else-if="!store.flows.length" title="No cash flows recorded" description="Deposits and withdrawals will show up here." />
    <ul v-else class="flex flex-col gap-2">
      <li v-for="flow in store.flows.slice(0, 6)" :key="flow.id" class="flex items-center justify-between text-xs">
        <span class="flex items-center gap-2">
          <component :is="flow.flow_type === 'deposit' ? ArrowDownToLine : ArrowUpFromLine" :size="13" :class="flow.flow_type === 'deposit' ? 'text-[var(--color-positive)]' : 'text-[var(--color-negative)]'" />
          <span class="text-[var(--color-text-secondary)]">{{ formatDate(flow.flow_date) }}</span>
          <span v-if="flow.note" class="text-[var(--color-text-tertiary)]">· {{ flow.note }}</span>
        </span>
        <span class="font-mono-nums font-medium" :class="flow.flow_type === 'deposit' ? 'text-[var(--color-positive)]' : 'text-[var(--color-negative)]'">
          {{ flow.flow_type === "deposit" ? "+" : "−" }}{{ formatCurrency(flow.amount, { compact: true }) }}
        </span>
      </li>
    </ul>

    <CashFlowModal v-if="showModal" @close="showModal = false" />
  </BaseCard>
</template>

<script>
import { ArrowDownToLine, ArrowUpFromLine, Landmark, Plus } from "@lucide/vue"
import { useFundStore } from "@/stores/fund"
import BaseButton from "@/components/primitives/BaseButton.vue"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import CashFlowModal from "./CashFlowModal.vue"
import { formatCurrency, formatDate } from "@/utils/format"

export default {
  name: "CashFlowCard",
  components: { BaseButton, BaseCard, EmptyState, ErrorState, LoadingState, CashFlowModal },
  data() {
    return { showModal: false, Landmark, Plus, ArrowDownToLine, ArrowUpFromLine }
  },
  computed: {
    store() {
      return useFundStore()
    },
  },
  created() {
    if (this.store.resource.status === "idle") this.store.fetch()
  },
  methods: {
    formatCurrency,
    formatDate,
  },
}
</script>
