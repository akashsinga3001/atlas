<template>
  <div class="flex items-center gap-2">
    <StatusPill :label="store.isActive ? 'Kill switch active' : 'Live'" :tone="store.isActive ? 'error' : 'positive'" :icon="store.isActive ? PauseCircle : Radio" />
    <BaseButton variant="secondary" size="sm" :icon="store.isActive ? Play : Pause" @click="showConfirm = true">
      {{ store.isActive ? "Resume" : "Pause entries" }}
    </BaseButton>

    <div v-if="showConfirm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" @click.self="showConfirm = false">
      <div class="w-full max-w-sm rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface-alt)] p-5" style="box-shadow: var(--shadow-modal)">
        <h3 class="text-sm font-semibold text-[var(--color-text-primary)]">{{ store.isActive ? "Resume new entries?" : "Pause new entries?" }}</h3>
        <p class="mt-1.5 text-xs leading-relaxed text-[var(--color-text-secondary)]">
          Existing positions' exits and trailing stops are never affected — this only pauses new entry jobs.
        </p>
        <input
          v-if="!store.isActive"
          v-model="reason"
          type="text"
          placeholder="Reason (required)"
          class="mt-3 w-full rounded-[var(--radius-sm)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2.5 py-1.5 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] focus:border-[var(--color-accent)] focus:outline-none"
        />
        <div class="mt-4 flex justify-end gap-2">
          <BaseButton variant="ghost" size="sm" @click="showConfirm = false">Cancel</BaseButton>
          <BaseButton variant="primary" size="sm" :disabled="!store.isActive && !reason.trim()" @click="confirm">Confirm</BaseButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { Pause, PauseCircle, Play, Radio } from "@lucide/vue"
import { useKillSwitchStore } from "@/stores/killSwitch"
import BaseButton from "@/components/primitives/BaseButton.vue"
import StatusPill from "@/components/primitives/StatusPill.vue"

export default {
  name: "KillSwitchPill",
  components: { BaseButton, StatusPill },
  data() {
    return {
      showConfirm: false,
      reason: "",
      Pause,
      PauseCircle,
      Play,
      Radio,
    }
  },
  computed: {
    store() {
      return useKillSwitchStore()
    },
  },
  methods: {
    async confirm() {
      if (this.store.isActive) {
        await this.store.deactivate()
      } else {
        await this.store.activate(this.reason.trim())
        this.reason = ""
      }
      this.showConfirm = false
    },
  },
}
</script>
