<template>
  <div class="devices-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>设备管理</span>
          <el-button type="primary" @click="showAddDialog">
            <el-icon><Plus /></el-icon> 添加设备
          </el-button>
        </div>
      </template>

      <el-table :data="devices" stripe v-loading="loading">
        <el-table-column prop="sn" label="设备编号" width="150" />
        <el-table-column prop="name" label="设备名称" />
        <el-table-column prop="model" label="型号" width="100" />
        <el-table-column label="校准参数" width="180">
          <template #default="{ row }">
            <span>K={{ row.k_val }} B={{ row.b_val }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="high_limit" label="报警阈值" width="100" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'online' ? 'success' : 'info'">
              {{ row.status === 'online' ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="editDevice(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteDevice(row.sn)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        :page-size="20"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="fetchDevices"
        class="pagination"
      />
    </el-card>

    <!-- Add/Edit Dialog -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑设备' : '添加设备'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="设备编号" required>
          <el-input v-model="form.sn" :disabled="isEdit" placeholder="如: A001" />
        </el-form-item>
        <el-form-item label="设备名称">
          <el-input v-model="form.name" placeholder="如: 1号检测点" />
        </el-form-item>
        <el-form-item label="设备型号">
          <el-input v-model="form.model" placeholder="如: MCS-100" />
        </el-form-item>
        <el-divider>校准参数</el-divider>
        <el-form-item label="K值 (斜率)">
          <el-input-number v-model="form.k_val" :precision="4" :step="0.1" />
        </el-form-item>
        <el-form-item label="B值 (截距)">
          <el-input-number v-model="form.b_val" :precision="4" :step="0.1" />
        </el-form-item>
        <el-form-item label="温补系数">
          <el-input-number v-model="form.t_coef" :precision="4" :step="0.01" />
        </el-form-item>
        <el-divider>报警阈值</el-divider>
        <el-form-item label="高报阈值">
          <el-input-number v-model="form.high_limit" :min="0" />
        </el-form-item>
        <el-form-item label="低报阈值">
          <el-input-number v-model="form.low_limit" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveDevice" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { devicesApi } from '../../api'

interface Device {
  sn: string
  name: string
  model: string
  k_val: number
  b_val: number
  t_coef: number
  high_limit: number
  low_limit: number | null
  status: string
}

const devices = ref<Device[]>([])
const loading = ref(false)
const saving = ref(false)
const page = ref(1)
const total = ref(0)

const dialogVisible = ref(false)
const isEdit = ref(false)

const form = reactive({
  sn: '',
  name: '',
  model: '',
  k_val: 1.0,
  b_val: 0.0,
  t_coef: 0.0,
  high_limit: 1000,
  low_limit: null as number | null
})

async function fetchDevices() {
  loading.value = true
  try {
    const res = await devicesApi.list(page.value)
    devices.value = res.data.data
    total.value = res.data.total
  } catch (error) {
    ElMessage.error('获取设备列表失败')
  } finally {
    loading.value = false
  }
}

function showAddDialog() {
  isEdit.value = false
  Object.assign(form, {
    sn: '', name: '', model: '',
    k_val: 1.0, b_val: 0.0, t_coef: 0.0,
    high_limit: 1000, low_limit: null
  })
  dialogVisible.value = true
}

function editDevice(device: Device) {
  isEdit.value = true
  Object.assign(form, device)
  dialogVisible.value = true
}

async function saveDevice() {
  saving.value = true
  try {
    if (isEdit.value) {
      await devicesApi.update(form.sn, form)
      ElMessage.success('设备更新成功')
    } else {
      await devicesApi.create(form)
      ElMessage.success('设备添加成功')
    }
    dialogVisible.value = false
    fetchDevices()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

async function deleteDevice(sn: string) {
  try {
    await ElMessageBox.confirm('确定删除该设备吗？', '确认删除', { type: 'warning' })
    await devicesApi.delete(sn)
    ElMessage.success('设备已删除')
    fetchDevices()
  } catch {}
}

onMounted(fetchDevices)
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination {
  margin-top: 20px;
  justify-content: flex-end;
}
</style>
