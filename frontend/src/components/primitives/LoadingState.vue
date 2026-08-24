<template>
  <div class="flex items-center justify-center gap-2 py-14 text-sm text-[var(--color-text-tertiary)]">
    <Loader2 :size="16" class="animate-spin" />
    {{ label }}
  </div>
</template>

<script>
import { Loader2 } from "@lucide/vue"

export default {
  name: "LoadingState",
  components: { Loader2 },
  props: {
    label: {
      type: String,
      default: "Loading…",
    },
  },
}
</script>
