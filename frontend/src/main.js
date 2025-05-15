import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import store from './store'

console.log("🔧 API 주소:", process.env.VUE_APP_API_URL)  // ✅ 수정

const app = createApp(App)

app.use(router)
app.use(store)

app.mount('#app')
