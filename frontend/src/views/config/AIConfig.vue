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
          description="配置 OpenAI 格式的 API 接口后，大屏将自动在每天 8:00、12:00、17:00、20:00 生成平台运行状况的智能总结。"
          show-icon
          :closable="false"
          style="margin-bottom: 20px"
        />

        <el-form :model="form" label-width="120px">
          <el-form-item label="API 接口地址">
            <el-input v-model="form.api_url" placeholder="例如: https://api.openai.com/v1" />
            <div class="form-tip">支持 OpenAI 官方接口或兼容的第三方中转接口</div>
          </el-form-item>
          
          <el-form-item label="API Key">
            <el-input 
              v-model="form.api_key" 
              type="password" 
              show-password 
              placeholder="sk-..." 
              autocomplete="new-password"
            />
          </el-form-item>
          
          <el-form-item label="模型名称">
            <el-input v-model="form.model" placeholder="gpt-3.5-turbo" />
            <div class="form-tip">例如: gpt-3.5-turbo, gpt-4, 或其它兼容模型</div>
          </el-form-item>

          <el-form-item>
            <el-button type="success" @click="goToPurchase">购买 AI API</el-button>
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

const loading = ref(false)
const testing = ref(false)
const form = reactive({
  api_url: 'https://api.openai.com/v1',
  api_key: '',
  model: 'gpt-3.5-turbo'
})

async function testConnection() {
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
        api_url: res.data.api_url || 'https://api.openai.com/v1',
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
