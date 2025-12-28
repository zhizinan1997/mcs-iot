<!--
  MCS-IOT 管理大屏 (Management Dashboard)

  该文件是系统的主控台视图，提供全局状态概览及详细设备列表。
  主要功能：
  1. 统计看板：实时显示设备在线情况、告警数量等核心指标。
  2. 交互式设备列表：支持多维排序（SN、名称、浓度、电量等）及实时刷新。
  3. 历史回溯：集成 ECharts 插件，以图表形式展示特定传感器的浓度、温湿度历史趋势。
  4. 报警联动：在列表中直观展示触发报警的传感器状态及详情入口。

  技术栈：Vue 3 (Composition API), Element Plus, ECharts, SCSS.
-->
<template>
  <div class="dashboard">
    <!-- Stats Cards -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon blue"><el-icon><Monitor /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.devices_total }}</div>
            <div class="stat-label">传感器总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon green"><el-icon><CircleCheck /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.devices_online }}</div>
            <div class="stat-label">在线传感器</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon gray"><el-icon><CircleClose /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.devices_offline }}</div>
            <div class="stat-label">离线传感器</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon red"><el-icon><Bell /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.alarms_today }}</div>
            <div class="stat-label">今日报警</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Device List -->
    <el-card class="device-card">
      <template #header>
        <div class="card-header">
          <span>实时传感器状态</span>
          <el-button type="primary" size="small" @click="fetchData">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>
      </template>
      
      <el-table :data="sortedDevices" stripe @sort-change="handleSortChange">
        <el-table-column prop="instrument_name" label="仪表" min-width="120" sortable="custom">
          <template #default="{ row }">
            <span v-if="row.instrument_name" class="instrument-cell">
              <span class="color-dot" :style="{ backgroundColor: row.instrument_color || '#409eff' }"></span>
              {{ row.instrument_name }}
            </span>
            <span v-else style="color: #999">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="sn" label="传感器编号" min-width="100" sortable="custom" />
        <el-table-column prop="name" label="传感器名称" min-width="100" sortable="custom" />
        <el-table-column prop="ppm" label="监测值" min-width="120" sortable="custom">
          <template #default="{ row }">
            <span :class="{ 'alarm-value': row.ppm > 1000 }">
              {{ row.ppm?.toFixed(2) }} {{ row.unit || 'ppm' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="temp" label="温度 (°C)" min-width="90" sortable="custom">
          <template #default="{ row }">
            {{ row.temp?.toFixed(1) || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="battery" label="电池" min-width="70" align="center" sortable="custom">
          <template #default="{ row }">
            <span v-if="row.battery != null" :style="{ color: row.battery < 20 ? '#F56C6C' : row.battery < 50 ? '#E6A23C' : '#67C23A' }">
              {{ row.battery }}%
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="rssi" label="信号" min-width="85" align="center" sortable="custom">
          <template #default="{ row }">
            <span v-if="row.rssi != null" :style="{ color: row.rssi < -80 ? '#F56C6C' : row.rssi < -70 ? '#E6A23C' : '#67C23A' }">
              {{ row.rssi }}dBm
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="network" label="网络" min-width="70" align="center" sortable="custom">
          <template #default="{ row }">
            {{ row.network || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" min-width="80" align="center" sortable="custom">
          <template #default="{ row }">
            <el-tag :type="row.status === 'online' ? 'success' : 'info'" size="small">
              {{ row.status === 'online' ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="70" align="center" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="showHistory(row)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- History Chart Dialog -->
    <el-dialog 
      v-model="historyDialogVisible" 
      :title="`${selectedDevice?.name || selectedDevice?.sn} - 历史数据`"
      width="900px"
      class="history-dialog"
    >
      <div class="time-selector">
        <el-radio-group v-model="selectedHours" @change="loadHistory">
          <el-radio-button :value="1">1小时</el-radio-button>
          <el-radio-button :value="3">3小时</el-radio-button>
          <el-radio-button :value="24">1天</el-radio-button>
          <el-radio-button :value="72">3天</el-radio-button>
        </el-radio-group>
      </div>
      
      <div v-loading="historyLoading" class="charts-container">
        <div v-if="historyData.points.length === 0 && !historyLoading" class="no-data">
          <el-empty description="暂无数据" />
        </div>
        <template v-else>
          <!-- PPM Chart -->
          <div class="chart-card">
            <h4>📈 浓度 (PPM)</h4>
            <v-chart :option="ppmChartOption" autoresize style="height: 200px" />
          </div>
          
          <!-- Temperature Chart -->
          <div class="chart-card">
            <h4>🌡️ 温度 (°C)</h4>
            <v-chart :option="tempChartOption" autoresize style="height: 200px" />
          </div>
          
          <!-- Humidity Chart -->
          <div class="chart-card">
            <h4>💧 湿度 (%)</h4>
            <v-chart :option="humiChartOption" autoresize style="height: 200px" />
          </div>
        </template>
      </div>
      
      <!-- Alarms List -->
      <div v-if="historyData.alarms.length > 0" class="alarms-section">
        <h4>⚠️ 报警记录 ({{ historyData.alarms.length }})</h4>
        <el-timeline>
          <el-timeline-item 
            v-for="alarm in historyData.alarms" 
            :key="alarm.ts"
            :timestamp="formatTime(alarm.ts)"
            type="danger"
          >
            {{ alarm.type }}: {{ alarm.value }}
          </el-timeline-item>
        </el-timeline>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { dashboardApi, devicesApi } from '../../api'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

interface Stats {
  devices_total: number
  devices_online: number
  devices_offline: number
  devices_alarm: number
  alarms_today: number
}

interface Device {
  sn: string
  name: string
  ppm: number | null
  temp: number | null
  status: string
  battery: number | null
  rssi: number | null
  network: string | null
  instrument_name: string | null
  instrument_color: string | null
  unit: string
}

interface HistoryPoint {
  ts: string
  ppm: number | null
  temp: number | null
  humi: number | null
}

interface AlarmRecord {
  ts: string
  type: string
  value: number
}

const stats = ref<Stats>({
  devices_total: 0,
  devices_online: 0,
  devices_offline: 0,
  devices_alarm: 0,
  alarms_today: 0
})

const devices = ref<Device[]>([])

// Current sort state
const currentSort = ref<{ prop: string; order: string | null }>({ prop: 'sn', order: 'ascending' })

// Sorted devices
const sortedDevices = computed(() => {
  const { prop, order } = currentSort.value
  if (!order) return [...devices.value].sort((a, b) => (a.instrument_name || '').localeCompare(b.instrument_name || '') || a.sn.localeCompare(b.sn))
  
  const direction = order === 'ascending' ? 1 : -1
  return [...devices.value].sort((a: any, b: any) => {
    let aVal = a[prop]
    let bVal = b[prop]
    
    if (aVal == null) aVal = ''
    if (bVal == null) bVal = ''
    
    if (typeof aVal === 'number' && typeof bVal === 'number') {
      return (aVal - bVal) * direction
    }
    
    return String(aVal).localeCompare(String(bVal)) * direction
  })
})

function handleSortChange({ prop, order }: { prop: string; order: string | null }) {
  currentSort.value = { prop: prop || 'sn', order }
}

// History dialog state
const historyDialogVisible = ref(false)
const selectedDevice = ref<Device | null>(null)
const selectedHours = ref(1)
const historyLoading = ref(false)
const historyData = ref<{ points: HistoryPoint[], alarms: AlarmRecord[] }>({ points: [], alarms: [] })

async function fetchData() {
  try {
    const [statsRes, devicesRes] = await Promise.all([
      dashboardApi.stats(),
      dashboardApi.realtime()
    ])
    stats.value = statsRes.data
    devices.value = devicesRes.data
  } catch (error) {
    console.error('Failed to fetch dashboard data:', error)
  }
}

async function showHistory(device: Device) {
  selectedDevice.value = device
  historyDialogVisible.value = true
  await loadHistory()
}

async function loadHistory() {
  if (!selectedDevice.value) return
  historyLoading.value = true
  try {
    const res = await devicesApi.history(selectedDevice.value.sn, { hours: selectedHours.value })
    historyData.value = res.data
  } catch (error) {
    console.error('Failed to load history:', error)
  } finally {
    historyLoading.value = false
  }
}

function formatTime(ts: string) {
  return new Date(ts).toLocaleString('zh-CN', { 
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' 
  })
}

// Chart options
const baseChartOption = {
  grid: { top: 10, right: 20, bottom: 30, left: 50 },
  tooltip: { trigger: 'axis' as const },
  xAxis: { 
    type: 'category' as const, 
    boundaryGap: false,
    axisLabel: { 
      formatter: (val: string) => {
        const d = new Date(val)
        return `${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
      }
    }
  }
}

const ppmChartOption = computed(() => ({
  ...baseChartOption,
  yAxis: { type: 'value' as const, name: 'PPM' },
  xAxis: { ...baseChartOption.xAxis, data: historyData.value.points.map(p => p.ts) },
  series: [{
    type: 'line',
    smooth: true,
    showSymbol: false,
    areaStyle: { opacity: 0.3 },
    lineStyle: { color: '#409EFF', width: 2 },
    itemStyle: { color: '#409EFF' },
    data: historyData.value.points.map(p => p.ppm)
  }]
}))

const tempChartOption = computed(() => ({
  ...baseChartOption,
  yAxis: { type: 'value' as const, name: '°C' },
  xAxis: { ...baseChartOption.xAxis, data: historyData.value.points.map(p => p.ts) },
  series: [{
    type: 'line',
    smooth: true,
    showSymbol: false,
    areaStyle: { opacity: 0.3 },
    lineStyle: { color: '#E6A23C', width: 2 },
    itemStyle: { color: '#E6A23C' },
    data: historyData.value.points.map(p => p.temp)
  }]
}))

const humiChartOption = computed(() => ({
  ...baseChartOption,
  yAxis: { type: 'value' as const, name: '%', max: 100 },
  xAxis: { ...baseChartOption.xAxis, data: historyData.value.points.map(p => p.ts) },
  series: [{
    type: 'line',
    smooth: true,
    showSymbol: false,
    areaStyle: { opacity: 0.3 },
    lineStyle: { color: '#67C23A', width: 2 },
    itemStyle: { color: '#67C23A' },
    data: historyData.value.points.map(p => p.humi)
  }]
}))

onMounted(() => {
  fetchData()
  // Auto refresh every 5 seconds
  setInterval(fetchData, 5000)
})
</script>

<style scoped>
/* Global Styles for Dashboard */
.dashboard {
  height: 100%;
  padding: 24px;
  overflow-y: auto;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 24px;
  /* background: transparent; handled by layout */
}

.stats-row {
  margin-bottom: 0;
}

/* Glass Stat Card */
.stat-card {
  display: flex;
  align-items: center;
  padding: 24px;
  border-radius: 20px !important;
  border: 1px solid rgba(255, 255, 255, 0.6) !important;
  background: rgba(255, 255, 255, 0.65) !important;
  backdrop-filter: blur(20px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.04) !important;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.08) !important;
  background: rgba(255, 255, 255, 0.8) !important;
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 20px;
  width: 100%;
  padding: 0;
}

.stat-icon {
  width: 64px;
  height: 64px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: white;
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
}

.stat-icon.blue { background: linear-gradient(135deg, #0071e3, #47a1ff); }
.stat-icon.green { background: linear-gradient(135deg, #34c759, #6ee48c); }
.stat-icon.gray { background: linear-gradient(135deg, #8e8e93, #aeaeb2); }
.stat-icon.red { background: linear-gradient(135deg, #ff3b30, #ff6b64); }

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 36px;
  font-weight: 700;
  color: #1d1d1f;
  line-height: 1.1;
  letter-spacing: -1px;
}

.stat-label {
  color: #86868b;
  font-size: 14px;
  font-weight: 500;
  margin-top: 4px;
}

/* Glass Device List Card */
.device-card {
  border-radius: 24px !important;
  border: 1px solid rgba(255, 255, 255, 0.6) !important;
  background: rgba(255, 255, 255, 0.65) !important;
  backdrop-filter: blur(20px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.04) !important;
  overflow: hidden;
  flex: 1;
  display: flex;
  flex-direction: column;
}

:deep(.device-card .el-card__header) {
  padding: 20px 32px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  background: transparent;
}

:deep(.device-card .el-card__body) {
  padding: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header span {
  font-size: 20px;
  font-weight: 600;
  color: #1d1d1f;
  letter-spacing: -0.5px;
}

/* Table Styling Override */
:deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(255, 255, 255, 0.5);
  background: transparent !important;
}

:deep(.el-table th.el-table__cell) {
  background-color: rgba(255, 255, 255, 0.5);
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  color: #86868b;
  font-weight: 600;
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

.alarm-value {
  color: #ff3b30;
  font-weight: 700;
}

/* History Dialog Styles */
.time-selector {
  display: flex;
  justify-content: center;
  margin-bottom: 24px;
}

:deep(.el-radio-button__inner) {
  border-radius: 0;
  border: 1px solid #dcdfe6;
  background: transparent;
}

:deep(.el-radio-button:first-child .el-radio-button__inner) {
  border-radius: 8px 0 0 8px;
}

:deep(.el-radio-button:last-child .el-radio-button__inner) {
  border-radius: 0 8px 8px 0;
}

.charts-container {
  max-height: 65vh;
  overflow-y: auto;
  padding: 4px;
}

.chart-card {
  background: rgba(255, 255, 255, 0.8);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.chart-card h4 {
  margin: 0 0 16px 0;
  font-size: 15px;
  color: #1d1d1f;
  font-weight: 600;
}

.no-data {
  padding: 40px 0;
}

.alarms-section {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
}

.alarms-section h4 {
  margin: 0 0 16px 0;
  font-size: 15px;
  color: #ff3b30;
  font-weight: 600;
}

:deep(.history-dialog .el-dialog) {
  border-radius: 24px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  box-shadow: 0 20px 40px rgba(0,0,0,0.1);
}

:deep(.history-dialog .el-dialog__header) {
  margin-right: 0;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

:deep(.history-dialog .el-dialog__title) {
  font-weight: 600;
  color: #1d1d1f;
}

:deep(.history-dialog .el-dialog__body) {
  padding: 24px;
}

.instrument-cell {
  display: flex;
  align-items: center;
  gap: 10px;
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
