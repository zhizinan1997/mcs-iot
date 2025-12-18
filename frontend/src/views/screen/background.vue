<template>
  <div class="screen-background-page">
    <el-card class="full-card">
      <template #header>
        <div class="card-header">
          <span>大屏背景与仪表位置配置</span>
          <el-tag type="info">拖拽仪表标记调整位置</el-tag>
        </div>
      </template>

      <el-form :model="screenBgConfig" label-width="120px" class="main-form">
        <el-form-item label="上传背景图">
          <div class="upload-area">
            <input 
              type="file" 
              ref="fileInputRef" 
              accept="image/*" 
              style="display: none" 
              @change="handleFileSelect"
            />
            <el-button type="primary" @click="triggerFileInput" :loading="uploading">
              {{ uploading ? '上传中...' : '选择图片' }}
            </el-button>
            <el-button v-if="screenBgConfig.image_url" type="danger" @click="clearScreenBg">
              清除背景
            </el-button>
          </div>
        </el-form-item>

        <el-form-item label="位置编辑器" class="editor-form-item">
          <div class="position-editor">
            <div 
              class="preview-container" 
              ref="previewRef"
              @mousedown="handleMouseDown"
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
              <div v-else class="no-bg">请先上传背景图</div>
              
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
            <div class="editor-hint">
              <el-icon><InfoFilled /></el-icon>
              点击并拖拽绿色标记调整仪表在大屏上的位置
            </div>
          </div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="saveAllConfig" :loading="saving">
            保存所有配置
          </el-button>
          <el-button @click="loadAll">
            刷新
          </el-button>
        </el-form-item>
      </el-form>

      <el-divider />
      <div class="tips">
        <h4>使用说明:</h4>
        <ul>
          <li><strong>拖拽标记</strong>调整仪表在大屏地图上的位置</li>
          <li>只有设置了<strong>大屏显示</strong>的仪表才会显示</li>
          <li>位置按百分比保存，适应任意屏幕尺寸</li>
        </ul>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from "vue";
import { ElMessage } from "element-plus";
import { InfoFilled } from "@element-plus/icons-vue";
import { configApi, uploadApi, instrumentsApi } from "../../api";

interface Instrument {
  id: number;
  name: string;
  is_displayed: boolean;
  pos_x: number;
  pos_y: number;
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

function handleMouseDown() {
  // Only start drag if clicking directly on a marker
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
.screen-background-page {
  height: 100%;
  display: flex;
  flex-direction: column;
}

:deep(.full-card) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

:deep(.full-card .el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding-bottom: 0;
}

.main-form {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.editor-form-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-bottom: 0;
  overflow: hidden;
}

:deep(.editor-form-item .el-form-item__content) {
  height: 100%;
  align-items: stretch;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.upload-area {
  display: flex;
  gap: 10px;
  align-items: center;
}

.position-editor {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.preview-container {
  position: relative;
  width: 100%;
  flex: 1;
  border: 2px solid #409eff;
  border-radius: 8px;
  background: #1a1a2e;
  overflow: hidden;
  cursor: default;
}

.preview-bg {
  width: 100%;
  height: 100%;
  object-fit: fill;
  pointer-events: none;
  user-select: none;
}

.no-bg {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #666;
  font-size: 16px;
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

.editor-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  color: #909399;
  font-size: 13px;
}

.tips {
  color: #909399;
  font-size: 14px;
}

.tips h4 {
  margin: 0 0 8px;
  color: #606266;
}

.tips ul {
  margin: 0;
  padding-left: 20px;
}

.tips li {
  margin-bottom: 4px;
}
</style>
