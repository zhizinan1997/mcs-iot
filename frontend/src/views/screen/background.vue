<template>
  <div class="screen-bg-page full-height">
    <div class="glass-panel main-layout">
      <!-- Left Panel: Settings -->
      <div class="side-panel">
        <div class="panel-header">
           <h3><el-icon><Picture /></el-icon> 背景图设置</h3>
        </div>
        
        <div class="upload-area">
          <el-button @click="triggerFileInput" :loading="uploading">
            <el-icon><UploadFilled /></el-icon> 上传背景
          </el-button>
          <el-button @click="clearScreenBg" :disabled="!screenBgConfig.image_url">
            <el-icon><Delete /></el-icon> 清除
          </el-button>
          <input
            ref="fileInputRef"
            type="file"
            accept="image/*"
            style="display: none"
            @change="handleFileSelect"
          />
        </div>

        <el-divider />

        <div class="settings-group">
          <h4><el-icon><Location /></el-icon> 仪器点位</h4>
          <p class="hint">拖拽右侧预览图中的绿点调整仪器位置</p>
          
          <div class="markers-list custom-scroll">
            <div v-for="inst in displayedInstruments" :key="inst.id" class="marker-item">
              <span class="marker-idx">{{ inst.id }}</span>
              <span class="marker-name">{{ inst.name }}</span>
              <span class="marker-pos">({{ inst.pos_x.toFixed(1) }}%, {{ inst.pos_y.toFixed(1) }}%)</span>
            </div>
            <div v-if="displayedInstruments.length === 0" class="no-markers">
              暂无设置为"大屏显示"的仪器
            </div>
          </div>
        </div>
        
        <div class="panel-footer">
          <el-button type="primary" size="large" round class="save-btn" @click="saveAllConfig" :loading="saving">
            保存所有配置
          </el-button>
          <el-button size="large" round @click="loadAll">
            刷新
          </el-button>
        </div>
      </div>

      <!-- Right Panel: Editor -->
      <div class="editor-panel">
         <div class="editor-wrapper glass-inset-dark">
            <div 
              class="preview-container" 
              ref="previewRef"
              @mousemove="handleMouseMove"
              @mouseup="handleMouseUp"
              @mouseleave="handleMouseUp"
            >
               <img
                 v-if="screenBgConfig.image_url"
                 :src="screenBgConfig.image_url"
                 alt="背景预览"
                 class="preview-bg"
                 draggable="false"
               />
               <div v-else class="empty-bg">
                 <el-icon :size="48"><Picture /></el-icon>
                 <span>请先上传背景图片</span>
               </div>

               <!-- Instrument markers -->
               <div
                 v-for="inst in displayedInstruments"
                 :key="inst.id"
                 class="marker"
                 :class="{ dragging: draggingId === inst.id }"
                 :style="{ left: inst.pos_x + '%', top: inst.pos_y + '%' }"
                 @mousedown.stop="startDrag($event, inst)"
               >
                 <span class="dot"></span>
                 <span class="label">{{ inst.name }}</span>
               </div>
            </div>
         </div>
         <div class="editor-toolbar">
           <span><el-icon><InfoFilled /></el-icon> 点击并拖拽绿色标记调整仪表在大屏上的位置</span>
         </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Picture, UploadFilled, Location, Delete, InfoFilled } from '@element-plus/icons-vue'
import { configApi, uploadApi, instrumentsApi } from '../../api'

interface Instrument {
  id: number
  name: string
  is_displayed: boolean
  pos_x: number
  pos_y: number
}

const saving = ref(false)
const uploading = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const previewRef = ref<HTMLDivElement | null>(null)

const screenBgConfig = reactive({
  image_url: ""
})

const instruments = ref<Instrument[]>([])
const draggingId = ref<number | null>(null)
const dragOffset = reactive({ x: 0, y: 0 })

const displayedInstruments = computed(() => {
  return instruments.value.filter(i => i.is_displayed === true)
})

function triggerFileInput() {
  fileInputRef.value?.click()
}

async function loadScreenBgConfig() {
  try {
    const res = await configApi.getScreenBg()
    screenBgConfig.image_url = res.data.image_url || ""
  } catch (error) {
    console.error("Failed to load screen bg config:", error)
  }
}

async function loadInstruments() {
  try {
    const res = await instrumentsApi.list()
    instruments.value = res.data.data.map((i: any) => ({
      id: i.id,
      name: i.name,
      is_displayed: i.is_displayed,
      pos_x: i.pos_x ?? 50,
      pos_y: i.pos_y ?? 50
    }))
  } catch (error) {
    console.error("Failed to load instruments:", error)
  }
}

async function loadAll() {
  await Promise.all([loadScreenBgConfig(), loadInstruments()])
}

async function saveScreenBgConfig() {
  await configApi.updateScreenBg(screenBgConfig)
}

async function saveInstrumentPositions() {
  const promises = displayedInstruments.value.map(inst =>
    instrumentsApi.updatePosition(inst.id, inst.pos_x, inst.pos_y)
  )
  await Promise.all(promises)
}

async function saveAllConfig() {
  saving.value = true
  try {
    await Promise.all([saveScreenBgConfig(), saveInstrumentPositions()])
    ElMessage.success("配置已保存")
  } catch (error: any) {
    ElMessage.error("保存失败")
  } finally {
    saving.value = false
  }
}

async function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  uploading.value = true
  try {
    const res = await uploadApi.uploadImage(file)
    screenBgConfig.image_url = res.data.url
    ElMessage.success("图片上传成功")
  } catch (error: any) {
    const detail = error.response?.data?.detail || "上传失败"
    ElMessage.error(detail)
  } finally {
    uploading.value = false
    if (target) target.value = ""
  }
}

function clearScreenBg() {
  screenBgConfig.image_url = ""
}

// Drag and drop handlers
function startDrag(event: MouseEvent, inst: Instrument) {
  draggingId.value = inst.id
  const rect = previewRef.value?.getBoundingClientRect()
  if (rect) {
    const currentX = (inst.pos_x / 100) * rect.width
    const currentY = (inst.pos_y / 100) * rect.height
    dragOffset.x = event.clientX - rect.left - currentX
    dragOffset.y = event.clientY - rect.top - currentY
  }
}

function handleMouseMove(event: MouseEvent) {
  if (draggingId.value === null) return

  const rect = previewRef.value?.getBoundingClientRect()
  if (!rect) return

  const x = event.clientX - rect.left - dragOffset.x
  const y = event.clientY - rect.top - dragOffset.y

  const posX = Math.max(0, Math.min(100, (x / rect.width) * 100))
  const posY = Math.max(0, Math.min(100, (y / rect.height) * 100))

  const inst = instruments.value.find(i => i.id === draggingId.value)
  if (inst) {
    inst.pos_x = Math.round(posX * 10) / 10
    inst.pos_y = Math.round(posY * 10) / 10
  }
}

function handleMouseUp() {
  draggingId.value = null
}

onMounted(() => {
  loadAll()
})
</script>

<style scoped>
.screen-bg-page {
  padding: 24px;
  height: 100%;
  box-sizing: border-box;
}

.full-height {
  height: 100%;
}

.glass-panel {
  height: 100%;
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.6);
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(20px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.04);
  display: flex;
  overflow: hidden;
}

.main-layout {
  display: flex;
}

/* Left Panel */
.side-panel {
  width: 320px;
  flex-shrink: 0;
  border-right: 1px solid rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
  padding: 24px;
  background: rgba(255,255,255,0.4);
}

.panel-header h3 {
  margin: 0 0 24px;
  font-size: 18px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #1d1d1f;
}

/* Upload */
.upload-area {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 16px;
}

/* Settings Group */
.settings-group {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.settings-group h4 {
  margin: 0 0 8px;
  font-size: 15px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.hint {
  font-size: 12px;
  color: #86868b;
  margin: 0 0 16px;
}

.markers-list {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}

.marker-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  background: rgba(255,255,255,0.5);
  padding: 8px 12px;
  border-radius: 8px;
}

.marker-idx {
  width: 24px;
  height: 24px;
  background: #0071e3;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
}

.marker-name {
  flex: 1;
  font-size: 14px;
  color: #1d1d1f;
}

.marker-pos {
  font-size: 11px;
  color: #86868b;
  font-family: monospace;
}

.no-markers {
  color: #86868b;
  font-size: 13px;
  text-align: center;
  padding: 20px;
}

.panel-footer {
  margin-top: 24px;
  display: flex;
  gap: 12px;
}
.save-btn {
  flex: 1;
  font-weight: 600;
}

/* Right Panel */
.editor-panel {
  flex: 1;
  padding: 24px;
  display: flex;
  flex-direction: column;
  background: rgba(255,255,255,0.2);
}

.editor-wrapper {
  flex: 1;
  background: #1a1a2e;
  border-radius: 16px;
  box-shadow: inset 0 2px 8px rgba(0,0,0,0.2);
  overflow: hidden;
}

.preview-container {
  width: 100%;
  height: 100%;
  position: relative;
  cursor: default;
}

.preview-bg {
  width: 100%;
  height: 100%;
  object-fit: contain;
  pointer-events: none;
  user-select: none;
}

.empty-bg {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: rgba(255,255,255,0.2);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.marker {
  position: absolute;
  transform: translate(-50%, -50%);
  cursor: grab;
  z-index: 10;
  transition: transform 0.1s ease;
}

.marker:hover {
  transform: translate(-50%, -50%) scale(1.2);
}

.marker.dragging {
  cursor: grabbing;
  transform: translate(-50%, -50%) scale(1.3);
  z-index: 20;
}

.marker .dot {
  display: block;
  width: 16px;
  height: 16px;
  background: radial-gradient(circle, #4ade80 0%, #22c55e 40%, rgba(34,197,94,0.4) 80%);
  border-radius: 50%;
  box-shadow: 0 0 12px #4ade80, 0 0 24px #22c55e;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 0.9; }
  50% { transform: scale(1.3); opacity: 1; }
}

.marker .label {
  position: absolute;
  top: -22px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 11px;
  white-space: nowrap;
  background: rgba(0,0,0,0.8);
  color: #fff;
  padding: 2px 6px;
  border-radius: 3px;
  pointer-events: none;
}

.editor-toolbar {
  height: 40px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  font-size: 13px;
  color: #606266;
  gap: 6px;
}

/* Scrollbar */
.custom-scroll::-webkit-scrollbar {
  width: 6px;
}
.custom-scroll::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 3px;
}
</style>
