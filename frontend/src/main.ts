import { createApp } from "vue"
import { createPinia } from "pinia"

import "@fontsource-variable/inter"
import "@fontsource/ibm-plex-mono/400.css"
import "@fontsource/ibm-plex-mono/500.css"
import "@fontsource/ibm-plex-mono/600.css"
import "@fontsource/ibm-plex-mono/700.css"
import App from "./App.vue"
import router from "./router"
import "./assets/main.css"

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount("#app")
