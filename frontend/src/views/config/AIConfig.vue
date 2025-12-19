<template>
  <div class="ai-config-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>AI 接口配置</span>
          <div>
            <el-button type="warning" @click="testConnection" :loading="testing">测试连接</el-button>
            <el-button type="primary" @click="saveConfig" :loading="loading">保存配置</el-button>
          </div>
        </div>
      </template>

      <div class="config-content">
        <el-alert
          title="AI 助手说明"
          type="info"
          description="配置 API Key 后，大屏将自动在每天 8:00、12:00、17:00、20:00 生成平台运行状况的智能总结。"
          show-icon
          :closable="false"
          style="margin-bottom: 20px"
        />

        <el-form :model="form" label-width="120px">
          <el-form-item label="API 接口地址">
            <el-input :value="fixedApiUrl" disabled />
            <div class="form-tip">接口地址已固定，无需修改</div>
          </el-form-item>
          
          <el-form-item label="API Key">
            <el-input 
              v-model="form.api_key" 
              type="password" 
              show-password 
              placeholder="sk-..." 
              autocomplete="new-password"
            />
            <div class="form-tip">请前往下方链接购买或获取 API Key</div>
          </el-form-item>
          
          <el-form-item label="模型名称">
            <el-input 
              v-model="form.model" 
              placeholder="如: gpt-3.5-turbo, gpt-4o, claude-3-5-sonnet"
            />
            <div class="form-tip">输入模型名称，如 gpt-3.5-turbo、gpt-4o、gemini-2.0-flash 等</div>
          </el-form-item>

          <el-form-item>
            <el-button type="success" size="large" @click="goToPurchase">
              <el-icon><ShoppingCart /></el-icon>
              购买 AI API Key
            </el-button>
            <span class="purchase-tip">推荐前往 Ryan AI 获取稳定高速的 API 服务</span>
          </el-form-item>
        </el-form>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { configApi } from '../../api'
import { ElMessage } from 'element-plus'
import { ShoppingCart } from '@element-plus/icons-vue'

const loading = ref(false)
const testing = ref(false)
const fixedApiUrl = 'https://newapi2.zhizinan.top/v1'

const form = reactive({
  api_key: '',
  model: 'gpt-3.5-turbo'
})

async function testConnection() {
  if (!form.api_key) {
    ElMessage.warning('请先填写 API Key')
    return
  }
  testing.value = true
  try {
    const res = await configApi.testAI(form)
    ElMessage.success('连接成功: ' + res.data.message)
  } catch (e: any) {
    console.error(e)
    ElMessage.error('连接失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    testing.value = false
  }
}

async function loadConfig() {
  loading.value = true
  try {
    const res = await configApi.getAI()
    if (res.data) {
      Object.assign(form, {
        api_key: res.data.api_key || '',
        model: res.data.model || 'gpt-3.5-turbo'
      })
    }
  } catch (e) {
    console.error('Failed to load AI config', e)
    ElMessage.error('加载配置失败')
  } finally {
    loading.value = false
  }
}

async function saveConfig() {
  loading.value = true
  try {
    await configApi.updateAI(form)
    ElMessage.success('AI 配置已保存')
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    loading.value = false
  }
}

function goToPurchase() {
  window.open('https://zhizinan.top', '_blank')
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.ai-config-container {
  max-width: 800px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.form-tip {
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
  margin-top: 4px;
}
.purchase-tip {
  margin-left: 10px;
  font-size: 12px;
  color: #67c23a;
}
</style>

