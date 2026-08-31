<template>
  <section
    class="animate-fade flex flex-col overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] transition-shadow duration-200 hover:shadow-[0_4px_16px_-4px_rgba(16,19,24,0.12)]"
    style="box-shadow: var(--shadow-card)"
  >
    <header v-if="title" class="flex shrink-0 items-center justify-between gap-2 px-4 pb-3 pt-4">
      <div class="flex items-center gap-1.5">
        <component :is="icon" v-if="icon" :size="14" class="text-[var(--color-text-tertiary)]" />
        <h2 class="label-caps">{{ title }}</h2>
      </div>
      <slot name="header-actions" />
    </header>
    <div class="min-h-0 flex-1 overflow-y-auto" :class="padded ? 'p-4' : ''" :style="title ? 'padding-top:0' : ''">
      <slot />
    </div>
  </section>
</template>

<script>
export default {
  name: "BaseCard",
  props: {
    title: {
      type: String,
      default: "",
    },
    icon: {
      type: [Object, Function],
      default: null,
    },
    padded: {
      type: Boolean,
      default: true,
    },
  },
}
</script>
