import { createApp } from "vue"
import { createPinia } from "pinia"

import "@fontsource-variable/inter"
import "@fontsource-variable/space-grotesk"
import "@fontsource/ibm-plex-mono/500.css"
import "@fontsource/ibm-plex-mono/600.css"
import App from "./App.vue"
import router from "./router"
import "./assets/main.css"

const savedTheme = localStorage.getItem("atlas-theme")
if (savedTheme === "dark") document.documentElement.setAttribute("data-theme", "dark")

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount("#app")
