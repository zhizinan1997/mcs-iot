<template>
  <div class="dashboard">
    <!-- Stats Cards -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon blue"><el-icon><Monitor /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.devices_total }}</div>
            <div class="stat-label">设备总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon green"><el-icon><CircleCheck /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.devices_online }}</div>
            <div class="stat-label">在线设备</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon gray"><el-icon><CircleClose /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.devices_offline }}</div>
            <div class="stat-label">离线设备</div>
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
          <span>实时设备状态</span>
          <el-button type="primary" size="small" @click="fetchData">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>
      </template>
      
      <el-table :data="sortedDevices" stripe>
        <el-table-column prop="sn" label="设备编号" min-width="100" />
        <el-table-column prop="name" label="设备名称" min-width="100" />
        <el-table-column prop="ppm" label="浓度 (PPM)" min-width="100">
          <template #default="{ row }">
            <span :class="{ 'alarm-value': row.ppm > 1000 }">
              {{ row.ppm?.toFixed(2) || '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="temp" label="温度 (°C)" min-width="90">
          <template #default="{ row }">
            {{ row.temp?.toFixed(1) || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="电池" min-width="70" align="center">
          <template #default="{ row }">
            <span v-if="row.battery != null" :style="{ color: row.battery < 20 ? '#F56C6C' : row.battery < 50 ? '#E6A23C' : '#67C23A' }">
              {{ row.battery }}%
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="信号" min-width="85" align="center">
          <template #default="{ row }">
            <span v-if="row.rssi != null" :style="{ color: row.rssi < -80 ? '#F56C6C' : row.rssi < -70 ? '#E6A23C' : '#67C23A' }">
              {{ row.rssi }}dBm
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="network" label="网络" min-width="70" align="center">
          <template #default="{ row }">
            {{ row.network || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" min-width="80" align="center">
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

// Sorted devices by sn (device number)
const sortedDevices = computed(() => {
  return [...devices.value].sort((a, b) => a.sn.localeCompare(b.sn))
})

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
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.stats-row {
  margin-bottom: 0;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 20px;
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: white;
}

.stat-icon.blue { background: linear-gradient(135deg, #409EFF, #66b1ff); }
.stat-icon.green { background: linear-gradient(135deg, #67C23A, #85ce61); }
.stat-icon.gray { background: linear-gradient(135deg, #909399, #a6a9ad); }
.stat-icon.red { background: linear-gradient(135deg, #F56C6C, #f78989); }

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
}

.stat-label {
  color: #909399;
  font-size: 14px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.alarm-value {
  color: #F56C6C;
  font-weight: bold;
}

/* History Dialog Styles */
.time-selector {
  display: flex;
  justify-content: center;
  margin-bottom: 20px;
}

.charts-container {
  max-height: 65vh;
  overflow-y: auto;
}

.chart-card {
  background: linear-gradient(135deg, #f8f9fa 0%, #fff 100%);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}

.chart-card h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #606266;
}

.no-data {
  padding: 40px 0;
}

.alarms-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}

.alarms-section h4 {
  margin: 0 0 16px 0;
  font-size: 14px;
  color: #F56C6C;
}

:deep(.history-dialog .el-dialog__body) {
  padding-top: 10px;
}
</style>
