/**
 * MCS-IOT 前端应用入口 (App Entry Point)
 * 
 * 该文件负责初始化 Vue 3 实例并挂载全局插件。
 * 主要职责：
 * 1. 挂载 Pinia 状态管理仓库。
 * 2. 配置 Vue Router 路由系统。
 * 3. 引入 Element Plus 组件库及其图标集并进行全局注册。
 * 4. 引入全局样式文件 (CSS/SCSS)。
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'
import './style.css'

const app = createApp(App)
const pinia = createPinia()

// Register all Element Plus icons
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
}

app.use(pinia)
app.use(router)
app.use(ElementPlus)
app.mount('#app')
