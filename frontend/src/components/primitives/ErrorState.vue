<template>
  <div class="flex flex-col items-center justify-center gap-3 py-14 text-center">
    <div class="mb-1 flex h-10 w-10 items-center justify-center rounded-full bg-[var(--color-error-bg)]">
      <AlertCircle :size="18" class="text-[var(--color-error)]" />
    </div>
    <p class="text-sm font-medium text-[var(--color-error)]">{{ message || "Something went wrong." }}</p>
    <BaseButton v-if="retryable" variant="secondary" size="sm" :icon="RefreshCw" @click="$emit('retry')"> Retry </BaseButton>
  </div>
</template>

<script>
import { AlertCircle, RefreshCw } from "@lucide/vue"
import BaseButton from "@/components/primitives/BaseButton.vue"

export default {
  name: "ErrorState",
  components: { AlertCircle, BaseButton },
  props: {
    message: {
      type: String,
      default: "",
    },
    retryable: {
      type: Boolean,
      default: true,
    },
  },
  emits: ["retry"],
  data() {
    return { RefreshCw }
  },
}
</script>
