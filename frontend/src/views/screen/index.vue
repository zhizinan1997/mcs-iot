<template>
  <div class="dashboard">
    <!-- Header Bar -->
    <header class="header">
      <div class="header-left"></div>
      <div class="header-center">
        <h1>元芯物联网智慧云平台</h1>
        <p>Infinicore IoT Smart Ecosystem</p>
      </div>
      <div class="header-right">
        <span class="loc">📍 {{ weather.location || '定位中...' }}</span>
        <span class="date">{{ currentDate }}</span>
        <span class="weather">{{ weather.desc }} {{ weather.temp }}°C</span>
      </div>
    </header>

    <!-- Main Grid: 3 columns -->
    <main class="main">
      <!-- LEFT COLUMN -->
      <section class="col col-left">
        <!-- Panel: 仪表概览 -->
        <div class="panel panel-sm">
          <div class="panel-title">仪表概览</div>
          <div class="instruments-grid">
            <div class="instrument-card" v-for="inst in displayedInstruments" :key="inst.id">
              <div class="inst-name">{{ inst.name }}</div>
              <div class="inst-desc">{{ inst.description || '暂无描述' }}</div>
              <div class="inst-stats">
                <span class="sensor-count">{{ inst.sensor_count || 0 }}</span>
                <span class="sensor-label">传感器</span>
              </div>
              <div class="inst-types">{{ inst.sensor_types || '—' }}</div>
            </div>
            <div v-if="!displayedInstruments.length" class="empty-instruments">暂无显示的仪表</div>
          </div>
        </div>
        <!-- Panel: 报警/能耗图 -->
        <div class="panel panel-sm">
          <div class="panel-title">设备状态</div>
          <div class="donut-wrapper">
            <v-chart class="donut-chart" :option="donutOption" autoresize />
            <div class="donut-label">
              <span class="num">{{ stats.devices_total }}</span>
              <span class="txt">设备总数</span>
            </div>
          </div>
        </div>
        <!-- Panel: AI 智能总结 -->
        <div class="panel panel-ai">
          <div class="panel-title">🤖 AI 智能分析</div>
          <div class="ai-content">
            <div class="ai-summary">
              <p v-if="aiSummary">{{ aiSummary }}</p>
              <p v-else class="ai-thinking">正在分析数据...</p>
            </div>
          </div>
        </div>
      </section>

      <!-- CENTER COLUMN -->
      <section class="col col-center">
        <!-- Top: Alert + Map -->
        <div class="center-top">
          <div class="alert-bar">
            园区严重污染物: <strong>{{ topPollutant.name }}</strong> ({{ topPollutant.value }} {{ topPollutant.unit }})
          </div>
          <div class="map-box">
            <!-- 3D Building Placeholder Image - Replace src with actual 3D factory image -->
            <img class="map-bg-image" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'/%3E" alt="3D Factory Map" />
            <div class="map-3d">
              <div
                v-for="d in devices"
                :key="d.sn"
                class="marker"
                :class="{ alarm: (d.ppm||0) > 1000 }"
                :style="{ left: pos(d.sn, 'x') + '%', top: pos(d.sn, 'y') + '%' }"
                @click="selected = selected === d.sn ? null : d.sn"
              >
                <span class="dot"></span>
                <span class="pin-line"></span>
                <span class="name">{{ d.name || d.sn }}</span>
                <div class="tooltip" v-if="selected === d.sn">
                  <p><b>{{ d.name }}</b></p>
                  <p>SN: {{ d.sn }}</p>
                  <p>状态: {{ d.status }}</p>
                  <p class="val">{{ d.ppm?.toFixed(1) }} {{ d.unit }}</p>
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
        <!-- Bottom: Trend Chart -->
        <div class="panel trend-panel">
          <div class="panel-title">
            污染物趋势图
            <span class="tabs">
              <button class="tab active">今日</button>
              <button class="tab">昨日</button>
            </span>
          </div>
          <v-chart class="trend-chart" :option="trendOption" autoresize />
        </div>
      </section>

      <!-- RIGHT COLUMN -->
      <section class="col col-right">
        <!-- Panel: 天气概况 -->
        <div class="panel weather-panel">
          <div class="panel-title">天气概况</div>
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
          <div class="panel-title">设备状态</div>
          <div class="device-list">
            <div class="device-item" v-for="d in devices" :key="d.sn">
              <span class="status-dot" :class="d.status"></span>
              <span class="d-name">{{ d.name || d.sn }}</span>
              <span class="d-val" :class="{ alarm: (d.ppm||0) > 1000 }">{{ d.ppm?.toFixed(0) }} <small>{{ d.unit }}</small></span>
            </div>
          </div>
        </div>
        <!-- Panel: 最新报警 -->
        <div class="panel alarm-panel">
          <div class="panel-title">最新报警</div>
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
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, provide } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import VChart, { THEME_KEY } from 'vue-echarts'
import { dashboardApi, alarmsApi, instrumentsApi } from '../../api'

use([CanvasRenderer, PieChart, LineChart, GridComponent, TooltipComponent])
provide(THEME_KEY, 'dark')

interface Device { sn: string; name: string | null; ppm: number | null; temp: number | null; status: string; unit: string }
interface Alarm { id: number; time: string; sn: string; value: number }
interface Instrument { id: number; name: string; description: string | null; color: string | null; is_displayed?: boolean; sensor_count?: number; sensor_types?: string }

const currentDate = ref('')
const devices = ref<Device[]>([])
const alarms = ref<Alarm[]>([])
const instruments = ref<Instrument[]>([])
const selected = ref<string | null>(null)
const trend = ref<number[]>([])
const trendLabels = ref<string[]>([])
const stats = reactive({ devices_total: 0, devices_online: 0 })
const weather = reactive({ temp: '--', humidity: '--', wind: '--', desc: '--', location: '', icon: '🌤️' })

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

const donutOption = computed(() => ({
  series: [{
    type: 'pie', radius: ['70%', '85%'], center: ['50%', '50%'],
    label: { show: false },
    itemStyle: { borderRadius: 4, borderColor: '#0f172a', borderWidth: 2 },
    data: [
      { value: stats.devices_online, itemStyle: { color: { type: 'linear', x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: '#22d3ee' }, { offset: 1, color: '#06b6d4' }] } } },
      { value: stats.devices_total - stats.devices_online, itemStyle: { color: 'rgba(100,116,139,0.3)' } }
    ]
  }]
}))

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

function pos(sn: string, axis: 'x' | 'y'): number {
  let h = 0; const s = axis === 'x' ? sn : sn.split('').reverse().join('')
  for (let i = 0; i < s.length; i++) { h = ((h << 5) - h) + s.charCodeAt(i); h |= 0 }
  return 15 + Math.abs(h % 70)
}
function fmtTime(t: string) { return new Date(t).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }

async function fetchData() {
  try {
    const [st, dv, al, instRes] = await Promise.all([
      dashboardApi.stats(),
      dashboardApi.realtime(),
      alarmsApi.list({ page: 1, size: 10 }),
      instrumentsApi.list()
    ])
    Object.assign(stats, st.data)
    devices.value = dv.data || []
    alarms.value = al.data?.data || []
    
    // Process instruments with sensor aggregation
    const instList = instRes.data || []
    instruments.value = instList.map((inst: Instrument) => {
      const sensorDevices = devices.value.filter((d: Device) => d.name?.includes(inst.name))
      const types = [...new Set(sensorDevices.map((d: Device) => d.unit))].join(', ')
      return {
        ...inst,
        sensor_count: sensorDevices.length,
        sensor_types: types || '—'
      }
    })
    
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

let timer: ReturnType<typeof setInterval>
onMounted(() => {
  currentDate.value = new Date().toLocaleDateString('zh-CN')
  fetchData(); fetchWeather()
  timer = setInterval(() => { currentDate.value = new Date().toLocaleDateString('zh-CN'); fetchData() }, 3000)
})
onUnmounted(() => clearInterval(timer))
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
  font-family: 'Microsoft YaHei', sans-serif;
  display: flex; flex-direction: column; overflow: hidden;
}

/* ========== HEADER ========== */
.header {
  height: 60px; display: flex; align-items: center; justify-content: space-between;
  padding: 0 30px;
  background: linear-gradient(90deg, rgba(15,23,42,0.9), rgba(30,41,59,0.7), rgba(15,23,42,0.9));
  border-bottom: 1px solid rgba(34,211,238,0.2);
}
.header h1 {
  margin: 0; font-size: 24px; font-weight: 700; letter-spacing: 4px;
  color: #22d3ee;
  text-shadow: 0 0 20px rgba(34,211,238,0.5), 0 0 40px rgba(34,211,238,0.3);
}
.header p { margin: 2px 0 0 0; font-size: 10px; color: #64748b; letter-spacing: 6px; text-transform: uppercase; }
.header-right { display: flex; gap: 20px; font-size: 13px; color: #94a3b8; font-family: 'Courier New', monospace; }
.header-right .loc { color: #22d3ee; text-shadow: 0 0 8px rgba(34,211,238,0.4); }
.header-right .date { color: #64748b; }
.header-right .weather { color: #22d3ee; text-shadow: 0 0 8px rgba(34,211,238,0.4); }

/* ========== MAIN GRID ========== */
.main { flex: 1; display: grid; grid-template-columns: 1fr 2.2fr 1fr; gap: 12px; padding: 12px; min-height: 0; }
.col { display: flex; flex-direction: column; gap: 12px; min-height: 0; }

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

/* ========== LEFT COLUMN: Instruments Grid ========== */
.instruments-grid {
  display: flex; flex-direction: column; gap: 8px;
  padding: 10px; flex: 1; overflow-y: auto;
}
.instrument-card {
  background: rgba(30,41,59,0.5);
  border: 1px solid rgba(34,211,238,0.15);
  border-radius: 6px;
  padding: 10px 12px;
  transition: all 0.2s;
  cursor: pointer;
}
.instrument-card:hover {
  background: rgba(34,211,238,0.08);
  border-color: rgba(34,211,238,0.3);
}
.inst-name {
  font-size: 13px; font-weight: 600; color: #22d3ee;
  margin-bottom: 4px;
  text-shadow: 0 0 8px rgba(34,211,238,0.3);
}
.inst-desc {
  font-size: 10px; color: #64748b;
  margin-bottom: 8px;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.inst-stats {
  display: flex; align-items: baseline; gap: 4px;
  margin-bottom: 4px;
}
.sensor-count {
  font-size: 20px; font-weight: 700;
  font-family: 'Courier New', monospace;
  color: #22d3ee;
  text-shadow: 0 0 10px rgba(34,211,238,0.5);
}
.sensor-label {
  font-size: 10px; color: #64748b;
}
.inst-types {
  font-size: 9px; color: #475569;
  font-family: 'Courier New', monospace;
}
.empty-instruments {
  text-align: center; color: #475569;
  padding: 20px; font-size: 12px;
}

/* ========== LEFT COLUMN: Donut Chart ========== */
.donut-wrapper { flex: 1; position: relative; display: flex; align-items: center; justify-content: center; padding: 10px; }
.donut-chart { width: 100%; height: 100%; }
.donut-label { position: absolute; text-align: center; pointer-events: none; }
.donut-label .num {
  display: block; font-size: 36px; font-weight: 700;
  font-family: 'Courier New', monospace;
  color: #22d3ee;
  text-shadow: 0 0 20px rgba(34,211,238,0.6), 0 0 40px rgba(34,211,238,0.3);
}
.donut-label .txt { font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 2px; }

/* ========== CENTER: Alert Bar ========== */
.col-center { display: flex; flex-direction: column; gap: 10px; }
.center-top { flex: 2; display: flex; flex-direction: column; gap: 8px; min-height: 0; }
.alert-bar {
  background: rgba(239,68,68,0.08);
  border: 1px solid rgba(239,68,68,0.3);
  color: #fca5a5; text-align: center; padding: 8px 16px; font-size: 13px; border-radius: 6px;
}
.alert-bar strong { color: #f87171; font-family: 'Courier New', monospace; text-shadow: 0 0 10px rgba(239,68,68,0.5); }

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
  display: block; width: 14px; height: 14px;
  background: radial-gradient(circle, #22d3ee 30%, rgba(34,211,238,0.6) 70%);
  border-radius: 50%;
  box-shadow: 0 0 15px #22d3ee, 0 0 30px rgba(34,211,238,0.4);
  animation: pulse 2s ease-in-out infinite;
}
.marker.alarm .dot {
  background: radial-gradient(circle, #f87171 30%, rgba(248,113,113,0.6) 70%);
  box-shadow: 0 0 15px #f87171, 0 0 30px rgba(248,113,113,0.4);
}
@keyframes pulse {
  0%, 100% { transform: scale(1); box-shadow: 0 0 15px currentColor, 0 0 30px rgba(34,211,238,0.4); }
  50% { transform: scale(1.3); box-shadow: 0 0 25px currentColor, 0 0 50px rgba(34,211,238,0.6); }
}
/* Pin line connecting to ground */
.marker .pin-line {
  position: absolute; top: 100%; left: 50%; transform: translateX(-50%);
  width: 1px; height: 30px;
  background: linear-gradient(to bottom, #22d3ee, transparent);
  opacity: 0.5;
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
