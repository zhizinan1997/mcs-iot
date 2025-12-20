<template>
  <div class="screen-bg-page full-height">
    <div class="glass-panel main-layout">
      <!-- Left Panel: Settings -->
      <div class="side-panel glass-inset-light">
        <div class="panel-header">
           <h3><el-icon><Picture /></el-icon> 背景图设置</h3>
        </div>
        
        <div class="upload-area">
          <el-upload
            class="mac-upload"
            action="#"
            :http-request="customUpload"
            :show-file-list="false"
            :before-upload="beforeUpload"
            drag
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              拖拽图片到此处或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 JPG/PNG 格式，建议分辨率 1920x1080
              </div>
            </template>
          </el-upload>
        </div>

        <div class="settings-group">
          <h4><el-icon><Location /></el-icon> 仪器点位</h4>
          <p class="hint">拖拽右侧预览图中的点位调整位置</p>
          
          <el-button class="mac-btn-block" @click="addMarker">
            <el-icon><Plus /></el-icon> 添加新点位
          </el-button>

          <div class="markers-list custom-scroll">
            <div v-for="(marker, index) in markers" :key="index" class="marker-item">
              <span class="marker-idx">{{ index + 1 }}</span>
              <el-input v-model="marker.name" placeholder="点位名称" size="small" />
              <el-button type="danger" link @click="removeMarker(index)">
                <el-icon><Close /></el-icon>
              </el-button>
            </div>
          </div>
        </div>
        
        <div class="panel-footer">
          <el-button type="primary" size="large" round class="save-btn" @click="saveConfig" :loading="saving">
            保存布局配置
          </el-button>
        </div>
      </div>

      <!-- Right Panel: Editor -->
      <div class="editor-panel">
         <div class="editor-wrapper glass-inset-dark">
            <div 
              class="preview-container" 
              ref="previewRef"
              :style="{ backgroundImage: `url(${bgUrl})` }"
              @drop="handleDrop"
              @dragover.prevent
            >
               <div 
                 v-for="(marker, index) in markers" 
                 :key="index"
                 class="marker"
                 :style="{ left: marker.x + '%', top: marker.y + '%' }"
                 @mousedown="startDrag($event, index)"
               >
                 <div class="dot"></div>
                 <div class="label">{{ marker.name || `点位 ${index+1}` }}</div>
               </div>
               
               <div v-if="!bgUrl" class="empty-bg">
                 <el-icon :size="48"><Picture /></el-icon>
                 <span>请先上传背景图片</span>
               </div>
            </div>
         </div>
         <div class="editor-toolbar">
           <span>画布操作提示：直接拖动点位即可调整位置，右键可删除。</span>
           <el-button link type="primary" @click="loadConfig"><el-icon><Refresh /></el-icon> 重置</el-button>
         </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Picture, UploadFilled, Location, Plus, Close, Refresh } from '@element-plus/icons-vue'
import { configApi, uploadApi } from '../../api'

const bgUrl = ref('')
const markers = ref<any[]>([])
const saving = ref(false)
const previewRef = ref<HTMLElement | null>(null)

// Drag state
let isDragging = false
let currentMarkerIndex = -1

async function customUpload(options: any) {
  try {
    const res = await uploadApi.uploadImage(options.file)
    handleUploadSuccess(res.data)
  } catch (error) {
    ElMessage.error('上传失败')
    options.onError(error)
  }
}

function handleUploadSuccess(res: any) {
  bgUrl.value = res.url
  ElMessage.success('背景图上传成功')
}

function beforeUpload(file: any) {
  const isImg = file.type.startsWith('image/')
  if (!isImg) ElMessage.error('只能上传图片文件')
  return isImg
}

function addMarker() {
  markers.value.push({
    x: 50,
    y: 50,
    name: `新点位 ${markers.value.length + 1}`
  })
}

function removeMarker(index: number) {
  markers.value.splice(index, 1)
}

// Drag Logic
function startDrag(e: MouseEvent, index: number) {
  isDragging = true
  currentMarkerIndex = index
  e.preventDefault()
  
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

function onMouseMove(e: MouseEvent) {
  if (!isDragging || !previewRef.value) return
  
  const rect = previewRef.value.getBoundingClientRect()
  let x = ((e.clientX - rect.left) / rect.width) * 100
  let y = ((e.clientY - rect.top) / rect.height) * 100
  
  // Clamp
  x = Math.max(0, Math.min(100, x))
  y = Math.max(0, Math.min(100, y))
  
  if (currentMarkerIndex !== -1) {
    markers.value[currentMarkerIndex].x = x
    markers.value[currentMarkerIndex].y = y
  }
}

function onMouseUp() {
  isDragging = false
  currentMarkerIndex = -1
  document.removeEventListener('mousemove', onMouseMove)
  document.removeEventListener('mouseup', onMouseUp)
}

function handleDrop() {
  // Optional: handle drop specific logic
}

async function loadConfig() {
  try {
    const res = await configApi.getScreenBg()
    if (res.data) {
      bgUrl.value = res.data.background_url || ''
      markers.value = res.data.markers || []
    }
  } catch (err) {
    console.error(err)
  }
}

async function saveConfig() {
  saving.value = true
  try {
    await configApi.updateScreenBg({
      background_url: bgUrl.value,
      markers: markers.value
    })
    ElMessage.success('布局配置已保存')
  } catch (err) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadConfig()
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
.mac-upload {
  margin-bottom: 24px;
}
:deep(.el-upload-dragger) {
  background: rgba(255, 255, 255, 0.5);
  border-radius: 12px;
  border: 1px dashed #dcdfe6;
}
:deep(.el-upload-dragger:hover) {
  border-color: #0071e3;
  background: rgba(0, 113, 227, 0.05);
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

.mac-btn-block {
  width: 100%;
  margin-bottom: 16px;
  border-radius: 8px;
  border-style: dashed;
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
  padding: 8px;
  border-radius: 8px;
}

.marker-idx {
  width: 20px;
  height: 20px;
  background: #0071e3;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
}

.panel-footer {
  margin-top: 24px;
  text-align: center;
}
.save-btn {
  width: 100%;
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
  background: #1e1e1e;
  border-radius: 16px;
  box-shadow: inset 0 2px 8px rgba(0,0,0,0.2);
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.preview-container {
  width: 100%;
  height: 100%;
  background-size: contain;
  background-repeat: no-repeat;
  background-position: center;
  position: relative;
  border: 1px solid rgba(255,255,255,0.1);
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
}
.marker:active {
  cursor: grabbing;
}

.dot {
  width: 16px;
  height: 16px;
  background: radial-gradient(circle, #4ade80 0%, #22c55e 40%, rgba(34,197,94,0.4) 80%);
  border-radius: 50%;
  box-shadow: 0 0 12px #4ade80, 0 0 24px #22c55e;
  border: 2px solid #fff;
}

.label {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0,0,0,0.7);
  color: white;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  white-space: nowrap;
  pointer-events: none;
}

.editor-toolbar {
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 8px;
  font-size: 13px;
  color: #606266;
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
