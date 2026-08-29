<template>
  <div class="overflow-x-auto">
    <table class="data-table">
      <thead>
        <tr>
          <th>Leg</th>
          <th>Type</th>
          <th class="num">Strike</th>
          <th>Side</th>
          <th class="num">Qty</th>
          <th>Status</th>
          <th class="num">Entry</th>
          <th class="num">Current</th>
          <th class="num">P&amp;L</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="leg in legs" :key="leg.id">
          <td class="font-medium">{{ roleLabel(leg.role) }}</td>
          <td>{{ leg.option_type ?? "—" }}</td>
          <td class="num font-mono-nums">{{ leg.strike ?? "—" }}</td>
          <td>
            <span class="label-caps" :class="isShort(leg.role) ? 'text-[var(--color-negative)]' : 'text-[var(--color-positive)]'">{{ isShort(leg.role) ? "Short" : "Long" }}</span>
          </td>
          <td class="num font-mono-nums">{{ leg.entry_fill_quantity ?? "—" }}</td>
          <td><StatusPill :label="leg.status" :tone="legTone(leg.status)" /></td>
          <td class="num font-mono-nums">{{ leg.entry_fill_price !== null ? formatCurrency(leg.entry_fill_price) : "—" }}</td>
          <td class="num font-mono-nums">{{ currentPrice(leg) !== null ? formatCurrency(currentPrice(leg)) : "—" }}</td>
          <td class="num font-mono-nums" :class="legPnlClass(leg)">{{ legPnl(leg) !== null ? formatCurrency(legPnl(leg), { signed: true }) : "—" }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import StatusPill from "@/components/primitives/StatusPill.vue"
import { formatCurrency } from "@/utils/format"

const SHORT_ROLES = new Set(["short_call", "short_put"])
const ROLE_LABELS = { short_call: "Short Call", short_put: "Short Put", long_call: "Long Call", long_put: "Long Put" }
const STATUS_TONES = { pending: "inactive", open: "live", closed: "inactive", failed: "error" }

export default {
  name: "PositionLegTable",
  components: { StatusPill },
  props: {
    legs: {
      type: Array,
      required: true,
    },
    quotes: {
      type: Object,
      default: () => ({}),
    },
  },
  methods: {
    formatCurrency,
    isShort(role) {
      return SHORT_ROLES.has(role)
    },
    roleLabel(role) {
      return ROLE_LABELS[role] ?? role
    },
    legTone(status) {
      return STATUS_TONES[status] ?? "inactive"
    },
    currentPrice(leg) {
      if (leg.exit_fill_price !== null && leg.exit_fill_price !== undefined) return leg.exit_fill_price
      const quote = this.quotes[leg.ticker]?.last_price
      return quote ?? null
    },
    legPnl(leg) {
      if (leg.entry_fill_price === null || !leg.entry_fill_quantity) return null
      const current = this.currentPrice(leg)
      if (current === null) return null
      const diff = this.isShort(leg.role) ? leg.entry_fill_price - current : current - leg.entry_fill_price
      return diff * leg.entry_fill_quantity
    },
    legPnlClass(leg) {
      const pnl = this.legPnl(leg)
      if (pnl === null) return "text-[var(--color-text-tertiary)]"
      return pnl >= 0 ? "text-[var(--color-positive)]" : "text-[var(--color-negative)]"
    },
  },
}
</script>
