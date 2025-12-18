<template>
  <div class="dashboard">
    <!-- Header Bar -->
    <header class="header">
      <div class="header-left"></div>
      <div class="header-center">
        <h1>元芯物联网智慧云平台</h1>
      </div>
      <div class="header-right">
        <span class="loc">📍 {{ weather.location || '定位中...' }}</span>
        <span class="date">{{ currentDate }}</span>
        <span class="weather">{{ weather.desc }} {{ weather.temp }}°C</span>
      </div>
    </header>

    <!-- Main Content with Resizable Splitpanes -->
    <!-- Outer: Left+Center Area | Right Column (full height) -->
    <Splitpanes class="main-splitpanes" @resized="onHorizontalResize">
      <!-- Left + Center with vertical split -->
      <Pane :size="panelSizes.left + panelSizes.center" min-size="50">
        <Splitpanes horizontal @resized="onVerticalResize">
          <!-- Top: Left + Center columns -->
          <Pane :size="panelSizes.mainHeight" min-size="30">
            <Splitpanes @resized="onLeftCenterResize">
              <!-- LEFT COLUMN -->
              <Pane :size="panelSizes.leftInner || 35" min-size="20" max-size="50">
                <section class="col col-left">
        <!-- Panel: 仪表概览 -->
        <div class="panel panel-sm">
          <div class="safety-header">
            <div class="header-deco"><div class="deco-dot"></div><div class="deco-ring"></div></div>
            <div class="header-text">仪表概览</div>
            <div class="header-sub">INSTRUMENT OVERVIEW</div>
          </div>
          <div class="instruments-grid">
            <div class="instrument-card" v-for="inst in displayedInstruments" :key="inst.id" :style="{ '--card-color': inst.color || '#22d3ee' }">
              <div class="inst-header">
                <span class="inst-name">{{ inst.name }}</span>
                <span class="inst-color" :style="{ background: inst.color || '#22d3ee' }"></span>
              </div>
              <div class="inst-desc">{{ inst.description || '监控仪表' }}</div>
              <div class="inst-footer">
                <span class="sensor-count">{{ inst.sensor_count || 0 }}</span>
                <span class="sensor-types">传感器</span>
              </div>
            </div>
            <div v-if="!displayedInstruments.length" class="empty-instruments">
              暂无显示的仪表<br/><small>请在管理界面→大屏显示管理中设置</small>
            </div>
          </div>
        </div>
        
        <!-- Panel: 安全监管 -->
        <div class="panel panel-safety">
          <div class="safety-header">
            <div class="header-deco">
              <div class="deco-dot"></div>
              <div class="deco-ring"></div>
            </div>
            <div class="header-text">安全监管</div>
            <div class="header-sub">SAFETY SUPERVISION</div>
          </div>
          <div class="safety-body">
            <!-- Left: Gauge -->
            <div class="safety-left">
              <div class="gauge-container">
                <!-- Rotating Tech Ring -->
                <div class="tech-ring"></div>
                <v-chart class="gauge-chart" :option="gaugeOption" autoresize />
                <div class="gauge-overlay">
                  <span class="g-val" :style="{ color: scoreColor.end }">{{ overallScore }}<small>分</small></span>
                  <span class="g-label">综合评分</span>
                </div>
              </div>
            </div>
            
            <!-- Right: Progress Bars -->
            <div class="safety-right">
              <!-- Bar 1: Online Rate -->
              <div class="progress-item">
                <div class="p-header">
                  <span class="p-label">在线率</span>
                  <span class="p-val">{{ safetyPercent }}%</span>
                </div>
                <div class="p-track">
                  <div class="p-bar bar-blue" :style="{ width: safetyPercent + '%' }"></div>
                </div>
              </div>

              <!-- Bar 2: Alarm Handling Rate -->
              <div class="progress-item">
                <div class="p-header">
                  <span class="p-label">报警处理率</span>
                  <span class="p-val">{{ alarmHandlingPercent }}%</span>
                </div>
                <div class="p-track">
                  <div class="p-bar bar-orange" :style="{ width: alarmHandlingPercent + '%' }"></div>
                </div>
              </div>

              <!-- Bar 3: Device Health Rate -->
              <div class="progress-item">
                <div class="p-header">
                  <span class="p-label">设备健康率</span>
                  <span class="p-val">{{ healthPercent }}%</span>
                </div>
                <div class="p-track">
                  <div class="p-bar bar-green" :style="{ width: healthPercent + '%' }"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Panel: AI 智能总结 -->
        <div class="panel panel-ai">
          <div class="safety-header">
            <div class="header-deco"><div class="deco-dot"></div><div class="deco-ring"></div></div>
            <div class="header-text">AI 智能分析</div>
            <div class="header-sub">AI ANALYSIS</div>
          </div>
          <div class="ai-content">
            <div class="ai-summary">
              <p v-if="aiLoading" class="ai-thinking">{{ aiThinking }}</p>
              <p v-else-if="aiSummary">{{ aiSummary }}</p>
              <p v-else class="ai-error">暂无分析数据</p>
            </div>
          </div>
        </div>
      </section>
              </Pane>

              <!-- CENTER COLUMN -->
              <Pane :size="panelSizes.centerInner || 65" min-size="40">
      <section class="col col-center">
        <!-- Top: Alert + Map -->
        <div class="center-top">
          <div class="map-box" :style="mapBoxStyle">
            <div class="map-3d">
              <div
                v-for="inst in displayedInstruments"
                :key="inst.id"
                class="marker"
                :class="{ alarm: instrumentHasAlarm(inst.id) }"
                :style="{ left: instrumentPos(inst.id, 'x') + '%', top: instrumentPos(inst.id, 'y') + '%' }"
                @click="selectedInstrument = selectedInstrument === inst.id ? null : inst.id"
              >
                <span class="dot"></span>
                <span class="name">{{ inst.name }}</span>
                <div class="tooltip" v-if="selectedInstrument === inst.id">
                  <p><b>{{ inst.name }}</b></p>
                  <p v-if="inst.description">{{ inst.description }}</p>
                  <p>传感器数量: {{ getInstrumentDevices(inst.id).length }}</p>
                  <p :class="{ 'alarm-text': instrumentHasAlarm(inst.id) }">
                    状态: {{ instrumentHasAlarm(inst.id) ? '⚠️ 告警中' : '✅ 正常' }}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
        <!-- Bottom: Metrics row -->
        <div class="metrics-row">
          <div class="metric" v-for="m in metrics" :key="m.label">
            <div class="m-label">{{ m.label }}</div>
            <div class="m-value">{{ m.value }}<small>{{ m.unit }}</small></div>
          </div>
        </div>
      </section>
              </Pane>
            </Splitpanes>
          </Pane>
          
          <!-- Bottom: Trend Chart (spans left+center only) -->
          <Pane :size="panelSizes.trendHeight" min-size="15" max-size="50">
            <div class="trend-section">
              <div class="panel trend-panel">
                <div class="safety-header">
                  <div class="header-deco"><div class="deco-dot"></div><div class="deco-ring"></div></div>
                  <div class="header-text">污染物趋势图</div>
                  <div class="header-sub">POLLUTANT TRENDS</div>
                  <span class="tabs" style="margin-left: auto;">
                    <button class="tab active">今日</button>
                    <button class="tab">昨日</button>
                  </span>
                </div>
                <v-chart class="trend-chart" :option="trendOption" autoresize />
              </div>
            </div>
          </Pane>
        </Splitpanes>
      </Pane>

      <!-- RIGHT COLUMN (full height) -->
      <Pane :size="panelSizes.right" min-size="15" max-size="35">
        <section class="col col-right col-right-full">
          <!-- Panel: 天气概况 -->
          <div class="panel weather-panel">
            <div class="safety-header">
              <div class="header-deco"><div class="deco-dot"></div><div class="deco-ring"></div></div>
              <div class="header-text">天气概况</div>
              <div class="header-sub">WEATHER OVERVIEW</div>
            </div>
            <div class="weather-main">
              <span class="icon">{{ weather.icon }}</span>
              <span class="temp">{{ weather.temp }}<small>°C</small></span>
            </div>
            <div class="weather-details">
              <div><span>湿度</span><b>{{ weather.humidity }}%</b></div>
              <div><span>风速</span><b>{{ weather.wind }}</b></div>
              <div><span>空气质量</span><b class="good">优</b></div>
            </div>
          </div>
          <!-- Panel: 设备状态 -->
          <div class="panel device-panel">
            <div class="safety-header">
              <div class="header-deco"><div class="deco-dot"></div><div class="deco-ring"></div></div>
              <div class="header-text">设备状态</div>
              <div class="header-sub">DEVICE STATUS</div>
            </div>
            <div class="device-list">
              <div class="device-item" v-for="d in devices" :key="d.sn">
                <span class="status-dot" :class="d.status"></span>
                <span class="d-name">{{ d.name || d.sn }}</span>
                <span class="d-val" :class="{ alarm: (d.ppm||0) > 1000 }">{{ d.ppm?.toFixed(0) }} <small>{{ d.unit }}</small></span>
              </div>
            </div>
          </div>
          <!-- Panel: 最新报警 (fills remaining space) -->
          <div class="panel alarm-panel alarm-panel-fill">
            <div class="safety-header">
              <div class="header-deco"><div class="deco-dot"></div><div class="deco-ring"></div></div>
              <div class="header-text">最新报警</div>
              <div class="header-sub">LATEST ALARMS</div>
            </div>
            <div class="alarm-list">
              <div class="alarm-item" v-for="a in alarms" :key="a.id">
                <span class="a-time">{{ fmtTime(a.time) }}</span>
                <span class="a-sn">{{ a.sn }}</span>
                <span class="a-val">{{ a.value.toFixed(1) }}</span>
              </div>
              <div v-if="!alarms.length" class="empty">暂无报警</div>
            </div>
          </div>
        </section>
      </Pane>
    </Splitpanes>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, provide } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, LineChart, GaugeChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import VChart, { THEME_KEY } from 'vue-echarts'
import { dashboardApi, alarmsApi, instrumentsApi, configApi } from '../../api'
// @ts-ignore - splitpanes doesn't have type declarations
import { Splitpanes, Pane } from 'splitpanes'
import 'splitpanes/dist/splitpanes.css'

use([CanvasRenderer, PieChart, LineChart, GaugeChart, GridComponent, TooltipComponent])
provide(THEME_KEY, 'dark')

// Panel size persistence with localStorage
const LAYOUT_STORAGE_KEY = 'dashboard-layout-sizes'
const defaultSizes = { 
  left: 75, // left+center combined (horizontal outer split)
  center: 0, // unused in new layout
  right: 25, // right column (horizontal outer split)
  mainHeight: 70, // main content area (vertical inner split)
  trendHeight: 30, // trend chart (vertical inner split)
  leftInner: 35, // left column within left+center (horizontal inner split)
  centerInner: 65 // center column within left+center (horizontal inner split)
}
const panelSizes = reactive({ ...defaultSizes })

function loadLayoutSizes() {
  try {
    const saved = localStorage.getItem(LAYOUT_STORAGE_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)
      // Merge with defaults, allowing new keys
      for (const key of Object.keys(defaultSizes)) {
        if (parsed[key] !== undefined) {
          (panelSizes as Record<string, number>)[key] = parsed[key]
        }
      }
    }
  } catch (e) {
    console.warn('Failed to load layout sizes:', e)
  }
}

function saveLayoutSizes() {
  try {
    localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify(panelSizes))
  } catch (e) {
    console.warn('Failed to save layout sizes:', e)
  }
}

// Outer horizontal: left+center area vs right column
function onHorizontalResize(panes: Array<{ size: number }>) {
  if (panes && panes.length >= 2) {
    panelSizes.left = panes[0]?.size ?? panelSizes.left
    panelSizes.right = panes[1]?.size ?? panelSizes.right
    saveLayoutSizes()
  }
}

// Vertical: main content vs trend chart
function onVerticalResize(panes: Array<{ size: number }>) {
  if (panes && panes.length >= 2) {
    panelSizes.mainHeight = panes[0]?.size ?? panelSizes.mainHeight
    panelSizes.trendHeight = panes[1]?.size ?? panelSizes.trendHeight
    saveLayoutSizes()
  }
}

// Inner horizontal: left column vs center column
function onLeftCenterResize(panes: Array<{ size: number }>) {
  if (panes && panes.length >= 2) {
    panelSizes.leftInner = panes[0]?.size ?? panelSizes.leftInner
    panelSizes.centerInner = panes[1]?.size ?? panelSizes.centerInner
    saveLayoutSizes()
  }
}

interface Device { sn: string; name: string | null; ppm: number | null; temp: number | null; status: string; unit: string; instrument_id?: number | null; high_limit?: number }
interface Alarm { id: number; time: string; sn: string; value: number }
interface Instrument { id: number; name: string; description: string | null; color: string | null; is_displayed?: boolean; sensor_count?: number; sensor_types?: string; pos_x?: number; pos_y?: number }
interface ScreenStats {
  devices_total: number
  devices_online: number
  devices_alarm: number
  alarms_today: number
  alarms_confirmed_today: number
}

const currentDate = ref('')
const devices = ref<Device[]>([])
const alarms = ref<Alarm[]>([])
const instruments = ref<Instrument[]>([])
const selectedInstrument = ref<number | null>(null)
const trend = ref<number[]>([])
const trendLabels = ref<string[]>([])
const stats = reactive<ScreenStats>({ devices_total: 0, devices_online: 0, devices_alarm: 0, alarms_today: 0, alarms_confirmed_today: 0 })
const alarmStats = reactive({ today: 0, total: 0 })
const weather = reactive({ temp: '--', humidity: '--', wind: '--', desc: '--', location: '', icon: '🌤️' })
const aiSummary = ref('')
const aiLoading = ref(false)
const aiThinking = ref('正在分析数据...')

// Filter instruments by is_displayed field
const displayedInstruments = computed(() => {
  // Filter for instruments where is_displayed is explicitly true
  return instruments.value.filter((i: Instrument) => i.is_displayed === true)
})

// Get devices belonging to a specific instrument
function getInstrumentDevices(instrumentId: number): Device[] {
  return devices.value.filter((d: Device) => d.instrument_id === instrumentId)
}

// Check if any device in the instrument has alarm (ppm > high_limit or > 1000)
function instrumentHasAlarm(instrumentId: number): boolean {
  const instrumentDevices = getInstrumentDevices(instrumentId)
  return instrumentDevices.some((d: Device) => {
    const limit = d.high_limit || 1000
    return (d.ppm || 0) > limit
  })
}

// Get position for instrument marker from database
function instrumentPos(id: number, axis: 'x' | 'y'): number {
  const inst = instruments.value.find((i: Instrument) => i.id === id)
  if (inst) {
    return axis === 'x' ? (inst.pos_x || 50) : (inst.pos_y || 50)
  }
  // Fallback: generate position based on ID
  const seed = axis === 'x' ? id * 13 : id * 17 + 7
  return 15 + (seed % 70)
}

const safetyPercent = computed(() => {
  if (!stats.devices_total) return 0
  return Math.round((stats.devices_online / stats.devices_total) * 100)
})

const alarmHandlingPercent = computed(() => {
  if (!stats.alarms_today) return 100
  return Math.round((stats.alarms_confirmed_today / stats.alarms_today) * 100)
})

const healthPercent = computed(() => {
  if (!stats.devices_total) return 100
  // Health rate = (Total - Alarming) / Total
  return Math.round(((stats.devices_total - stats.devices_alarm) / stats.devices_total) * 100)
})

const overallScore = computed(() => {
  // Weights: Online(30%), Health(40%), AlarmHandling(30%)
  const s = safetyPercent.value || 0
  const h = healthPercent.value || 0
  const a = alarmHandlingPercent.value || 0
  
  // Initial state check
  if (!stats.devices_total && !stats.alarms_today) return 100 
  
  return Math.round((s * 0.3) + (h * 0.4) + (a * 0.3))
})

const scoreColor = computed(() => {
  const s = overallScore.value
  if (s >= 90) return { start: '#34d399', end: '#10b981', shadow: 'rgba(52,211,153,0.8)', stop1: 'rgba(16,185,129,0.8)', stop2: 'rgba(16,185,129,0.2)' } 
  if (s >= 70) return { start: '#fbbf24', end: '#f59e0b', shadow: 'rgba(251,191,36,0.8)', stop1: 'rgba(251,191,36,0.8)', stop2: 'rgba(251,191,36,0.2)' }
  return { start: '#f87171', end: '#ef4444', shadow: 'rgba(248,113,113,0.8)', stop1: 'rgba(248,113,113,0.8)', stop2: 'rgba(248,113,113,0.2)' }
})

const todayAlarmCount = computed(() => alarmStats.today)

const gaugeOption = computed(() => ({
  backgroundColor: 'transparent',
  series: [
    // Outer breathing glow ring (blue, subtle)
    {
      type: 'gauge',
      startAngle: 90, endAngle: -270, radius: '98%',
      pointer: { show: false }, progress: { show: false }, detail: { show: false },
      axisLine: { lineStyle: { width: 2, color: [[1, 'rgba(59,130,246,0.3)']] } },
      splitLine: { show: false },
      axisTick: { show: true, splitNumber: 1, length: 6, lineStyle: { width: 1, color: 'rgba(59,130,246,0.5)' } },
      axisLabel: { show: false },
      data: []
    },
    // Second outer ring (darker blue)
    {
      type: 'gauge',
      startAngle: 90, endAngle: -270, radius: '92%',
      pointer: { show: false }, progress: { show: false }, detail: { show: false },
      axisLine: { lineStyle: { width: 1, color: [[1, 'rgba(30,64,175,0.4)']] } },
      splitLine: { show: false },
      axisTick: { show: true, splitNumber: 2, length: 3, lineStyle: { width: 1, color: 'rgba(59,130,246,0.3)' } },
      axisLabel: { show: false },
      data: []
    },
    // Inner tick bars (gradient based on score)
    {
      type: 'gauge',
      startAngle: 90, endAngle: -270, radius: '75%',
      pointer: { show: false }, progress: { show: false }, detail: { show: false },
      axisLine: { show: false },
      splitLine: { 
        show: true, 
        length: 15, 
        distance: 2,
        lineStyle: { 
          width: 3, 
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: scoreColor.value.stop1 },
              { offset: 1, color: scoreColor.value.stop2 }
            ]
          }
        } 
      },
      axisTick: { show: false },
      axisLabel: { show: false },
      data: [{ value: overallScore.value }]
    },
    // Main progress ring (gradient based on score)
    {
      type: 'gauge',
      startAngle: 90, endAngle: -270, radius: '85%',
      pointer: { show: false },
      progress: { 
        show: true, 
        width: 6, 
        roundCap: true, 
        itemStyle: { 
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 1, y2: 0,
            colorStops: [
              { offset: 0, color: scoreColor.value.start },
              { offset: 1, color: scoreColor.value.end }
            ]
          },
          shadowColor: scoreColor.value.shadow,
          shadowBlur: 15
        } 
      },
      axisLine: { lineStyle: { width: 6, color: [[1, 'rgba(30,64,175,0.2)']] } },
      splitLine: { show: false },
      axisTick: { show: false },
      axisLabel: { show: false },
      data: [{ value: overallScore.value }],
      detail: { show: false }
    }
  ]
}))

const topPollutant = computed(() => {
  const sorted = [...devices.value].sort((a, b) => (b.ppm || 0) - (a.ppm || 0))
  const top = sorted[0]
  return { name: top?.name || '-', value: top?.ppm?.toFixed(1) || '-', unit: top?.unit || 'ppm' }
})

const metrics = computed(() => {
  const online = devices.value.filter(d => d.status === 'online')
  const avgT = online.length ? online.reduce((s, d) => s + (d.temp || 0), 0) / online.length : 0
  return [
    { label: 'PM2.5', value: '25', unit: 'ug/m³' },
    { label: 'H2', value: '0.05', unit: 'ppm' },
    { label: 'CH4', value: '0.12', unit: 'ppm' },
    { label: 'VOCs', value: '0.40', unit: 'ppm' },
    { label: 'Temp', value: avgT.toFixed(1), unit: '°C' },
    { label: 'Humi', value: '50', unit: '%' }
  ]
})

const trendOption = computed(() => ({
  grid: { top: 20, right: 15, bottom: 30, left: 45 },
  xAxis: { type: 'category', data: trendLabels.value, axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: '#64748b', fontSize: 11 }, splitLine: { show: false } },
  yAxis: { type: 'value', axisLine: { show: false }, axisTick: { show: false }, splitLine: { lineStyle: { color: 'rgba(100,116,139,0.15)', type: 'dashed' } }, axisLabel: { color: '#64748b', fontSize: 11 } },
  series: [{
    type: 'line', data: trend.value, smooth: true, symbol: 'none',
    lineStyle: { color: '#22d3ee', width: 3, shadowColor: 'rgba(34,211,238,0.5)', shadowBlur: 10 },
    areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(34,211,238,0.4)' }, { offset: 0.5, color: 'rgba(34,211,238,0.15)' }, { offset: 1, color: 'rgba(34,211,238,0)' }] } }
  }]
}))

function fmtTime(t: string) { return new Date(t).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }

async function fetchData() {
  try {
    const [st, dv, al, instRes, alStats] = await Promise.all([
      dashboardApi.stats(),
      dashboardApi.realtime(),
      alarmsApi.list({ page: 1, size: 10 }),
      instrumentsApi.list(),
      alarmsApi.stats().catch(() => ({ data: { today: 0, total: 0 } }))
    ])
    Object.assign(stats, st.data)
    devices.value = dv.data || []
    alarms.value = al.data?.data || []
    
    // Update alarm stats - try to get today count from API
    if (alStats.data) {
      alarmStats.today = alStats.data.today || alStats.data.today_count || 0
      alarmStats.total = alStats.data.total || 0
    }
    
    // Process instruments with sensor aggregation
    // API returns { total, data: [...] } so access .data.data
    const instList = instRes.data?.data || instRes.data || []
    console.log('Loaded instruments:', instList.length, instList)
    // Use backend sensor_count directly - it's calculated from instrument_id relation
    instruments.value = instList.map((inst: Instrument) => ({
      ...inst,
      sensor_count: inst.sensor_count || 0,
      sensor_types: '传感器设备'
    }))
    
    const avg = devices.value.reduce((s: number, d: Device) => s + (d.ppm || 0), 0) / (devices.value.length || 1)
    trend.value.push(avg); if (trend.value.length > 20) trend.value.shift()
    trendLabels.value.push(new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })); if (trendLabels.value.length > 20) trendLabels.value.shift()
  } catch (e) { console.error(e) }
}

async function fetchWeather() {
  if (!navigator.geolocation) return
  navigator.geolocation.getCurrentPosition(async p => {
    try {
      const r = await fetch(`https://wttr.in/${p.coords.latitude},${p.coords.longitude}?format=j1`)
      const j = await r.json(); const c = j.current_condition[0]
      weather.temp = c.temp_C; weather.humidity = c.humidity
      weather.wind = c.winddir16Point + ' ' + c.windspeedKmph + 'km/h'
      weather.desc = c.weatherDesc[0].value; weather.location = j.nearest_area[0].areaName[0].value
      weather.icon = ['113'].includes(c.weatherCode) ? '☀️' : ['116','119','122'].includes(c.weatherCode) ? '⛅' : '🌥️'
    } catch {}
  })
}

async function fetchAI() {
  if (aiLoading.value) return
  aiLoading.value = true
  aiThinking.value = '正在分析数据...'
  
  try {
    // TODO: Configure OpenAI API endpoint and key in environment
    const apiUrl = '/api/ai/chat'
    const prompt = `作为IoT智能分析师，请简要总结以下数据（50字以内）：
设备总数: ${stats.devices_total}
在线设备: ${stats.devices_online}
离线设备: ${stats.devices_total - stats.devices_online}
安全率: ${safetyPercent.value}%
今日报警: ${todayAlarmCount.value}次
最高污染物: ${topPollutant.value.name} (${topPollutant.value.value} ${topPollutant.value.unit})`

    const res = await fetch(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'gpt-3.5-turbo',
        messages: [{ role: 'user', content: prompt }],
        max_tokens: 100
      })
    })
    
    if (res.ok) {
      const data = await res.json()
      aiSummary.value = data.choices?.[0]?.message?.content || '分析完成，系统运行正常。'
    } else {
      // Fallback to local summary
      const onlineRate = safetyPercent.value
      if (onlineRate >= 90) {
        aiSummary.value = `系统运行良好，${stats.devices_online}/${stats.devices_total}设备在线，安全率${onlineRate}%。`
      } else if (onlineRate >= 70) {
        aiSummary.value = `注意：${stats.devices_total - stats.devices_online}台设备离线，建议检查网络连接。`
      } else {
        aiSummary.value = `警告：大量设备离线，安全率仅${onlineRate}%，请立即排查！`
      }
    }
  } catch {
    aiSummary.value = `当前${stats.devices_online}台设备在线，今日报警${todayAlarmCount.value}次。`
  } finally {
    aiLoading.value = false
  }
}

let timer: ReturnType<typeof setInterval>
let aiTimer: ReturnType<typeof setInterval>

// Screen Background
const screenBgUrl = ref('')
const mapBoxStyle = computed(() => {
  if (screenBgUrl.value) {
    return {
      backgroundImage: `url(${screenBgUrl.value})`,
      backgroundSize: '100% 100%',
      backgroundPosition: 'center',
      backgroundRepeat: 'no-repeat'
    }
  }
  return {}
})

async function fetchScreenBg() {
  try {
    const res = await configApi.getScreenBg()
    if (res.data?.image_url) {
      screenBgUrl.value = res.data.image_url
    }
  } catch (e) {
    console.log('No screen background configured')
  }
}

onMounted(() => {
  loadLayoutSizes() // Restore saved panel sizes
  currentDate.value = new Date().toLocaleDateString('zh-CN')
  fetchData(); fetchWeather(); fetchAI(); fetchScreenBg()
  timer = setInterval(() => { currentDate.value = new Date().toLocaleDateString('zh-CN'); fetchData() }, 3000)
  aiTimer = setInterval(fetchAI, 60000) // Refresh AI summary every minute
})
onUnmounted(() => { clearInterval(timer); clearInterval(aiTimer) })
</script>

<style scoped>
* { box-sizing: border-box; }

/* ========== GLOBAL: Deep Space Blue with Grid Texture ========== */
.dashboard {
  width: 100vw; height: 100vh;
  background: 
    linear-gradient(rgba(15,23,42,0.97), rgba(15,23,42,0.97)),
    repeating-linear-gradient(0deg, transparent, transparent 40px, rgba(34,211,238,0.03) 40px, rgba(34,211,238,0.03) 41px),
    repeating-linear-gradient(90deg, transparent, transparent 40px, rgba(34,211,238,0.03) 40px, rgba(34,211,238,0.03) 41px),
    linear-gradient(to bottom, #0f172a, #020617);
  color: #cbd5e1;
  font-family: 'Rajdhani', 'Microsoft YaHei', sans-serif;
  display: flex; flex-direction: column; overflow: hidden;
}

/* ========== HEADER ========== */
.header {
  height: 60px; display: flex; align-items: center; justify-content: space-between;
  padding: 0 30px;
  background: linear-gradient(90deg, rgba(15,23,42,0.9), rgba(30,41,59,0.7), rgba(15,23,42,0.9));
  border-bottom: 1px solid rgba(34,211,238,0.2);
  position: relative;
}
.header-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  text-align: center;
}
.header h1 {
  margin: 0; font-size: 28px; font-weight: 700; letter-spacing: 4px;
  color: #22d3ee;
  text-shadow: 0 0 20px rgba(34,211,238,0.5), 0 0 40px rgba(34,211,238,0.3);
  font-family: 'Orbitron', sans-serif;
  text-transform: uppercase;
}
.header p { display: none; }
.header-right { display: flex; gap: 20px; font-size: 15px; color: #94a3b8; font-family: 'Chakra Petch', monospace; font-weight: 500; }
.header-right .loc { color: #22d3ee; text-shadow: 0 0 8px rgba(34,211,238,0.4); }
.header-right .date { color: #64748b; }
.header-right .weather { color: #22d3ee; text-shadow: 0 0 8px rgba(34,211,238,0.4); }

/* ========== SPLITPANES LAYOUT ========== */
.main-splitpanes {
  flex: 1;
  min-height: 0;
}
/* Remove grid layout since we're using splitpanes */
.main { display: none; } /* Not used anymore */

.col { display: flex; flex-direction: column; gap: 12px; min-height: 0; padding: 8px; height: 100%; overflow-y: auto; }
/* Left column panels should be more compact */
.col-left { gap: 8px; }
.col-left .panel { flex: 0 0 auto; }

/* Splitpanes splitter styling - make them more visible and on-theme */
:deep(.splitpanes__splitter) {
  background: linear-gradient(90deg, transparent 45%, rgba(34,211,238,0.3) 50%, transparent 55%);
  position: relative;
}
:deep(.splitpanes__splitter:hover) {
  background: linear-gradient(90deg, transparent 40%, rgba(34,211,238,0.6) 50%, transparent 60%);
}
:deep(.splitpanes--horizontal > .splitpanes__splitter) {
  height: 8px;
  background: linear-gradient(180deg, transparent 45%, rgba(34,211,238,0.3) 50%, transparent 55%);
}
:deep(.splitpanes--horizontal > .splitpanes__splitter:hover) {
  background: linear-gradient(180deg, transparent 40%, rgba(34,211,238,0.6) 50%, transparent 60%);
}

/* ========== TREND SECTION: spans left+center only ========== */
.trend-section {
  width: 100%; height: 100%; padding: 8px;
}
.trend-section .trend-panel {
  flex: 1; height: 100%; 
  border-radius: 8px;
}

/* ========== RIGHT COLUMN: Full height ========== */
.col-right-full {
  height: 100%;
}
.col-right-full .alarm-panel-fill {
  flex: 1; /* Fill remaining vertical space */
  min-height: 200px;
}

/* ========== PANEL: Corner Decorations + Glassmorphism ========== */
.panel {
  position: relative;
  background: rgba(15,23,42,0.6);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: none;
  border-radius: 8px;
  display: flex; flex-direction: column; flex: 1; min-height: 0;
  overflow: hidden;
}
/* Four corner L-shaped decorations */
.panel::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  pointer-events: none;
  background:
    linear-gradient(135deg, #22d3ee 0%, #22d3ee 2px, transparent 2px, transparent 20px, transparent 20px),
    linear-gradient(225deg, #22d3ee 0%, #22d3ee 2px, transparent 2px, transparent 20px, transparent 20px),
    linear-gradient(315deg, #22d3ee 0%, #22d3ee 2px, transparent 2px, transparent 20px, transparent 20px),
    linear-gradient(45deg, #22d3ee 0%, #22d3ee 2px, transparent 2px, transparent 20px, transparent 20px);
  background-size: 20px 20px;
  background-position: top left, top right, bottom right, bottom left;
  background-repeat: no-repeat;
}
.panel-title {
  position: relative;
  padding: 10px 14px; font-size: 13px; font-weight: 600; color: #22d3ee;
  background: linear-gradient(90deg, rgba(34,211,238,0.1), transparent);
  border-bottom: 1px solid rgba(34,211,238,0.1);
  display: flex; justify-content: space-between; align-items: center;
}
.panel-title::before {
  content: '';
  position: absolute; left: 0; top: 50%; transform: translateY(-50%);
  width: 3px; height: 60%; background: #22d3ee;
  box-shadow: 0 0 10px rgba(34,211,238,0.5);
}

/* Shrunk panels for left column */
.panel-sm { flex: 0 0 auto; max-height: 35%; }

/* AI Panel styling */
.panel-ai { flex: 1; min-height: 80px; }
.ai-content {
  flex: 1; padding: 12px; display: flex; flex-direction: column;
  justify-content: center; overflow-y: auto;
}
.ai-summary {
  font-size: 12px; line-height: 1.6; color: #94a3b8;
}
.ai-summary p { margin: 0; }
.ai-thinking {
  color: #22d3ee; font-style: italic;
  animation: pulse-text 1.5s ease-in-out infinite;
}
.ai-error { color: #64748b; }
@keyframes pulse-text { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

/* ========== Safety Supervision Panel ========== */
/* ========== Safety Supervision Panel ========== */
.panel-safety { 
  display: flex; flex-direction: column; overflow: hidden;
  background: transparent;
  padding: 0; min-height: 240px;
}
.safety-header {
  height: 32px;
  background: linear-gradient(90deg, rgba(30,64,175,0.8) 0%, rgba(30,64,175,0) 100%);
  border-radius: 16px 0 0 16px;
  display: flex; align-items: center; padding: 0 12px;
  margin-bottom: 0;
  position: relative;
  border-left: 4px solid #3b82f6;
}
/* Deco ring similar to reference */
.safety-header::before {
    content: ''; position: absolute; left: -2px; top: 50%; transform: translateY(-50%);
    width: 14px; height: 14px; border: 2px solid #fbbf24; border-radius: 50%;
    z-index: 2; box-shadow: 0 0 5px #fbbf24; background: #1e3a8a;
}
.safety-header::after {
    content: ''; position: absolute; left: 1px; top: 50%; transform: translateY(-50%);
    width: 4px; height: 4px; background: #fbbf24; border-radius: 50%;
    z-index: 3;
}

.header-text {
  font-size: 18px; font-weight: 700; color: #fff;
  letter-spacing: 1px; margin-left: 10px; margin-right: 12px;
  font-family: 'Rajdhani', sans-serif;
  font-style: italic;
  text-transform: uppercase;
  text-shadow: 0 0 10px rgba(59,130,246,0.8);
}
.header-sub {
  font-size: 11px; color: #94a3b8; letter-spacing: 1px;
  font-family: 'Rajdhani', sans-serif; opacity: 0.7; margin-top: 3px;
  font-weight: 600;
}

/* Safety Body - Row Layout */
.safety-body {
  flex: 1; position: relative;
  display: flex; flex-direction: row; align-items: center; justify-content: space-between;
  min-height: 180px;
  padding: 10px 15px;
  gap: 15px;
}

/* Left: Gauge Area */
.safety-left {
  flex: 0 0 130px;
  display: flex; justify-content: center; align-items: center;
}
.gauge-container {
  width: 130px; height: 130px; position: relative;
  z-index: 10;
  display: flex; align-items: center; justify-content: center;
}
.tech-ring {
  position: absolute;
  top: 50%; left: 50%;
  width: 110%; height: 110%;
  transform: translate(-50%, -50%);
  border: 1px dashed rgba(34,211,238,0.3);
  border-radius: 50%;
  animation: spin 10s linear infinite;
  pointer-events: none;
}
.tech-ring::before {
  content: ''; position: absolute; top: -2px; left: 50%;
  width: 10px; height: 4px; background: #22d3ee;
  transform: translateX(-50%);
  box-shadow: 0 0 10px #22d3ee;
}
@keyframes spin { from { transform: translate(-50%, -50%) rotate(0deg); } to { transform: translate(-50%, -50%) rotate(360deg); } }

.gauge-chart { width: 100%; height: 100%; background: transparent !important; }
.gauge-overlay {
  position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  pointer-events: none; text-align: center;
}
.g-val {
  font-size: 28px; font-weight: 700; color: #fff; line-height: 1;
  text-shadow: 0 0 15px rgba(59,130,246,0.8);
  font-family: 'Chakra Petch', sans-serif;
}
.g-val small { font-size: 14px; font-weight: normal; color: #93c5fd; margin-left: 2px; }
.g-label {
  font-size: 12px; color: #94a3b8; margin-top: 6px; letter-spacing: 1px;
  font-family: 'Rajdhani', sans-serif; font-weight: 600; text-transform: uppercase;
}

/* Right: Progress Bars */
.safety-right {
  flex: 1;
  display: flex; flex-direction: column; justify-content: center;
  gap: 15px;
  padding-right: 5px;
}
.progress-item {
  display: flex; flex-direction: column; gap: 6px;
}
.p-header {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 13px; color: #cbd5e1;
}
.p-label { font-weight: 600; letter-spacing: 0.5px; font-family: 'Rajdhani', sans-serif; }
.p-val { font-family: 'Chakra Petch', monospace; font-weight: 700; font-size: 16px; }

/* Progress Track & Bar */
.p-track {
  height: 6px; width: 100%;
  background: rgba(30,41,59,0.5);
  border-radius: 3px;
  overflow: hidden;
  position: relative;
  box-shadow: inset 0 1px 2px rgba(0,0,0,0.3);
}
.p-bar {
  height: 100%;
  border-radius: 3px;
  position: relative;
  transition: width 1s ease-out;
}
/* Bar Gradients */
.bar-blue {
  background: linear-gradient(90deg, #3b82f6, #60a5fa);
  box-shadow: 0 0 8px rgba(59,130,246,0.5);
}
.bar-orange {
  background: linear-gradient(90deg, #f59e0b, #fbbf24);
  box-shadow: 0 0 8px rgba(245,158,11,0.5);
}
.bar-green {
  background: linear-gradient(90deg, #10b981, #34d399);
  box-shadow: 0 0 8px rgba(16,185,129,0.5);
}
/* Text colors matching bars */
.progress-item:nth-child(1) .p-val { color: #60a5fa; text-shadow: 0 0 8px rgba(96,165,250,0.4); }
.progress-item:nth-child(2) .p-val { color: #fbbf24; text-shadow: 0 0 8px rgba(251,191,36,0.4); }
.progress-item:nth-child(3) .p-val { color: #34d399; text-shadow: 0 0 8px rgba(52,211,153,0.4); }

/* Remove old stats styles */
.stats-col, .safety-stat, .s-val, .s-label { display: none; }

/* Remove the old decorative rings - now using the gauge series instead */

/* ========== LEFT COLUMN: Instruments Grid ========== */
.instruments-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  padding: 12px;
  flex: 1;
  overflow-y: auto;
  align-content: start;
}
.instrument-card {
  position: relative;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(34, 211, 238, 0.2);
  /* Tech shape with cut corners */
  clip-path: polygon(
    0 10px, 10px 0, 
    100% 0, 100% calc(100% - 10px), 
    calc(100% - 10px) 100%, 0 100%
  );
  padding: 12px;
  transition: all 0.3s ease;
  cursor: pointer;
  box-shadow: inset 0 0 20px rgba(0,0,0,0.5);
}
/* Corner accents using pseudo-elements */
.instrument-card::before {
  content: ''; position: absolute; top: 0; left: 0; width: 15px; height: 15px;
  border-top: 2px solid var(--card-color, #22d3ee);
  border-left: 2px solid var(--card-color, #22d3ee);
  border-top-left-radius: 4px; /* Fallback if clip-path removed */
}
.instrument-card::after {
  content: ''; position: absolute; bottom: 0; right: 0; width: 15px; height: 15px;
  border-bottom: 2px solid var(--card-color, #22d3ee);
  border-right: 2px solid var(--card-color, #22d3ee);
  border-bottom-right-radius: 4px;
}
.instrument-card:hover {
  background: rgba(34, 211, 238, 0.1);
  border-color: var(--card-color, #22d3ee);
  transform: translateY(-2px);
  box-shadow: 0 0 15px rgba(34, 211, 238, 0.2), inset 0 0 10px rgba(34, 211, 238, 0.05);
}

.inst-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px dashed rgba(255,255,255,0.1);
}
.inst-name {
  font-size: 14px; font-weight: 700; color: #fff;
  text-shadow: 0 0 10px rgba(255,255,255,0.3);
  letter-spacing: 1px;
}
.inst-color {
  width: 8px; height: 8px; border-radius: 50%;
  background-color: var(--card-color);
  box-shadow: 0 0 8px var(--card-color), 0 0 14px var(--card-color);
  animation: pulse-dot 2s infinite;
}
@keyframes pulse-dot { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }

.inst-desc {
  font-size: 10px; color: #94a3b8;
  margin-bottom: 12px;
  line-height: 1.4;
  height: 2.8em; /* Force height for alignment */
  overflow: hidden; text-overflow: ellipsis; 
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
}

.inst-footer {
  display: flex; align-items: flex-end; justify-content: space-between;
}
.sensor-count {
  font-size: 26px; font-weight: 700;
  color: var(--card-color, #22d3ee);
  font-family: 'Chakra Petch', monospace;
  line-height: 1;
  text-shadow: 0 0 15px rgba(34, 211, 238, 0.4);
}
.sensor-types {
  font-size: 11px; color: #64748b;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 3px;
  font-family: 'Rajdhani', sans-serif;
}
.empty-instruments {
  text-align: center; color: #475569;
  padding: 15px; font-size: 11px; line-height: 1.5;
}

/* ========== LEFT COLUMN: Donut Chart ========== */
.donut-wrapper { flex: 1; position: relative; display: flex; align-items: center; justify-content: center; padding: 10px; }
.donut-chart { width: 100%; height: 100%; }
.donut-label { position: absolute; text-align: center; pointer-events: none; }
.donut-label .num {
  display: block; font-size: 36px; font-weight: 700;
  font-family: 'Chakra Petch', monospace;
  color: #22d3ee;
  text-shadow: 0 0 20px rgba(34,211,238,0.6), 0 0 40px rgba(34,211,238,0.3);
}
.donut-label .txt { font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 2px; font-family: 'Rajdhani', sans-serif; font-weight: 600; }

/* ========== CENTER: Alert Bar ========== */
.col-center { display: flex; flex-direction: column; gap: 10px; }
.center-top { flex: 2; display: flex; flex-direction: column; gap: 8px; min-height: 0; }

/* ========== CENTER: Map Area ========== */
.map-box {
  flex: 1; position: relative; min-height: 0;
  background: radial-gradient(ellipse at center, rgba(30,41,59,0.8) 0%, rgba(15,23,42,0.95) 70%);
  border: 1px solid rgba(34,211,238,0.15);
  border-radius: 8px;
  overflow: hidden;
}
/* Placeholder 3D Building Image */
.map-bg-image {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%;
  object-fit: cover; opacity: 0.6; pointer-events: none;
}
.map-3d { width: 100%; height: 100%; position: relative; z-index: 1; }

/* ========== Markers: Breathing Light Bubbles ========== */
.marker { position: absolute; cursor: pointer; transform: translate(-50%, -50%); z-index: 10; }
.marker .dot {
  display: block; width: 19px; height: 19px;
  background: radial-gradient(circle, #4ade80 0%, #22c55e 40%, rgba(34,197,94,0.4) 80%);
  border-radius: 50%;
  box-shadow: 0 0 18px #4ade80, 0 0 35px #22c55e, 0 0 50px rgba(34,197,94,0.6);
  animation: pulse 2s ease-in-out infinite;
}
.marker.alarm .dot {
  background: radial-gradient(circle, #fb923c 0%, #f97316 40%, rgba(249,115,22,0.4) 80%);
  box-shadow: 0 0 20px #fb923c, 0 0 40px #f97316, 0 0 60px rgba(249,115,22,0.6);
}
@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 0.9; }
  50% { transform: scale(1.4); opacity: 1; }
}
.marker .name {
  position: absolute; top: -24px; left: 50%; transform: translateX(-50%);
  font-size: 10px; white-space: nowrap;
  background: rgba(15,23,42,0.9); padding: 3px 8px; border-radius: 4px;
  border: 1px solid rgba(34,211,238,0.3);
  color: #94a3b8; font-family: 'Courier New', monospace;
}
.marker .tooltip {
  position: absolute; bottom: 40px; left: 50%; transform: translateX(-50%);
  background: rgba(15,23,42,0.95); backdrop-filter: blur(10px);
  border: 1px solid #22d3ee; padding: 12px; font-size: 11px; width: 150px;
  z-index: 100; border-radius: 8px;
  box-shadow: 0 0 30px rgba(34,211,238,0.2);
}
.marker .tooltip p { margin: 4px 0; color: #94a3b8; }
.marker .tooltip .val {
  color: #22d3ee; font-weight: 700; font-size: 18px; margin-top: 6px;
  font-family: 'Courier New', monospace;
  text-shadow: 0 0 10px rgba(34,211,238,0.5);
}

/* ========== CENTER: Metrics Row ========== */
.metrics-row { display: flex; gap: 8px; height: 65px; }
.metric {
  flex: 1; position: relative;
  background: rgba(15,23,42,0.6); backdrop-filter: blur(4px);
  border-radius: 6px;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  transition: all 0.3s;
}
/* Corner decorations for metrics */
.metric::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; bottom: 0; pointer-events: none;
  background:
    linear-gradient(135deg, rgba(34,211,238,0.5) 0%, rgba(34,211,238,0.5) 1px, transparent 1px, transparent 8px, transparent 8px),
    linear-gradient(315deg, rgba(34,211,238,0.5) 0%, rgba(34,211,238,0.5) 1px, transparent 1px, transparent 8px, transparent 8px);
  background-size: 8px 8px;
  background-position: top left, bottom right;
  background-repeat: no-repeat;
}
.m-label { font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: 1px; }
.m-value {
  font-size: 18px; font-weight: 700; margin-top: 2px;
  font-family: 'Courier New', monospace;
  color: #22d3ee;
  text-shadow: 0 0 10px rgba(34,211,238,0.5);
}
.m-value small { font-size: 10px; color: #64748b; margin-left: 2px; font-weight: 400; }

/* ========== CENTER: Trend Chart ========== */
.trend-panel { flex: 1; min-height: 110px; }
.trend-chart { width: 100%; height: calc(100% - 40px); padding: 5px; }
.tabs { display: flex; gap: 6px; }
.tab {
  background: rgba(34,211,238,0.1); border: 1px solid rgba(34,211,238,0.2);
  color: #64748b; padding: 3px 10px; font-size: 11px; cursor: pointer; border-radius: 4px; transition: all 0.2s;
}
.tab:hover { background: rgba(34,211,238,0.15); color: #94a3b8; }
.tab.active { background: rgba(34,211,238,0.2); border-color: #22d3ee; color: #22d3ee; }

/* ========== RIGHT: Weather Panel ========== */
.weather-panel { flex: 0 0 auto; }
.weather-main { display: flex; align-items: center; justify-content: center; gap: 16px; padding: 12px; }
.weather-main .icon { font-size: 40px; filter: drop-shadow(0 0 10px rgba(255,200,100,0.4)); }
.weather-main .temp {
  font-size: 36px; font-weight: 300;
  font-family: 'Courier New', monospace;
  color: #22d3ee;
  text-shadow: 0 0 15px rgba(34,211,238,0.5);
}
.weather-main .temp small { font-size: 16px; color: #64748b; }
.weather-details { display: flex; justify-content: space-around; padding: 10px; border-top: 1px solid rgba(34,211,238,0.1); font-size: 11px; }
.weather-details div { text-align: center; padding: 6px 10px; background: rgba(34,211,238,0.05); border-radius: 6px; }
.weather-details span { display: block; color: #64748b; font-size: 10px; margin-bottom: 3px; }
.weather-details b { color: #cbd5e1; font-weight: 600; font-family: 'Courier New', monospace; }
.weather-details .good { color: #22c55e; text-shadow: 0 0 8px rgba(34,197,94,0.4); }

/* ========== RIGHT: Device List ========== */
.device-panel { flex: 2; min-height: 0; }
.device-list { flex: 1; overflow-y: auto; padding: 6px; }
.device-item {
  display: flex; align-items: center; padding: 8px 10px;
  border-radius: 6px; margin-bottom: 4px; gap: 8px;
  background: rgba(30,41,59,0.4);
  border: 1px solid transparent; transition: all 0.2s; cursor: pointer;
}
.device-item:hover { background: rgba(34,211,238,0.08); border-color: rgba(34,211,238,0.2); }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: #475569; }
.status-dot.online { background: #22c55e; box-shadow: 0 0 8px rgba(34,197,94,0.6); }
.d-name { flex: 1; font-size: 12px; font-weight: 500; color: #94a3b8; }
.d-val {
  font-size: 14px; font-weight: 700;
  font-family: 'Courier New', monospace;
  color: #22d3ee;
  text-shadow: 0 0 8px rgba(34,211,238,0.4);
}
.d-val.alarm { color: #f87171; text-shadow: 0 0 8px rgba(248,113,113,0.4); }
.d-val small { font-size: 10px; color: #64748b; font-weight: 400; }

/* ========== RIGHT: Alarm List ========== */
.alarm-panel { flex: 1; min-height: 0; }
.alarm-list { flex: 1; overflow-y: auto; padding: 6px; }
.alarm-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 10px; border-radius: 6px; margin-bottom: 4px;
  background: rgba(239,68,68,0.06); border-left: 2px solid #f87171;
  font-size: 11px;
}
.a-time { color: #64748b; font-family: 'Courier New', monospace; }
.a-sn { color: #fca5a5; font-weight: 500; }
.a-val { color: #f87171; font-weight: 700; font-size: 13px; font-family: 'Courier New', monospace; text-shadow: 0 0 8px rgba(248,113,113,0.4); }
.empty { text-align: center; color: #475569; padding: 24px; font-size: 12px; }

/* ========== SCROLLBAR ========== */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: rgba(30,41,59,0.3); border-radius: 2px; }
::-webkit-scrollbar-thumb { background: rgba(34,211,238,0.3); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: rgba(34,211,238,0.5); }
</style>
