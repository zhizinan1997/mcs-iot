<!--
  MCS-IOT 报警记录页面 (Alarm History & Management)

  该文件负责展示并管理系统中产生的所有报警日志。
  主要功能：
  1. 报警列表：分页展示报警时间、关联仪表、设备 SN、名称、类型、数值及状态。
  2. 智能筛选：支持按报警类型（高/低浓度、电量、信号等）及处理状态（新报警/已确认）进行过滤。
  3. 响应式操作：提供单条确认及一键确认所有报警的功能，同步更新后台计数。
  4. 动态渲染：基于报警严重程度自动匹配标签颜色，确保视觉预警效果。

  技术栈：Vue 3 (setup), Element Plus Table, Pagination & Select.
-->
<template>
  <div class="alarms-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <div class="filter-area">
            <el-button type="danger" @click="ackAllAlarms">确认所有报警</el-button>
            <el-select v-model="filters.type" placeholder="报警类型" clearable @change="fetchAlarms">
              <el-option label="高浓度" value="HIGH" />
              <el-option label="低浓度" value="LOW" />
              <el-option label="低电量" value="LOW_BAT" />
              <el-option label="信号弱" value="WEAK_SIGNAL" />
              <el-option label="离线" value="OFFLINE" />
            </el-select>
            <el-select v-model="filters.status" placeholder="状态" clearable @change="fetchAlarms">
              <el-option label="新报警" value="active" />
              <el-option label="已确认" value="ack" />
            </el-select>
          </div>
        </div>
      </template>

      <el-table :data="alarms" stripe v-loading="loading" @sort-change="handleSortChange">
        <el-table-column prop="id" label="ID" width="80" sortable="custom" />
        <el-table-column prop="time" label="时间" width="180" sortable="custom">
          <template #default="{ row }">
            {{ formatTime(row.time) }}
          </template>
        </el-table-column>
        <el-table-column prop="instrument_name" label="仪表" min-width="120" sortable="custom">
          <template #default="{ row }">
            <span v-if="row.instrument_name" class="instrument-cell">
              <span class="color-dot" :style="{ backgroundColor: row.instrument_color || '#409eff' }"></span>
              {{ row.instrument_name }}
            </span>
            <span v-else style="color: #999">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="sn" label="设备编号" width="120" sortable="custom" />
        <el-table-column prop="device_name" label="设备名称" min-width="120" sortable="custom">
          <template #default="{ row }">
            {{ row.device_name || row.sn }}
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="100" sortable="custom">
          <template #default="{ row }">
            <el-tag :type="getTypeColor(row.type)">{{ getTypeName(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="value" label="报警值" width="120" sortable="custom">
          <template #default="{ row }">
            {{ row.value?.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="threshold" label="阈值" width="120" sortable="custom">
          <template #default="{ row }">
            {{ row.threshold?.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" sortable="custom">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'danger' : 'success'">
              {{ row.status === 'active' ? '新报警' : '已确认' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button 
              v-if="row.status === 'active'"
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
  device_name: string
  instrument_name: string | null
  instrument_color: string | null
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

async function ackAllAlarms() {
  try {
    await alarmsApi.ackAll()
    ElMessage.success(`已确认所有报警`)
    fetchAlarms()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

function formatTime(time: string) {
  // 数据库已存储北京时间，直接格式化即可
  const date = new Date(time)
  return date.toLocaleString('zh-CN')
}

function getTypeName(type: string) {
  const typeMap: Record<string, string> = {
    'HIGH': '高浓度',
    'LOW': '低浓度',
    'LOW_BAT': '低电量',
    'WEAK_SIGNAL': '信号弱',
    'OFFLINE': '离线'
  }
  return typeMap[type] || type
}

function getTypeColor(type: string) {
  switch (type) {
    case 'HIGH': return 'danger'
    case 'LOW': return 'warning'
    case 'LOW_BAT': return 'warning'
    case 'WEAK_SIGNAL': return 'info'
    case 'OFFLINE': return 'info'
    default: return ''
  }
}

function handleSortChange({ prop, order }: { prop: string; order: string | null }) {
  if (!order) {
    fetchAlarms();
    return;
  }
  
  const direction = order === 'ascending' ? 1 : -1;
  alarms.value = [...alarms.value].sort((a: any, b: any) => {
    let aVal = a[prop];
    let bVal = b[prop];
    
    if (aVal == null) aVal = '';
    if (bVal == null) bVal = '';
    
    if (typeof aVal === 'number' && typeof bVal === 'number') {
      return (aVal - bVal) * direction;
    }
    
    return String(aVal).localeCompare(String(bVal)) * direction;
  });
}

onMounted(fetchAlarms)
</script>

<style scoped>
/* Global Styles */
.alarms-page {
  height: 100%;
  padding: 24px;
}

/* Glass Card */
:deep(.el-card) {
  height: 100%;
  border-radius: 24px !important;
  border: 1px solid rgba(255, 255, 255, 0.6) !important;
  background: rgba(255, 255, 255, 0.65) !important;
  backdrop-filter: blur(20px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.04) !important;
  display: flex;
  flex-direction: column;
}

:deep(.el-card__header) {
  padding: 20px 32px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  background: transparent;
}

:deep(.el-card__body) {
  padding: 0;
  height: calc(100% - 73px); /* Adjusted for header height */
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.card-header {
  display: flex;
  justify-content: flex-end;
  align-items: center;
}

.card-header span {
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
}

.filter-area {
  display: flex;
  gap: 12px;
}

/* Global rounded button for filter area */
:deep(.el-button) {
  border-radius: 14px;
  font-weight: 500;
}

:deep(.el-select .el-select__wrapper) {
  border-radius: 10px;
}

/* Glass Table Styling */
:deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(255, 255, 255, 0.5);
  background: transparent !important;
  border-radius: 0;
}

:deep(.el-table th.el-table__cell) {
  background-color: rgba(255, 255, 255, 0.5);
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  color: #86868b;
  font-weight: 600;
  font-size: 13px;
  padding: 12px 0;
}

:deep(.el-table td.el-table__cell) {
  border-bottom: 1px solid rgba(0, 0, 0, 0.03);
  padding: 16px 0;
}

:deep(.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell) {
  background: rgba(255, 255, 255, 0.2);
}

:deep(.el-table--enable-row-hover .el-table__body tr:hover > td.el-table__cell) {
  background-color: rgba(255, 255, 255, 0.5);
}

/* Tags rounded */
:deep(.el-tag) {
  border-radius: 6px;
  font-weight: 500;
  border: none;
}

.pagination {
  margin-top: 24px;
  justify-content: flex-end;
}

:deep(.el-pagination button),
:deep(.el-pager li) {
  border-radius: 8px !important;
}

.instrument-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.color-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
</style>
