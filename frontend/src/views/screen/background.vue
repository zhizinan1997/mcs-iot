<template>
  <div class="screen-background-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>传感器地图背景图配置</span>
          <el-tag type="info">支持 JPG/PNG/SVG</el-tag>
        </div>
      </template>

      <el-form :model="screenBgConfig" label-width="120px">
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

        <el-form-item label="当前背景" v-if="screenBgConfig.image_url">
          <div class="bg-preview">
            <img :src="screenBgConfig.image_url" alt="背景预览" />
          </div>
        </el-form-item>

        <el-form-item>
          <el-button 
            type="primary" 
            @click="saveScreenBgConfig" 
            :loading="saving"
          >保存配置</el-button>
        </el-form-item>
      </el-form>

      <el-divider />
      <div class="tips">
        <h4>使用说明:</h4>
        <ul>
          <li><strong>图片将被拉伸</strong>以填满整个传感器位置地图区域</li>
          <li>推荐使用工厂平面图或设备布局图作为背景</li>
          <li>建议图片尺寸: 1920x1080 或更高分辨率</li>
        </ul>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { configApi, uploadApi } from "../../api";

const saving = ref(false)
const uploading = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)

const screenBgConfig = reactive({
  image_url: ""
})

function triggerFileInput() {
  fileInputRef.value?.click()
}

async function loadScreenBgConfig() {
  try {
    const res = await configApi.getScreenBg()
    Object.assign(screenBgConfig, res.data)
  } catch (error) {
    console.error("Failed to load screen bg config:", error)
  }
}

async function saveScreenBgConfig() {
  saving.value = true
  try {
    await configApi.updateScreenBg(screenBgConfig)
    ElMessage.success("大屏背景配置已保存")
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

onMounted(() => {
  loadScreenBgConfig()
})
</script>

<style scoped>
.screen-background-page {
  max-width: 800px;
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

.bg-preview {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 10px;
  background: #f5f7fa;
}

.bg-preview img {
  max-width: 400px;
  max-height: 225px;
  display: block;
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
