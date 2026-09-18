<template>
  <BaseCard title="Trade Log" :icon="ArrowLeftRight" :padded="false">
    <!-- Only entries/exits — job/pipeline runs are already signaled by the System status tile
         and have their own full history on /operations/jobs. A trading dashboard's activity log
         should answer "did my strategies trade today," not double as an ops audit trail. That
         also keeps this list genuinely short most days, so a compact table reads as "quiet day"
         rather than "broken empty box." -->
    <EmptyState v-if="!items.length" title="No trades yet today" description="Entries and exits will appear here as strategies fill orders." />
    <div v-else class="overflow-x-auto px-4 pb-4">
      <table class="data-table">
        <thead>
          <tr>
            <th>Action</th>
            <th>Symbol</th>
            <th>Strategy</th>
            <th class="num">Price</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.key">
            <td>
              <span class="inline-flex items-center gap-1 text-[11.5px] font-semibold" :class="item.action === 'entry' ? 'text-[var(--color-positive)]' : 'text-[var(--color-negative)]'">
                <ArrowUpCircle v-if="item.action === 'entry'" :size="12" />
                <ArrowDownCircle v-else :size="12" />
                {{ item.action === "entry" ? "BUY" : "SELL" }}
              </span>
            </td>
            <td class="font-medium">{{ item.ticker }}</td>
            <td class="text-[var(--color-text-secondary)]">{{ item.strategy }}</td>
            <td class="num font-mono-nums">{{ item.price !== null ? formatCurrency(item.price) : "—" }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </BaseCard>
</template>

<script>
import { ArrowDownCircle, ArrowLeftRight, ArrowUpCircle } from "@lucide/vue"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import { formatCurrency } from "@/utils/format"

export default {
  name: "RecentActivityCard",
  components: { ArrowDownCircle, ArrowUpCircle, BaseCard, EmptyState },
  props: {
    items: { type: Array, required: true }, // {time, action: 'entry'|'exit', ticker, strategy, price}[]
  },
  data() {
    return { ArrowLeftRight }
  },
  methods: {
    formatCurrency,
  },
}
</script>
