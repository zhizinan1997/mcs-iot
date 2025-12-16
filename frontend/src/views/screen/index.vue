<template>
  <div class="screen-container" ref="containerRef">
    <!-- Header -->
    <header class="screen-header">
      <div class="header-left">
        <span class="time">{{ currentTime }}</span>
      </div>
      <h1 class="title">{{ config.title }}</h1>
      <div class="header-right">
        <div class="stat-item">
          <span class="label">设备总数</span>
          <span class="value">{{ stats.devices_total }}</span>
        </div>
        <div class="stat-item online">
          <span class="label">在线</span>
          <span class="value">{{ stats.devices_online }}</span>
        </div>
        <div class="stat-item alarm">
          <span class="label">今日报警</span>
          <span class="value">{{ stats.alarms_today }}</span>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <div class="screen-main">
      <!-- Left Panel: Factory Map -->
      <div class="map-panel">
        <div class="panel-header">
          <span>工厂平面图</span>
          <el-button v-if="editMode" type="primary" size="small" @click="savePositions">
            保存布局
          </el-button>
          <el-button size="small" @click="editMode = !editMode">
            {{ editMode ? '退出编辑' : '编辑布局' }}
          </el-button>
        </div>
        <div 
          class="factory-map" 
          ref="mapRef"
          :style="{ backgroundImage: config.background_image ? `url(${config.background_image})` : '' }"
        >
          <!-- Draggable Device Icons -->
          <div
            v-for="device in devices"
            :key="device.sn"
            class="device-marker"
            :class="{ 
              online: device.status === 'online',
              alarm: device.ppm && device.ppm > 1000,
              dragging: editMode
            }"
            :style="{
              left: `${device.position_x || 50}%`,
              top: `${device.position_y || 50}%`
            }"
            :draggable="editMode"
            @dragstart="onDragStart($event, device)"
            @click="selectDevice(device)"
          >
            <div class="marker-icon">
              <el-icon><Monitor /></el-icon>
            </div>
            <div class="marker-label">{{ device.name || device.sn }}</div>
            <div class="marker-value" v-if="device.ppm !== null">
              {{ device.ppm?.toFixed(1) }} ppm
            </div>
          </div>
        </div>
      </div>

      <!-- Right Panel -->
      <div class="right-panel">
        <!-- Selected Device Info -->
        <div class="info-panel" v-if="selectedDevice">
          <div class="panel-header">
            <span>{{ selectedDevice.name || selectedDevice.sn }}</span>
            <el-tag :type="selectedDevice.status === 'online' ? 'success' : 'info'" size="small">
              {{ selectedDevice.status === 'online' ? '在线' : '离线' }}
            </el-tag>
          </div>
          <div class="info-grid">
            <div class="info-item">
              <span class="label">浓度</span>
              <span class="value" :class="{ alarm: selectedDevice.ppm > 1000 }">
                {{ selectedDevice.ppm?.toFixed(2) || '-' }} ppm
              </span>
            </div>
            <div class="info-item">
              <span class="label">温度</span>
              <span class="value">{{ selectedDevice.temp?.toFixed(1) || '-' }} °C</span>
            </div>
          </div>
        </div>

        <!-- Trend Chart -->
        <div class="chart-panel">
          <div class="panel-header">实时趋势</div>
          <v-chart class="chart" :option="chartOption" autoresize />
        </div>

        <!-- Alarm List -->
        <div class="alarm-panel">
          <div class="panel-header">
            <span>最新报警</span>
          </div>
          <div class="alarm-list">
            <div 
              v-for="alarm in recentAlarms" 
              :key="alarm.id" 
              class="alarm-item"
              :class="alarm.type.toLowerCase()"
            >
              <span class="alarm-time">{{ formatTime(alarm.time) }}</span>
              <span class="alarm-sn">{{ alarm.sn }}</span>
              <span class="alarm-type">{{ alarm.type }}</span>
              <span class="alarm-value">{{ alarm.value?.toFixed(1) }} ppm</span>
            </div>
            <div v-if="recentAlarms.length === 0" class="no-alarm">
              暂无报警
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Drop Zone for drag -->
    <div 
      v-if="editMode && draggingDevice"
      class="drop-overlay"
      @dragover.prevent
      @drop="onDrop"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, provide } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart, { THEME_KEY } from 'vue-echarts'
import { dashboardApi, alarmsApi, configApi } from '../../api'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])
provide(THEME_KEY, 'dark')

interface Device {
  sn: string
  name: string | null
  ppm: number | null
  temp: number | null
  status: string
  position_x: number | null
  position_y: number | null
}

interface Alarm {
  id: number
  time: string
  sn: string
  type: string
  value: number
}

const containerRef = ref<HTMLElement>()
const mapRef = ref<HTMLElement>()

const currentTime = ref('')
const editMode = ref(false)
const draggingDevice = ref<Device | null>(null)
const selectedDevice = ref<Device | null>(null)

const config = reactive({
  title: 'MCS-IoT 监测大屏',
  background_image: '',
  refresh_rate: 5
})

const stats = reactive({
  devices_total: 0,
  devices_online: 0,
  devices_offline: 0,
  alarms_today: 0
})

const devices = ref<Device[]>([])
const recentAlarms = ref<Alarm[]>([])
const trendData = ref<{ time: string; value: number }[]>([])

// WebSocket connection
let ws: WebSocket | null = null
let reconnectTimer: number | null = null

// Chart options
const chartOption = computed(() => ({
  backgroundColor: 'transparent',
  grid: { top: 30, right: 20, bottom: 30, left: 50 },
  tooltip: { trigger: 'axis' },
  xAxis: {
    type: 'category',
    data: trendData.value.map(d => d.time.split(' ')[1] || d.time),
    axisLine: { lineStyle: { color: '#3a4a5a' } },
    axisLabel: { color: '#8a9aa9' }
  },
  yAxis: {
    type: 'value',
    name: 'PPM',
    axisLine: { lineStyle: { color: '#3a4a5a' } },
    axisLabel: { color: '#8a9aa9' },
    splitLine: { lineStyle: { color: '#2a3a4a' } }
  },
  series: [{
    type: 'line',
    data: trendData.value.map(d => d.value),
    smooth: true,
    symbol: 'circle',
    symbolSize: 6,
    lineStyle: { color: '#409EFF', width: 2 },
    areaStyle: {
      color: {
        type: 'linear',
        x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [
          { offset: 0, color: 'rgba(64, 158, 255, 0.4)' },
          { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
        ]
      }
    }
  }]
}))

function updateTime() {
  currentTime.value = new Date().toLocaleString('zh-CN')
}

async function fetchData() {
  try {
    const [statsRes, devicesRes, alarmsRes] = await Promise.all([
      dashboardApi.stats(),
      dashboardApi.realtime(),
      alarmsApi.list({ page: 1, size: 5 })
    ])
    Object.assign(stats, statsRes.data)
    devices.value = devicesRes.data
    recentAlarms.value = alarmsRes.data.data

    // Update trend with latest data
    if (selectedDevice.value) {
      const device = devices.value.find(d => d.sn === selectedDevice.value?.sn)
      if (device && device.ppm !== null) {
        const now = new Date().toLocaleTimeString('zh-CN')
        trendData.value.push({ time: now, value: device.ppm })
        if (trendData.value.length > 30) {
          trendData.value.shift()
        }
      }
    }
  } catch (error) {
    console.error('Failed to fetch data:', error)
  }
}

async function loadConfig() {
  try {
    const res = await configApi.getDashboard()
    Object.assign(config, res.data)
  } catch {}
}

function connectWebSocket() {
  const wsUrl = `ws://localhost:8000/api/dashboard/ws`
  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    console.log('WebSocket connected')
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'realtime') {
        devices.value = data.data
      }
    } catch {}
  }

  ws.onclose = () => {
    console.log('WebSocket disconnected, reconnecting...')
    reconnectTimer = setTimeout(connectWebSocket, 3000) as unknown as number
  }
}

function selectDevice(device: Device) {
  selectedDevice.value = device
  trendData.value = [] // Reset trend data
}

function onDragStart(event: DragEvent, device: Device) {
  draggingDevice.value = device
}

function onDrop(event: DragEvent) {
  if (!mapRef.value || !draggingDevice.value) return

  const rect = mapRef.value.getBoundingClientRect()
  const x = ((event.clientX - rect.left) / rect.width) * 100
  const y = ((event.clientY - rect.top) / rect.height) * 100

  const device = devices.value.find(d => d.sn === draggingDevice.value?.sn)
  if (device) {
    device.position_x = Math.max(0, Math.min(100, x))
    device.position_y = Math.max(0, Math.min(100, y))
  }
  draggingDevice.value = null
}

async function savePositions() {
  const positions: Record<string, { x: number; y: number }> = {}
  devices.value.forEach(d => {
    if (d.position_x !== null && d.position_y !== null) {
      positions[d.sn] = { x: d.position_x, y: d.position_y }
    }
  })
  
  try {
    await fetch('http://localhost:8000/api/dashboard/devices/positions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify(positions)
    })
    editMode.value = false
  } catch (error) {
    console.error('Failed to save positions:', error)
  }
}

function formatTime(time: string) {
  return new Date(time).toLocaleTimeString('zh-CN')
}

let dataInterval: number | null = null
let timeInterval: number | null = null

onMounted(() => {
  updateTime()
  loadConfig()
  fetchData()
  
  timeInterval = setInterval(updateTime, 1000) as unknown as number
  dataInterval = setInterval(fetchData, config.refresh_rate * 1000) as unknown as number
  
  // Try WebSocket connection
  connectWebSocket()
})

onUnmounted(() => {
  if (timeInterval) clearInterval(timeInterval)
  if (dataInterval) clearInterval(dataInterval)
  if (reconnectTimer) clearTimeout(reconnectTimer)
  if (ws) ws.close()
})
</script>

<style scoped>
.screen-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #0f1923 0%, #1a2a3a 100%);
  color: #fff;
  display: flex;
  flex-direction: column;
}

.screen-header {
  height: 60px;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  border-bottom: 1px solid rgba(64, 158, 255, 0.3);
}

.header-left .time {
  color: #8a9aa9;
  font-size: 14px;
}

.title {
  font-size: 24px;
  font-weight: 600;
  background: linear-gradient(90deg, #409EFF, #67C23A);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0;
}

.header-right {
  display: flex;
  gap: 24px;
}

.stat-item {
  text-align: center;
}

.stat-item .label {
  display: block;
  font-size: 12px;
  color: #8a9aa9;
}

.stat-item .value {
  font-size: 24px;
  font-weight: 700;
  color: #409EFF;
}

.stat-item.online .value { color: #67C23A; }
.stat-item.alarm .value { color: #F56C6C; }

.screen-main {
  flex: 1;
  display: flex;
  padding: 16px;
  gap: 16px;
}

.map-panel {
  flex: 2;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  border: 1px solid rgba(64, 158, 255, 0.2);
  display: flex;
  flex-direction: column;
}

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-header {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(64, 158, 255, 0.2);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.factory-map {
  flex: 1;
  position: relative;
  background-size: cover;
  background-position: center;
  background-color: rgba(0, 20, 40, 0.5);
}

.device-marker {
  position: absolute;
  transform: translate(-50%, -50%);
  cursor: pointer;
  text-align: center;
  transition: all 0.3s;
}

.device-marker.dragging {
  cursor: grab;
}

.device-marker:hover {
  transform: translate(-50%, -50%) scale(1.1);
}

.marker-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(64, 158, 255, 0.3);
  border: 2px solid #409EFF;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto;
  font-size: 20px;
}

.device-marker.online .marker-icon {
  background: rgba(103, 194, 58, 0.3);
  border-color: #67C23A;
  animation: pulse 2s infinite;
}

.device-marker.alarm .marker-icon {
  background: rgba(245, 108, 108, 0.5);
  border-color: #F56C6C;
  animation: alarm-pulse 0.5s infinite;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(103, 194, 58, 0.4); }
  50% { box-shadow: 0 0 0 10px rgba(103, 194, 58, 0); }
}

@keyframes alarm-pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

.marker-label {
  font-size: 12px;
  margin-top: 4px;
  white-space: nowrap;
}

.marker-value {
  font-size: 14px;
  font-weight: 700;
  color: #67C23A;
}

.device-marker.alarm .marker-value {
  color: #F56C6C;
}

.info-panel, .chart-panel, .alarm-panel {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  border: 1px solid rgba(64, 158, 255, 0.2);
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  padding: 16px;
}

.info-item {
  text-align: center;
}

.info-item .label {
  display: block;
  font-size: 12px;
  color: #8a9aa9;
}

.info-item .value {
  font-size: 24px;
  font-weight: 700;
  color: #67C23A;
}

.info-item .value.alarm {
  color: #F56C6C;
}

.chart-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chart {
  flex: 1;
  min-height: 200px;
}

.alarm-panel {
  max-height: 200px;
  overflow-y: auto;
}

.alarm-list {
  padding: 8px;
}

.alarm-item {
  display: flex;
  gap: 12px;
  padding: 8px 12px;
  background: rgba(245, 108, 108, 0.1);
  border-left: 3px solid #F56C6C;
  margin-bottom: 8px;
  border-radius: 4px;
  font-size: 13px;
}

.alarm-time { color: #8a9aa9; }
.alarm-sn { flex: 1; }
.alarm-type { color: #F56C6C; font-weight: 600; }
.alarm-value { color: #fff; }

.no-alarm {
  text-align: center;
  color: #8a9aa9;
  padding: 20px;
}

.drop-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 100;
}
</style>
