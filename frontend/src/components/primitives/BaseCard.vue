<template>
  <section
    class="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)]"
    style="box-shadow: var(--shadow-card)"
    :class="padded ? 'p-5' : ''"
  >
    <header v-if="title" class="mb-4 flex items-center justify-between gap-2">
      <div class="flex items-center gap-2">
        <component :is="icon" v-if="icon" :size="15" class="text-[var(--color-text-tertiary)]" />
        <h2 class="label-caps">{{ title }}</h2>
      </div>
      <slot name="header-actions" />
    </header>
    <slot />
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
