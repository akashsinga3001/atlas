<template>
  <div class="flex flex-col items-center justify-center gap-2 py-14 text-center">
    <div class="mb-1 flex h-10 w-10 items-center justify-center rounded-full bg-[var(--color-surface-alt)]">
      <Inbox :size="18" class="text-[var(--color-text-tertiary)]" />
    </div>
    <p class="text-sm font-medium text-[var(--color-text-secondary)]">{{ title }}</p>
    <p v-if="description" class="max-w-xs text-xs text-[var(--color-text-tertiary)]">{{ description }}</p>
  </div>
</template>

<script>
import { Inbox } from "@lucide/vue"

export default {
  name: "EmptyState",
  components: { Inbox },
  props: {
    title: {
      type: String,
      required: true,
    },
    description: {
      type: String,
      default: "",
    },
  },
}
</script>
