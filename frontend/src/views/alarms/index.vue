<template>
  <div class="alarms-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>报警记录</span>
          <div class="filter-area">
            <el-select v-model="filters.type" placeholder="报警类型" clearable @change="fetchAlarms">
              <el-option label="高报" value="HIGH" />
              <el-option label="低报" value="LOW" />
              <el-option label="离线" value="OFFLINE" />
            </el-select>
            <el-select v-model="filters.status" placeholder="状态" clearable @change="fetchAlarms">
              <el-option label="新报警" value="new" />
              <el-option label="已确认" value="ack" />
            </el-select>
          </div>
        </div>
      </template>

      <el-table :data="alarms" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="time" label="时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.time) }}
          </template>
        </el-table-column>
        <el-table-column prop="sn" label="设备编号" width="120" />
        <el-table-column prop="type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getTypeColor(row.type)">{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="value" label="报警值" width="120">
          <template #default="{ row }">
            {{ row.value?.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="threshold" label="阈值" width="120">
          <template #default="{ row }">
            {{ row.threshold?.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'new' ? 'danger' : 'success'">
              {{ row.status === 'new' ? '新报警' : '已确认' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button 
              v-if="row.status === 'new'"
              size="small" 
              type="primary" 
              @click="ackAlarm(row.id)"
            >
              确认
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        :page-size="20"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="fetchAlarms"
        class="pagination"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { alarmsApi } from '../../api'

interface Alarm {
  id: number
  time: string
  sn: string
  type: string
  value: number
  threshold: number
  status: string
  notified: boolean
}

const alarms = ref<Alarm[]>([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)

const filters = reactive({
  type: '',
  status: ''
})

async function fetchAlarms() {
  loading.value = true
  try {
    const params = {
      page: page.value,
      size: 20,
      ...(filters.type && { type: filters.type }),
      ...(filters.status && { status: filters.status })
    }
    const res = await alarmsApi.list(params)
    alarms.value = res.data.data
    total.value = res.data.total
  } catch (error) {
    ElMessage.error('获取报警记录失败')
  } finally {
    loading.value = false
  }
}

async function ackAlarm(id: number) {
  try {
    await alarmsApi.ack(id)
    ElMessage.success('已确认')
    fetchAlarms()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

function formatTime(time: string) {
  return new Date(time).toLocaleString('zh-CN')
}

function getTypeColor(type: string) {
  switch (type) {
    case 'HIGH': return 'danger'
    case 'LOW': return 'warning'
    case 'OFFLINE': return 'info'
    default: return ''
  }
}

onMounted(fetchAlarms)
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-area {
  display: flex;
  gap: 12px;
}

.pagination {
  margin-top: 20px;
  justify-content: flex-end;
}
</style>
