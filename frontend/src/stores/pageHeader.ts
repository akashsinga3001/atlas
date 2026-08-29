import { defineStore } from "pinia"

export const usePageHeaderStore = defineStore("pageHeader", {
  state: () => ({ title: "Atlas", subtitle: "" }),
  actions: {
    set(title: string, subtitle = "") {
      this.title = title
      this.subtitle = subtitle
    },
  },
})
