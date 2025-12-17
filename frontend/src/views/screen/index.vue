<template>
  <div class="screen-container">
    <!-- Header -->
    <header class="screen-header">
      <div class="header-left">
        <h1 class="title">{{ config.title || 'MCS-IoT 监测大屏' }}</h1>
      </div>
      <div class="header-center">
        <div class="pollutant-indicator">
          <span class="pollutant-label">主要监测物:</span>
          <span class="pollutant-value">CH₄</span>
        </div>
      </div>
      <div class="header-right">
        <div class="header-info">
          <span class="location">{{ weather.location }}</span>
          <span class="date">{{ currentDate }}</span>
          <span class="time">{{ currentTime }}</span>
        </div>
        <div class="weather-widget">
          <div class="weather-icon">🌤️</div>
          <div class="weather-info">
            <span class="temp">{{ weather.temp }}°C</span>
            <span class="desc">{{ weather.desc }}</span>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <div class="screen-main">
      <!-- Left Panel: Stats & Thumbnails -->
      <aside class="left-panel">
        <div class="panel-section thumbnails">
          <div class="section-title">
            <span class="glow-dot"></span>
            监测仪表
          </div>
          <div class="thumbnail-grid">
            <div class="thumbnail-item" v-for="inst in instruments" :key="inst.id">
              <div class="thumbnail-img" :style="{ borderColor: inst.color }">
                <div class="zone-overlay" :style="{ backgroundColor: inst.color + '33' }">
                  <span class="zone-name">{{ inst.name }}</span>
                  <span class="zone-count">{{ getInstrumentDeviceCount(inst.id) }} 台</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="panel-section stats-panel">
          <div class="section-title">
            <span class="glow-dot"></span>
            实时统计
          </div>
          <div class="stat-grid">
            <div class="stat-card">
              <div class="stat-icon blue">📊</div>
              <div class="stat-info">
                <span class="stat-value">{{ stats.devices_total }}</span>
                <span class="stat-label">传感器总数</span>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon green">✅</div>
              <div class="stat-info">
                <span class="stat-value green">{{ stats.devices_online }}</span>
                <span class="stat-label">在线传感器</span>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon red">🔔</div>
              <div class="stat-info">
                <span class="stat-value red">{{ stats.alarms_today }}</span>
                <span class="stat-label">今日报警</span>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon cyan">📈</div>
              <div class="stat-info">
                <span class="stat-value cyan">{{ avgPpm.toFixed(1) }}</span>
                <span class="stat-label">平均浓度(ppm)</span>
              </div>
            </div>
          </div>
        </div>

        <div class="panel-section metrics-panel">
          <div class="section-title">
            <span class="glow-dot"></span>
            关键指标
          </div>
          <div class="metrics-list">
            <div class="metric-item">
              <span class="metric-label">PM2.5</span>
              <span class="metric-value">{{ metrics.pm25 }} <small>μg/m³</small></span>
            </div>
            <div class="metric-item">
              <span class="metric-label">PM10</span>
              <span class="metric-value">{{ metrics.pm10 }} <small>μg/m³</small></span>
            </div>
            <div class="metric-item">
              <span class="metric-label">CO₂</span>
              <span class="metric-value">{{ metrics.co2 }} <small>ppm</small></span>
            </div>
            <div class="metric-item">
              <span class="metric-label">Temperature</span>
              <span class="metric-value">{{ metrics.temp }} <small>°C</small></span>
            </div>
            <div class="metric-item">
              <span class="metric-label">Humidity</span>
              <span class="metric-value">{{ metrics.humidity }} <small>%</small></span>
            </div>
          </div>
        </div>
      </aside>

      <!-- Center Panel: Factory Map -->
      <main class="center-panel">
        <div class="map-container">
          <div class="map-header">
            <span class="map-title">厂区三维监测图</span>
            <div class="map-legend">
              <span class="legend-item online"><span class="dot"></span>在线</span>
              <span class="legend-item offline"><span class="dot"></span>离线</span>
              <span class="legend-item alarm"><span class="dot"></span>报警</span>
            </div>
          </div>
          <div class="factory-map" ref="mapRef">
            <!-- Device Markers -->
            <div
              v-for="device in devices"
              :key="device.sn"
              class="device-marker"
              :class="{
                online: device.status === 'online',
                alarm: device.ppm && device.ppm > 1000,
                selected: selectedDevice?.sn === device.sn
              }"
              :style="{
                left: `${device.position_x ?? getStablePosition(device.sn, 'x')}%`,
                top: `${device.position_y ?? getStablePosition(device.sn, 'y')}%`
              }"
              @click="selectDevice(device)"
            >
              <div class="marker-pulse"></div>
              <div class="marker-icon">
                <span>📍</span>
              </div>
              <div class="marker-tooltip" v-if="selectedDevice?.sn === device.sn">
                <div class="tooltip-header">
                  <span class="tooltip-name">{{ device.name || device.sn }}</span>
                  <span class="tooltip-status" :class="device.status">
                    {{ device.status === 'online' ? '在线' : '离线' }}
                  </span>
                </div>
                <div class="tooltip-body">
                  <div class="tooltip-row">
                    <span>浓度:</span>
                    <span class="value" :class="{ alarm: (device.ppm ?? 0) > 1000 }">
                      {{ device.ppm?.toFixed(2) || '-' }} ppm
                    </span>
                  </div>
                  <div class="tooltip-row">
                    <span>温度:</span>
                    <span class="value">{{ device.temp?.toFixed(1) || '-' }} °C</span>
                  </div>
                  <div class="tooltip-row">
                    <span>湿度:</span>
                    <span class="value">{{ device.humi?.toFixed(1) || '-' }} %</span>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Map Grid Lines -->
            <div class="map-grid"></div>
          </div>
        </div>
      </main>

      <!-- Right Panel: Device Status Cards -->
      <aside class="right-panel">
        <div class="panel-section device-list-panel">
          <div class="section-title">
            <span class="glow-dot"></span>
            传感器状态
          </div>
          <div class="device-list">
            <div 
              v-for="device in devices" 
              :key="device.sn" 
              class="device-card"
              :class="{ 
                online: device.status === 'online',
                alarm: device.ppm && device.ppm > 1000 
              }"
              @click="selectDevice(device)"
            >
              <div class="device-icon">
                {{ getDeviceIcon(device.sn) }}
              </div>
              <div class="device-info">
                <span class="device-instrument" v-if="device.instrument_name">
                  <span class="instrument-dot" :style="{ backgroundColor: device.instrument_color || '#409eff' }"></span>
                  {{ device.instrument_name }}
                </span>
                <span class="device-name">{{ device.name || device.sn }}</span>
              </div>
              <div class="device-reading">
                <span class="reading-value" :class="{ alarm: (device.ppm ?? 0) > 1000 }">
                  {{ device.ppm?.toFixed(0) || '-' }}
                </span>
                <span class="reading-unit">ppm</span>
              </div>
            </div>
          </div>
        </div>

        <div class="panel-section alarm-panel">
          <div class="section-title">
            <span class="glow-dot red"></span>
            最新报警
          </div>
          <div class="alarm-list">
            <div 
              v-for="alarm in recentAlarms" 
              :key="alarm.id" 
              class="alarm-item"
            >
              <span class="alarm-time">{{ formatTime(alarm.time) }}</span>
              <span class="alarm-sn">{{ alarm.sn }}</span>
              <span class="alarm-value">{{ alarm.value?.toFixed(1) }} ppm</span>
            </div>
            <div v-if="recentAlarms.length === 0" class="no-data">
              暂无报警
            </div>
          </div>
        </div>
      </aside>
    </div>

    <!-- Bottom Panel: Trend Chart -->
    <footer class="screen-footer">
      <div class="chart-container">
        <div class="chart-header">
          <span class="chart-title">污染物趋势图</span>
          <div class="chart-tabs">
            <button 
              v-for="tab in ['今日', '昨日', '本周']" 
              :key="tab"
              class="chart-tab"
              :class="{ active: activeTab === tab }"
              @click="activeTab = tab"
            >
              {{ tab }}
            </button>
          </div>
        </div>
        <v-chart class="trend-chart" :option="chartOption" autoresize />
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, provide } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart, { THEME_KEY } from 'vue-echarts'
import { dashboardApi, alarmsApi, configApi, instrumentsApi } from '../../api'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])
provide(THEME_KEY, 'dark')

interface Device {
  sn: string
  name: string | null
  ppm: number | null
  temp: number | null
  humi?: number | null
  status: string
  position_x: number | null
  position_y: number | null
  zone_id: number | null
  zone_name: string | null
  zone_color: string | null
  instrument_name: string | null
  instrument_color: string | null
}

interface Alarm {
  id: number
  time: string
  sn: string
  type: string
  value: number
}

const currentTime = ref('')
const currentDate = ref('')
const activeTab = ref('今日')
const selectedDevice = ref<Device | null>(null)

const config = reactive({
  title: 'MCS-IoT 监测大屏',
  refresh_rate: 5
})

const weather = reactive({
  temp: '--',
  desc: '获取中...',
  location: '定位中...'
})

const stats = reactive({
  devices_total: 0,
  devices_online: 0,
  devices_offline: 0,
  alarms_today: 0
})

const metrics = reactive({
  pm25: 23,
  pm10: 46,
  co2: 420,
  temp: 28,
  humidity: 40
})

interface Instrument {
  id: number
  name: string
  color: string
  description: string | null
  sensor_count: number
  is_displayed: boolean
}

const instruments = ref<Instrument[]>([])

const devices = ref<Device[]>([])
const recentAlarms = ref<Alarm[]>([])
const trendData = ref<{ time: string; value: number }[]>([])

const avgPpm = computed(() => {
  const validDevices = devices.value.filter(d => d.ppm !== null)
  if (validDevices.length === 0) return 0
  return validDevices.reduce((sum, d) => sum + (d.ppm || 0), 0) / validDevices.length
})

// Chart options with glowing effect
const chartOption = computed(() => ({
  backgroundColor: 'transparent',
  grid: { top: 40, right: 40, bottom: 40, left: 60 },
  tooltip: { 
    trigger: 'axis',
    backgroundColor: 'rgba(0, 30, 60, 0.9)',
    borderColor: '#00d4ff',
    textStyle: { color: '#fff' }
  },
  xAxis: {
    type: 'category',
    data: trendData.value.map(d => d.time.split(' ')[1] || d.time),
    axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.3)' } },
    axisLabel: { color: 'rgba(255, 255, 255, 0.6)' },
    splitLine: { show: false }
  },
  yAxis: {
    type: 'value',
    name: 'PPM',
    nameTextStyle: { color: 'rgba(255, 255, 255, 0.6)' },
    axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.3)' } },
    axisLabel: { color: 'rgba(255, 255, 255, 0.6)' },
    splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.1)' } }
  },
  series: [{
    type: 'line',
    data: trendData.value.map(d => d.value),
    smooth: true,
    symbol: 'circle',
    symbolSize: 8,
    lineStyle: { 
      color: '#00d4ff', 
      width: 3,
      shadowColor: '#00d4ff',
      shadowBlur: 10
    },
    itemStyle: {
      color: '#00d4ff',
      shadowColor: '#00d4ff',
      shadowBlur: 10
    },
    areaStyle: {
      color: {
        type: 'linear',
        x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [
          { offset: 0, color: 'rgba(0, 212, 255, 0.4)' },
          { offset: 0.5, color: 'rgba(0, 212, 255, 0.1)' },
          { offset: 1, color: 'rgba(0, 212, 255, 0)' }
        ]
      }
    }
  }]
}))

function updateTime() {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('zh-CN')
  currentDate.value = now.toLocaleDateString('zh-CN', { 
    year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' 
  })
}

async function fetchData() {
  console.log('[Screen] Fetching data...')
  
  // Fetch stats
  try {
    const statsRes = await dashboardApi.stats()
    console.log('[Screen] Stats:', statsRes.data)
    Object.assign(stats, statsRes.data)
  } catch (error) {
    console.error('[Screen] Failed to fetch stats:', error)
  }
  
  // Fetch devices
  try {
    const devicesRes = await dashboardApi.realtime()
    console.log('[Screen] Devices:', devicesRes.data?.length, 'devices')
    devices.value = devicesRes.data || []
    
    // Update trend data
    if (devices.value.length > 0) {
      const now = new Date().toLocaleTimeString('zh-CN')
      const avg = avgPpm.value
      trendData.value.push({ time: now, value: avg })
      if (trendData.value.length > 30) {
        trendData.value.shift()
      }
    }

    // Update metrics from device data
    if (devices.value.length > 0) {
      const onlineDevices = devices.value.filter((d: Device) => d.status === 'online')
      if (onlineDevices.length > 0) {
        const avgTemp = onlineDevices.reduce((sum: number, d: Device) => sum + (d.temp || 0), 0) / onlineDevices.length
        metrics.temp = Math.round(avgTemp)
        const avgHumi = onlineDevices.reduce((sum: number, d: Device) => sum + (d.humi || 50), 0) / onlineDevices.length
        metrics.humidity = Math.round(avgHumi)
      }
    }
  } catch (error) {
    console.error('[Screen] Failed to fetch devices:', error)
  }
  
  // Fetch alarms (separate to avoid blocking other data)
  try {
    const alarmsRes = await alarmsApi.list({ page: 1, size: 5 })
    recentAlarms.value = alarmsRes.data?.data || []
  } catch (error) {
    console.error('[Screen] Failed to fetch alarms:', error)
    recentAlarms.value = [] // Set empty on error
  }
}

async function loadConfig() {
  try {
    const res = await configApi.getDashboard()
    Object.assign(config, res.data)
    console.log('[Screen] Config loaded, refresh_rate:', config.refresh_rate)
    
    // Restart data interval with new refresh rate
    if (dataInterval) {
      clearInterval(dataInterval)
    }
    dataInterval = setInterval(fetchData, config.refresh_rate * 1000) as unknown as number
    console.log('[Screen] Data interval set to', config.refresh_rate, 'seconds')
  } catch (err) {
    console.error('[Screen] Failed to load config:', err)
  }
}

function selectDevice(device: Device) {
  selectedDevice.value = selectedDevice.value?.sn === device.sn ? null : device
}

// Generate stable position based on device SN (consistent across renders)
function getStablePosition(sn: string, axis: 'x' | 'y'): number {
  let hash = 0
  const seed = axis === 'x' ? sn : sn.split('').reverse().join('')
  for (let i = 0; i < seed.length; i++) {
    hash = ((hash << 5) - hash) + seed.charCodeAt(i)
    hash = hash & hash // Convert to 32bit integer
  }
  // Return value between 15 and 85 (to keep markers within visible area)
  return 15 + Math.abs(hash % 70)
}

// Get device count for an instrument
function getInstrumentDeviceCount(instId: number): number {
  // We can use the devices list which already contains instrument info, 
  // OR use the count from instrument object (but realtime count from devices list is better)
  // Devices list has instrument_name, maybe not instrument_id?
  // Let's check Device interface. It has instrument_name, instrument_color.
  // Ideally backend should return instrument_id.
  // But we can match by name if ID is missing, or rely on instrument.sensor_count?
  // Let's rely on filtering devices by instrument_name for now if ID is missing.
  // Wait, instruments have names.
  const inst = instruments.value.find(i => i.id === instId)
  if (!inst) return 0
  return devices.value.filter(d => d.instrument_name === inst.name).length
}

function getDeviceIcon(sn: string): string {
  if (sn.startsWith('GAS')) return '🔥'
  if (sn.startsWith('CO2')) return '💨'
  if (sn.startsWith('NH3')) return '⚗️'
  return '📡'
}

function formatTime(time: string): string {
  return new Date(time).toLocaleTimeString('zh-CN')
}

// Fetch weather using browser geolocation and wttr.in API
async function fetchWeather() {
  console.log('[Screen] Fetching weather...')
  
  // Get geolocation
  if ('geolocation' in navigator) {
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords
        console.log('[Screen] Location:', latitude, longitude)
        
        try {
          // Use wttr.in API with Chinese lang (free, no key required)
          const response = await fetch(
            `https://wttr.in/${latitude},${longitude}?format=j1&lang=zh`,
            { headers: { 'Accept': 'application/json' } }
          )
          const data = await response.json()
          
          if (data.current_condition && data.current_condition[0]) {
            const current = data.current_condition[0]
            weather.temp = current.temp_C
            // Prefer Chinese description
            weather.desc = current.lang_zh?.[0]?.value || current.weatherDesc?.[0]?.value || '未知'
          }
          
          // Try to get Chinese location using reverse geocoding fallback
          await fetchChineseLocation(latitude, longitude)
          
          console.log('[Screen] Weather:', weather)
        } catch (err) {
          console.error('[Screen] Weather API error:', err)
          weather.desc = '获取失败'
        }
      },
      (error) => {
        console.warn('[Screen] Geolocation error:', error.message)
        weather.location = '定位失败'
        weather.desc = '--'
        // Fallback: try IP-based location
        fetchWeatherByIP()
      },
      { timeout: 5000, enableHighAccuracy: false }
    )
  } else {
    weather.location = '不支持定位'
    fetchWeatherByIP()
  }
}

// Get Chinese location name using ipapi.co (free, 1000 req/day)
async function fetchChineseLocation(_lat: number, _lon: number) {
  try {
    // ipapi.co provides Chinese city names directly
    const response = await fetch('https://ipapi.co/json/')
    const data = await response.json()
    if (data.city) {
      // ipapi returns Chinese city names for CN region
      weather.location = data.city
      console.log('[Screen] Location from ipapi:', data.city)
    } else {
      weather.location = '未知位置'
    }
  } catch (err) {
    console.error('[Screen] IP location error:', err)
    weather.location = '定位失败'
  }
}

// Fallback weather by IP
async function fetchWeatherByIP() {
  try {
    // First get location from ipapi.co
    const ipRes = await fetch('https://ipapi.co/json/')
    const ipData = await ipRes.json()
    if (ipData.city) {
      weather.location = ipData.city
    }
    
    // Then get weather
    const response = await fetch('https://wttr.in/?format=j1&lang=zh')
    const data = await response.json()
    if (data.current_condition?.[0]) {
      weather.temp = data.current_condition[0].temp_C
      weather.desc = data.current_condition[0].lang_zh?.[0]?.value || 
                     data.current_condition[0].weatherDesc?.[0]?.value || '未知'
    }
  } catch (err) {
    console.error('[Screen] IP Weather error:', err)
  }
}

// Fetch instruments from API
async function fetchInstruments() {
  try {
    const res = await instrumentsApi.list()
    // Filter only instruments that should show on screen
    instruments.value = res.data.data.filter((i: any) => i.is_displayed !== false)
    console.log('[Screen] Instruments loaded:', instruments.value.length)
  } catch (error) {
    console.error('[Screen] Failed to load instruments:', error)
  }
}

let dataInterval: number | null = null
let timeInterval: number | null = null

onMounted(async () => {
  console.log('[Screen] Component mounted')
  updateTime()
  fetchData()
  fetchWeather()
  fetchInstruments() // Load instruments
  
  // Start time interval immediately
  timeInterval = setInterval(updateTime, 1000) as unknown as number
  
  // Load config first, which will start the data interval with correct refresh rate
  await loadConfig()
})

onUnmounted(() => {
  if (timeInterval) clearInterval(timeInterval)
  if (dataInterval) clearInterval(dataInterval)
})
</script>

<style scoped>
/* ===== Base Styles ===== */
.screen-container {
  height: 100vh;
  max-height: 100vh;
  background: linear-gradient(135deg, #0a1628 0%, #0f2847 50%, #1a365d 100%);
  color: #fff;
  display: flex;
  flex-direction: column;
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
  overflow: hidden;
}

/* ===== Header ===== */
.screen-header {
  height: 70px;
  background: linear-gradient(90deg, rgba(0, 30, 60, 0.8), rgba(0, 50, 100, 0.6), rgba(0, 30, 60, 0.8));
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 30px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.3);
  box-shadow: 0 2px 20px rgba(0, 212, 255, 0.2);
}

.title {
  font-size: 28px;
  font-weight: 700;
  background: linear-gradient(90deg, #00d4ff, #00ff88, #00d4ff);
  background-size: 200% 100%;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: gradient-flow 3s linear infinite;
  margin: 0;
  letter-spacing: 4px;
}

@keyframes gradient-flow {
  0% { background-position: 0% 50%; }
  100% { background-position: 200% 50%; }
}

.header-center .pollutant-indicator {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 20px;
  background: rgba(0, 212, 255, 0.1);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 20px;
}

.pollutant-label {
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
}

.pollutant-value {
  color: #00d4ff;
  font-size: 18px;
  font-weight: 700;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-info .location {
  font-size: 14px;
  color: #00d4ff;
  font-weight: 500;
}

.header-info .date {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
}

.header-info .time {
  font-size: 18px;
  font-weight: 600;
  color: #00d4ff;
}

.weather-widget {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  border: 1px solid rgba(0, 212, 255, 0.2);
}

.weather-icon {
  font-size: 28px;
}

.weather-info {
  display: flex;
  flex-direction: column;
}

.weather-info .temp {
  font-size: 16px;
  font-weight: 600;
}

.weather-info .desc {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
}

/* ===== Main Layout ===== */
.screen-main {
  flex: 1;
  display: flex;
  padding: 12px;
  gap: 12px;
  min-height: 0;
  max-height: calc(100vh - 70px);
  overflow: hidden;
}

/* ===== Panel Styles ===== */
.left-panel, .right-panel {
  width: 260px;
  min-width: 260px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow: hidden;
}

.panel-section {
  background: rgba(0, 30, 60, 0.6);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 12px;
  backdrop-filter: blur(10px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.15);
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}

.glow-dot {
  width: 8px;
  height: 8px;
  background: #00d4ff;
  border-radius: 50%;
  box-shadow: 0 0 10px #00d4ff;
}

.glow-dot.red {
  background: #ff4757;
  box-shadow: 0 0 10px #ff4757;
}

/* ===== Thumbnails ===== */
.thumbnail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  padding: 12px;
}

.thumbnail-item {
  aspect-ratio: 16/9;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.3s;
}

.thumbnail-item:hover {
  transform: scale(1.05);
}

.thumbnail-img {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, rgba(0, 100, 150, 0.5), rgba(0, 50, 100, 0.8));
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.zone-overlay {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.9);
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);
}

/* ===== Stats ===== */
.stat-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  padding: 12px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  background: rgba(0, 50, 100, 0.3);
  border-radius: 10px;
  border: 1px solid rgba(0, 212, 255, 0.1);
}

.stat-icon {
  font-size: 24px;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: #00d4ff;
}

.stat-value.green { color: #00ff88; }
.stat-value.red { color: #ff4757; }
.stat-value.cyan { color: #00d4ff; }

.stat-label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
}

/* ===== Metrics ===== */
.metrics-list {
  padding: 12px;
}

.metric-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid rgba(0, 212, 255, 0.1);
}

.metric-item:last-child {
  border-bottom: none;
}

.metric-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
}

.metric-value {
  font-size: 16px;
  font-weight: 600;
  color: #00d4ff;
}

.metric-value small {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  margin-left: 2px;
}

/* ===== Center Panel / Map ===== */
.center-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.map-container {
  flex: 1;
  background: rgba(0, 30, 60, 0.6);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 4px 30px rgba(0, 212, 255, 0.1);
}

.map-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: rgba(0, 50, 100, 0.3);
  border-bottom: 1px solid rgba(0, 212, 255, 0.2);
}

.map-title {
  font-size: 15px;
  font-weight: 600;
}

.map-legend {
  display: flex;
  gap: 16px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

.legend-item .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.legend-item.online .dot { background: #00ff88; box-shadow: 0 0 6px #00ff88; }
.legend-item.offline .dot { background: #666; }
.legend-item.alarm .dot { background: #ff4757; box-shadow: 0 0 6px #ff4757; }

.factory-map {
  flex: 1;
  position: relative;
  background: 
    radial-gradient(ellipse at center, rgba(0, 100, 150, 0.2) 0%, transparent 70%),
    linear-gradient(0deg, rgba(0, 212, 255, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 212, 255, 0.05) 1px, transparent 1px);
  background-size: 100% 100%, 40px 40px, 40px 40px;
  overflow: hidden;
}

.map-grid {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
}

/* ===== Device Markers ===== */
.device-marker {
  position: absolute;
  transform: translate(-50%, -50%);
  cursor: pointer;
  z-index: 10;
}

.device-marker .marker-pulse {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(102, 102, 102, 0.3);
}

.device-marker.online .marker-pulse {
  background: rgba(0, 255, 136, 0.3);
  animation: pulse 2s infinite;
}

.device-marker.alarm .marker-pulse {
  background: rgba(255, 71, 87, 0.5);
  animation: alarm-pulse 0.5s infinite;
}

@keyframes pulse {
  0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
  50% { transform: translate(-50%, -50%) scale(1.5); opacity: 0; }
}

@keyframes alarm-pulse {
  0%, 100% { transform: translate(-50%, -50%) scale(1); }
  50% { transform: translate(-50%, -50%) scale(1.3); }
}

.marker-icon {
  position: relative;
  width: 32px;
  height: 32px;
  background: rgba(0, 50, 100, 0.8);
  border: 2px solid #666;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
  transition: all 0.3s;
}

.device-marker.online .marker-icon {
  border-color: #00ff88;
  box-shadow: 0 0 15px rgba(0, 255, 136, 0.5);
}

.device-marker.alarm .marker-icon {
  border-color: #ff4757;
  box-shadow: 0 0 15px rgba(255, 71, 87, 0.5);
}

.device-marker.selected .marker-icon {
  transform: scale(1.2);
  border-color: #00d4ff;
  box-shadow: 0 0 20px rgba(0, 212, 255, 0.8);
}

.device-marker:hover .marker-icon {
  transform: scale(1.1);
}

/* ===== Tooltip ===== */
.marker-tooltip {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-bottom: 10px;
  min-width: 180px;
  background: rgba(0, 30, 60, 0.95);
  border: 1px solid rgba(0, 212, 255, 0.5);
  border-radius: 10px;
  padding: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
  z-index: 100;
}

.marker-tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 8px solid transparent;
  border-top-color: rgba(0, 212, 255, 0.5);
}

.tooltip-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.2);
}

.tooltip-name {
  font-weight: 600;
  font-size: 14px;
}

.tooltip-status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(102, 102, 102, 0.3);
}

.tooltip-status.online {
  background: rgba(0, 255, 136, 0.2);
  color: #00ff88;
}

.tooltip-body .tooltip-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  padding: 4px 0;
}

.tooltip-row .value {
  color: #00d4ff;
  font-weight: 600;
}

.tooltip-row .value.alarm {
  color: #ff4757;
}

/* ===== Right Panel ===== */
.device-list-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.device-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.device-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  margin-bottom: 8px;
  background: rgba(0, 50, 100, 0.3);
  border-radius: 10px;
  border: 1px solid rgba(0, 212, 255, 0.1);
  cursor: pointer;
  transition: all 0.3s;
}

.device-card:hover {
  background: rgba(0, 100, 150, 0.4);
  border-color: rgba(0, 212, 255, 0.3);
}

.device-card.online {
  border-left: 3px solid #00ff88;
}

.device-card.alarm {
  border-left: 3px solid #ff4757;
  background: rgba(255, 71, 87, 0.1);
}

.device-icon {
  font-size: 20px;
}

.device-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.device-name {
  font-size: 13px;
  font-weight: 600;
}

.device-instrument {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #00d4ff;
  margin-bottom: 2px;
}

.instrument-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.device-location {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
}

.device-reading {
  text-align: right;
}

.reading-value {
  font-size: 18px;
  font-weight: 700;
  color: #00ff88;
}

.reading-value.alarm {
  color: #ff4757;
}

.reading-unit {
  display: block;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.5);
}

/* ===== Alarm Panel ===== */
.alarm-panel {
  max-height: 200px;
}

.alarm-list {
  padding: 8px;
  max-height: 150px;
  overflow-y: auto;
}

.alarm-item {
  display: flex;
  gap: 10px;
  padding: 8px 10px;
  margin-bottom: 6px;
  background: rgba(255, 71, 87, 0.1);
  border-left: 3px solid #ff4757;
  border-radius: 6px;
  font-size: 12px;
}

.alarm-time {
  color: rgba(255, 255, 255, 0.5);
}

.alarm-sn {
  flex: 1;
}

.alarm-value {
  color: #ff4757;
  font-weight: 600;
}

.no-data {
  text-align: center;
  padding: 20px;
  color: rgba(255, 255, 255, 0.4);
  font-size: 13px;
}

/* ===== Footer / Chart ===== */
.screen-footer {
  height: 200px;
  padding: 0 16px 16px;
}

.chart-container {
  height: 100%;
  background: rgba(0, 30, 60, 0.6);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.15);
}

.chart-title {
  font-size: 14px;
  font-weight: 600;
}

.chart-tabs {
  display: flex;
  gap: 8px;
}

.chart-tab {
  padding: 6px 16px;
  background: transparent;
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 16px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.3s;
}

.chart-tab:hover {
  background: rgba(0, 212, 255, 0.1);
}

.chart-tab.active {
  background: rgba(0, 212, 255, 0.2);
  border-color: #00d4ff;
  color: #00d4ff;
}

.trend-chart {
  flex: 1;
  min-height: 0;
}

/* ===== Scrollbar ===== */
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb {
  background: rgba(0, 212, 255, 0.3);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 212, 255, 0.5);
}
</style>
