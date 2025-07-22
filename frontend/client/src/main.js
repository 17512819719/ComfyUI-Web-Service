import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

// 引入 Font Awesome
import '@fortawesome/fontawesome-free/css/all.min.css'

// 引入样式
import './styles/global.css'

// 引入性能优化指令
import { lazyLoad, preload } from './directives/lazyLoad'

// 引入性能监控
import { performanceMonitor } from './utils/performance'

const app = createApp(App)

// 注册全局指令
app.directive('lazy-load', lazyLoad)
app.directive('preload', preload)

// 使用 Pinia
app.use(createPinia())
app.use(router)

// 启动性能监控
if (process.env.NODE_ENV === 'development') {
  performanceMonitor.observeLongTasks()
  performanceMonitor.observeMemory()
}

app.mount('#app')