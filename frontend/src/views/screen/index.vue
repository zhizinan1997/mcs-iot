<template>
  <div class="dashboard">
    <!-- Header Bar -->
    <header class="header">
      <div class="header-bg-deco"></div>
      <div class="header-left"></div>
      <div class="header-center">
        <div class="title-deco-left">
          <div class="deco-line-1"></div>
          <div class="deco-line-2"></div>
          <div class="deco-block"></div>
        </div>
        <div class="title-box">
          <div class="chip-lines"></div>
          <h1>{{ dashboardTitle }}</h1>
          <div class="chip-light"></div>
        </div>
        <div class="title-deco-right">
          <div class="deco-block"></div>
          <div class="deco-line-1"></div>
          <div class="deco-line-2"></div>
        </div>
      </div>
      <div class="header-right">
        <span class="loc">📍 {{ weather.location || '定位中...' }}</span>
        <span class="date">{{ currentDate }}</span>
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
                <section class="col col-left" style="padding: 0; display: block; overflow: hidden;">
                  <Splitpanes horizontal @resized="onLeftColumnResize">
                    <!-- Panel: 仪表概览 -->
                    <Pane :size="panelSizes.leftPanel1 || 35" min-size="10">
                      <div class="panel panel-sm" style="height: 100%; border-radius: 0;">
                        <div class="safety-header">
                          <div class="header-deco"><div class="deco-dot"></div><div class="deco-ring"></div></div>
                          <div class="header-text">仪表概览</div>
                          <div class="header-sub">INSTRUMENT OVERVIEW</div>
                        </div>
                        <div class="instruments-grid">
                          <TransitionGroup name="inst-fade">
                            <div class="instrument-card" v-for="inst in carouselInstruments" :key="inst.id" :style="{ '--card-color': inst.color || '#22d3ee' }">
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
                          </TransitionGroup>
                          <div v-if="!displayedInstruments.length" class="empty-instruments">
                            暂无显示的仪表<br/><small>请在管理界面→大屏显示管理中设置</small>
                          </div>
                        </div>
                      </div>
                    </Pane>
                    
                    <!-- Panel: 安全监管 -->
                    <Pane :size="panelSizes.leftPanel2 || 45" min-size="10">
                      <div class="panel panel-safety" style="height: 100%; border-radius: 0;">
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
                            <div class="gauge-container" :style="{ '--score-color': scoreColor.end, '--score-shadow': scoreColor.shadow }">
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
                    </Pane>
                    
                    <!-- Panel: AI 智能总结 -->
                    <Pane :size="panelSizes.leftPanel3 || 20" min-size="5">
                      <div class="panel panel-ai" style="height: 100%; border-radius: 0;">
                        <div class="safety-header">
                          <div class="header-deco"><div class="deco-dot"></div><div class="deco-ring"></div></div>
                          <div class="header-text">元芯AI总结</div>
                          <div class="header-sub">METACHIP AI ANALYSIS</div>
                        </div>
                        <div class="ai-content">
                          <div class="ai-summary">
                            <p v-if="aiLoading" class="ai-thinking">{{ aiThinking }}</p>
                            <p v-else-if="aiSummary">{{ aiSummary }}</p>
                            <p v-else class="ai-error">暂无分析数据</p>
                          </div>
                        </div>
                      </div>
                    </Pane>
                  </Splitpanes>
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
                :class="{ alarm: instrumentHasAlarm(inst.id), 'z-top': selectedInstrument === inst.id }"
                :style="{ left: instrumentPos(inst.id, 'x') + '%', top: instrumentPos(inst.id, 'y') + '%' }"
                @click="toggleInstrument($event, inst.id)"
              >
                <span class="dot"></span>
                <span class="name">{{ inst.name }}</span>
              </div>
            </div>
          </div>
        </div>
        <!-- Bottom: Metrics row -->
        <div class="metrics-grid">
          <div class="metric-card" v-for="m in metrics" :key="m.label">
            <div class="mc-header">
              <div class="mc-dot"></div>
              <div class="mc-label">{{ m.label }}</div>
            </div>
            <div class="mc-body">
              <div class="mc-value">{{ m.value }}</div>
              <div class="mc-unit">{{ m.unit }}</div>
            </div>
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
                    <button 
                      v-for="inst in instruments" 
                      :key="inst.id"
                      class="tab"
                      :class="{ active: activeChartInstrumentId === inst.id }"
                      @click="selectChartInstrument(inst.id)"
                    >
                      {{ inst.name }}
                    </button>
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
            <div class="weather-content" v-if="weather.today && weather.tomorrow">
              <!-- Today -->
              <div class="weather-day">
                <div class="day-title">今日</div>
                <div class="day-main">
                  <span class="w-icon">{{ getWeatherIcon(weather.today.code_day) }}</span>
                  <span class="w-temp">{{ weather.today.low }}~{{ weather.today.high }}°C</span>
                </div>
                <div class="day-detail">
                  <span>{{ weather.today.text_day }}</span>
                  <span>降水 {{ (Number(weather.today.precip) * 100).toFixed(0) }}%</span>
                </div>
              </div>
              <div class="weather-divider"></div>
              <!-- Tomorrow -->
              <div class="weather-day">
                <div class="day-title">明日</div>
                <div class="day-main">
                  <span class="w-icon">{{ getWeatherIcon(weather.tomorrow.code_day) }}</span>
                  <span class="w-temp">{{ weather.tomorrow.low }}~{{ weather.tomorrow.high }}°C</span>
                </div>
                <div class="day-detail">
                  <span>{{ weather.tomorrow.text_day }}</span>
                  <span>降水 {{ (Number(weather.tomorrow.precip) * 100).toFixed(0) }}%</span>
                </div>
              </div>
            </div>
            <div class="weather-loading" v-else>
              {{ weather.error || '加载中...' }}
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
              <div class="scroll-wrapper" :style="{ animationDuration: sortedDevices.length * 2 + 's' }">
                <div 
                  class="device-item" 
                  v-for="(d, i) in [...sortedDevices, ...sortedDevices]" 
                  :key="i"
                  :class="{ 'device-alarm': d.hasUnhandledAlarm }"
                >
                  <span class="status-dot" :class="d.status"></span>
                  <span class="d-name">{{ d.name || d.sn }}</span>
                  <span class="d-signal" v-if="d.network || d.rssi !== null">
                    <span class="signal-type">{{ getNetworkType(d.network) }}</span>
                    <!-- WiFi Icon: Concentric Arcs -->
                    <span v-if="isWifi(d.network)" class="wifi-signal" :class="{ 'signal-critical': isSignalCritical(d.rssi, d.network) }">
                      <span class="wifi-arc arc-1" :class="{ active: getSignalBars(d.rssi, d.network) >= 1 }"></span>
                      <span class="wifi-arc arc-2" :class="{ active: getSignalBars(d.rssi, d.network) >= 2 }"></span>
                      <span class="wifi-arc arc-3" :class="{ active: getSignalBars(d.rssi, d.network) >= 3 }"></span>
                      <span class="wifi-arc arc-4" :class="{ active: getSignalBars(d.rssi, d.network) >= 4 }"></span>
                    </span>
                    <!-- Cellular/Other Icon: Vertical Bars -->
                    <span v-else class="cell-signal" :class="{ 'signal-critical': isSignalCritical(d.rssi, d.network) }">
                      <span class="bar" :class="{ active: getSignalBars(d.rssi, d.network) >= 1 }"></span>
                      <span class="bar" :class="{ active: getSignalBars(d.rssi, d.network) >= 2 }"></span>
                      <span class="bar" :class="{ active: getSignalBars(d.rssi, d.network) >= 3 }"></span>
                      <span class="bar" :class="{ active: getSignalBars(d.rssi, d.network) >= 4 }"></span>
                    </span>
                  </span>
                  <span class="d-val" :class="{ alarm: (d.ppm||0) > (d.high_limit || 1000) }">{{ d.ppm?.toFixed(0) }} <small>{{ d.unit }}</small></span>
                </div>
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
              <div class="scroll-wrapper" :style="{ animationDuration: alarms.length * 2 + 's' }">
                <div class="alarm-item" v-for="(a, i) in [...alarms, ...alarms]" :key="i">
                  <span class="a-time">{{ fmtTime(a.time) }}</span>
                  <span class="a-info">
                    <span class="a-name">{{ a.instrument_name || '' }}{{ a.instrument_name && a.device_name ? ' · ' : '' }}{{ a.device_name || a.sn }}</span>
                  </span>
                  <span class="a-type" :class="getAlarmTypeClass(a.type)">{{ fmtAlarmType(a.type) }}</span>
                </div>
              </div>
              <div v-if="!alarms.length" class="empty">暂无报警</div>
            </div>
          </div>
        </section>
      </Pane>
    </Splitpanes>
    <!-- Global Tooltip via Teleport -->
    <Teleport to="body">
      <div 
        v-if="selectedInstData" 
        class="tooltip global-tooltip"
        :class="tooltipPos.placement"
        :style="{ left: tooltipPos.x + 'px', top: tooltipPos.y + 'px' }"
      >
        <div class="tt-header">
          <p class="tt-title">{{ selectedInstData.name }}</p>
          <p class="tt-status" :class="{ 'alarm-text': instrumentHasAlarm(selectedInstData.id) }">
            {{ instrumentHasAlarm(selectedInstData.id) ? '⚠️ 告警中' : '✅ 正常' }}
          </p>
        </div>
        <div class="tt-stats">
          <div class="tt-stat-item">
            <span>传感器</span><b>{{ getInstrumentDevices(selectedInstData.id).length }}</b>
          </div>
          <div class="tt-stat-item">
            <span>今日报警</span><b>{{ selectedInstData.alarms_today || 0 }}</b>
          </div>
          <div class="tt-stat-item">
            <span>未处理</span><b class="warn-val">{{ selectedInstData.alarms_unhandled || 0 }}</b>
          </div>
        </div>
        <div class="tt-sensors" v-if="getInstrumentDevices(selectedInstData.id).length">
          <div class="tt-sensor-row" v-for="d in getInstrumentDevices(selectedInstData.id)" :key="d.sn">
            <span class="s-name">{{ d.name || d.sn }}</span>
            <span class="s-val" :class="{ 'alarm-val': (d.ppm || 0) > (d.high_limit || 1000) }">
              {{ d.ppm?.toFixed(1) }} <small>{{ d.unit }}</small>
            </span>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, provide, watch } from 'vue'
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
  centerInner: 65, // center column within left+center (horizontal inner split)
  leftPanel1: 35, // instrument overview
  leftPanel2: 45, // safety supervision
  leftPanel3: 20 // ai analysis
}
const panelSizes = reactive({ ...defaultSizes })

function loadLayoutSizes() {
  try {
    const saved = localStorage.getItem(LAYOUT_STORAGE_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)
      // Merge with defaults, allowing new keys
      for (const key of Object.keys(defaultSizes)) {
        // Use type assertion to allow dynamic key access
        if (parsed[key] !== undefined) {
          (panelSizes as Record<string, number>)[key] = parsed[key]
        }
      }
      // Ensure new keys are present if missing in saved data
      for (const key of Object.keys(defaultSizes)) {
        if ((panelSizes as Record<string, number>)[key] === undefined) {
          (panelSizes as Record<string, number>)[key] = (defaultSizes as Record<string, number>)[key] || 0
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

// Left column vertical split resize
function onLeftColumnResize(panes: Array<{ size: number }>) {
  if (panes && panes.length >= 3) {
    panelSizes.leftPanel1 = panes[0]?.size ?? panelSizes.leftPanel1
    panelSizes.leftPanel2 = panes[1]?.size ?? panelSizes.leftPanel2
    panelSizes.leftPanel3 = panes[2]?.size ?? panelSizes.leftPanel3
    saveLayoutSizes()
  }
}

interface Device { sn: string; name: string | null; ppm: number | null; temp: number | null; status: string; unit: string; instrument_id?: number | null; high_limit?: number; sensor_type?: string; network?: string | null; rssi?: number | null; hasUnhandledAlarm?: boolean }
interface Alarm { id: number; time: string; sn: string; value: number; status?: string; type?: string; device_name?: string; instrument_name?: string }
interface Instrument { id: number; name: string; description: string | null; color: string | null; is_displayed?: boolean; sensor_count?: number; sensor_types?: string; pos_x?: number; pos_y?: number; alarms_today?: number; alarms_unhandled?: number }
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

// Sorted devices by name for display
const sortedDevices = computed(() => {
  return [...devices.value].sort((a, b) => {
    const nameA = a.name || a.sn
    const nameB = b.name || b.sn
    return nameA.localeCompare(nameB, 'zh-CN')
  })
})

// Network-specific signal thresholds
// 4G (RSRP): Excellent > -90, Critical -105, Edge -115
// WiFi (RSSI): Excellent > -60, Critical -70, Edge -85
// NB-IoT (RSRP): Excellent > -105, Critical -115, Edge -130
// LoRa (RSSI): Excellent > -105, Critical -120, Edge -140

interface SignalThreshold {
  excellent: number
  good: number
  fair: number
  edge: number
}

const SIGNAL_THRESHOLDS: Record<string, SignalThreshold> = {
  '4G': { excellent: -90, good: -100, fair: -105, edge: -115 },
  'LTE': { excellent: -90, good: -100, fair: -105, edge: -115 },
  'WIFI': { excellent: -60, good: -65, fair: -70, edge: -85 },
  'WI-FI': { excellent: -60, good: -65, fair: -70, edge: -85 },
  'NBIOT': { excellent: -105, good: -110, fair: -115, edge: -130 },
  'NB-IOT': { excellent: -105, good: -110, fair: -115, edge: -130 },
  'LORA': { excellent: -105, good: -115, fair: -120, edge: -140 },
  // Default fallback (WiFi-like)
  'DEFAULT': { excellent: -60, good: -65, fair: -70, edge: -85 }
}

// Get signal bars count (1-4) based on network type
function getSignalBars(rssi: number | null | undefined, network?: string | null): number {
  if (rssi === null || rssi === undefined) return 0
  
  const netType = (network || '').toUpperCase().replace(/[^A-Z0-9-]/g, '')
  const th = SIGNAL_THRESHOLDS[netType] || SIGNAL_THRESHOLDS['DEFAULT']
  
  // Fallback defaults to ensure non-undefined
  const excellent = th?.excellent ?? -60
  const good = th?.good ?? -65
  const fair = th?.fair ?? -70
  const edge = th?.edge ?? -85
  
  if (rssi >= excellent) return 4
  if (rssi >= good) return 3
  if (rssi >= fair) return 2
  if (rssi >= edge) return 1
  return 0  // Below edge = critical/disconnected
}

// Check if signal is at critical edge level
function isSignalCritical(rssi: number | null | undefined, network?: string | null): boolean {
  if (rssi === null || rssi === undefined) return false
  const netType = (network || '').toUpperCase().replace(/[^A-Z0-9-]/g, '')
  const th = SIGNAL_THRESHOLDS[netType] || SIGNAL_THRESHOLDS['DEFAULT']
  const edge = th?.edge ?? -85
  return rssi <= edge
}

// Get network type label
function getNetworkType(network: string | null | undefined): string {
  if (!network) return ''
  const n = network.toUpperCase()
  if (n.includes('5G')) return '5G'
  if (n.includes('WIFI') || n.includes('WI-FI')) return 'WiFi'
  if (n.includes('ETH') || n.includes('LAN')) return 'ETH'
  if (n.includes('NB') || n.includes('IOT')) return 'NB-IoT'
  if (n.includes('LORA')) return 'LoRa'
  return n
}

// Check if network is WiFi
function isWifi(network: string | null | undefined): boolean {
  if (!network) return false
  const n = network.toUpperCase()
  return n.includes('WIFI') || n.includes('WI-FI')
}
const instruments = ref<Instrument[]>([])
const selectedInstrument = ref<number | null>(null)
const tooltipPos = reactive({ x: 0, y: 0, placement: 'top' })

const selectedInstData = computed(() => {
  return instruments.value.find((i: Instrument) => i.id === selectedInstrument.value)
})

function toggleInstrument(event: MouseEvent, instId: number) {
  if (selectedInstrument.value === instId) {
    selectedInstrument.value = null
  } else {
    selectedInstrument.value = instId
    // Calculate position
    const target = event.currentTarget as HTMLElement
    const rect = target.getBoundingClientRect()
    
    // Check available space above
    const tooltipHeightEstimate = 320 // Estimate max height including padding
    const spaceAbove = rect.top
    
    if (spaceAbove < tooltipHeightEstimate) {
      // Not enough space above, show below
      tooltipPos.placement = 'bottom'
      tooltipPos.x = rect.left + rect.width / 2
      tooltipPos.y = rect.bottom + 15
    } else {
      // Show above (default)
      tooltipPos.placement = 'top'
      tooltipPos.x = rect.left + rect.width / 2
      tooltipPos.y = rect.top - 15 
    }
  }
}

const trend = ref<number[]>([])
const trendLabels = ref<string[]>([])
const stats = reactive<ScreenStats>({ devices_total: 0, devices_online: 0, devices_alarm: 0, alarms_today: 0, alarms_confirmed_today: 0 })
const alarmStats = reactive({ today: 0, total: 0 })

// Instrument History Chart State
const activeChartInstrumentId = ref<number | null>(null)
const instrumentHistory = ref<any>(null)
const historyLoading = ref(false)

// Tech colors for chart series
const CHART_COLORS = ['#22d3ee', '#a855f7', '#10b981', '#f59e0b', '#ef4444', '#3b82f6', '#ec4899', '#6366f1']

async function fetchInstrumentHistory(id: number) {
  if (!id) return
  // historyLoading.value = true // Don't show loading on periodic refresh to avoid flickering
  try {
    const res = await instrumentsApi.history(id, 1) // 1 hour
    instrumentHistory.value = res.data
  } catch (e) {
    console.error('Failed to fetch instrument history', e)
  } finally {
    historyLoading.value = false
  }
}

function selectChartInstrument(id: number) {
  activeChartInstrumentId.value = id
  fetchInstrumentHistory(id)
}

const trendOption = computed(() => {
  // Default empty option
  const baseOption = {
    grid: { top: 30, right: 20, bottom: 20, left: 40, containLabel: true },
    tooltip: { 
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.9)',
      borderColor: '#22d3ee',
      textStyle: { color: '#fff' }
    },
    legend: {
      top: 0,
      textStyle: { color: '#94a3b8' },
      data: [] as string[]
    },
    xAxis: { 
      type: 'time', 
      axisLine: { show: false }, 
      axisTick: { show: false }, 
      axisLabel: { 
        color: '#64748b', 
        fontSize: 11,
        formatter: (val: number) => new Date(val).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
      }, 
      splitLine: { show: false } 
    },
    yAxis: { 
      type: 'value', 
      axisLine: { show: false }, 
      axisTick: { show: false }, 
      splitLine: { lineStyle: { color: 'rgba(100,116,139,0.15)', type: 'dashed' } }, 
      axisLabel: { color: '#64748b', fontSize: 11 } 
    },
    series: [] as any[]
  }

  if (!instrumentHistory.value || !instrumentHistory.value.series) {
    return baseOption
  }

  const series = instrumentHistory.value.series.map((s: any, idx: number) => {
    const color = CHART_COLORS[idx % CHART_COLORS.length]
    return {
      name: s.sensor_type || s.name || s.sn,
      type: 'line',
      smooth: true,
      symbol: 'none',
      data: s.data,
      lineStyle: { color, width: 2 },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: color + '66' }, // 0.4 alpha
            { offset: 1, color: color + '00' }  // 0 alpha
          ]
        }
      }
    }
  })

  // Enforce time range on x-axis if start/end are provided
  let xAxisRange = {}
  if (instrumentHistory.value.start && instrumentHistory.value.end) {
    xAxisRange = {
      min: new Date(instrumentHistory.value.start).getTime(),
      max: new Date(instrumentHistory.value.end).getTime()
    }
  }

  return {
    ...baseOption,
    xAxis: {
      ...baseOption.xAxis,
      ...xAxisRange
    },
    legend: {
      ...baseOption.legend,
      data: series.map((s: any) => s.name)
    },
    series
  }
})
interface DailyWeather {
  date: string
  text_day: string
  code_day: string
  text_night: string
  code_night: string
  high: string
  low: string
  rainfall: string
  precip: string
  wind_direction: string
  wind_speed: string
  humidity: string
}

interface WeatherState {
  location: string
  today: DailyWeather | null
  tomorrow: DailyWeather | null
  error: string
  loading: boolean
}

const weather = reactive<WeatherState>({
  location: '',
  today: null,
  tomorrow: null,
  error: '',
  loading: false
})

const aiSummary = ref('')
const aiLoading = ref(false)
const aiThinking = ref('正在分析数据...')

// Filter instruments by is_displayed field
const displayedInstruments = computed(() => {
  // Filter for instruments where is_displayed is explicitly true
  return instruments.value.filter((i: Instrument) => i.is_displayed === true)
})

// Carousel pagination for instrument panel
const CAROUSEL_PAGE_SIZE = 4
const CAROUSEL_INTERVAL_MS = 5000
const carouselPage = ref(0)
let carouselTimer: ReturnType<typeof setInterval> | null = null

const totalCarouselPages = computed(() => {
  return Math.ceil(displayedInstruments.value.length / CAROUSEL_PAGE_SIZE)
})

const carouselInstruments = computed(() => {
  const start = carouselPage.value * CAROUSEL_PAGE_SIZE
  return displayedInstruments.value.slice(start, start + CAROUSEL_PAGE_SIZE)
})

function startCarouselTimer() {
  if (carouselTimer) clearInterval(carouselTimer)
  if (totalCarouselPages.value <= 1) return
  carouselTimer = setInterval(() => {
    carouselPage.value = (carouselPage.value + 1) % totalCarouselPages.value
  }, CAROUSEL_INTERVAL_MS)
}

function stopCarouselTimer() {
  if (carouselTimer) {
    clearInterval(carouselTimer)
    carouselTimer = null
  }
}

// Watch to restart carousel when instrument count changes
watch(totalCarouselPages, (newPages) => {
  if (newPages > 1) {
    startCarouselTimer()
  } else {
    stopCarouselTimer()
    carouselPage.value = 0
  }
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

// Helper to interpolate colors
const getSmoothColor = (percentage: number) => {
  // Stops: 0% (Red) -> 25% (Orange) -> 50% (Yellow) -> 75% (Lime) -> 100% (Green)
  const stops = [
    { pct: 0, r: 239, g: 68, b: 68 },     // #ef4444 Red
    { pct: 25, r: 249, g: 115, b: 22 },   // #f97316 Orange
    { pct: 50, r: 234, g: 179, b: 8 },    // #eab308 Yellow
    { pct: 75, r: 132, g: 204, b: 22 },   // #84cc16 Lime
    { pct: 100, r: 34, g: 197, b: 94 }    // #22c55e Green
  ]
  
  const p = Math.max(0, Math.min(100, percentage))
  
  let start = stops[0] || { pct: 0, r: 239, g: 68, b: 68 }
  let end = stops[stops.length - 1] || { pct: 100, r: 34, g: 197, b: 94 }
  
  for (let i = 0; i < stops.length - 1; i++) {
    const s1 = stops[i]
    const s2 = stops[i+1]
    if (s1 && s2 && p >= s1.pct && p <= s2.pct) {
      start = s1
      end = s2
      break
    }
  }
  
  const range = end.pct - start.pct
  const factor = (p - start.pct) / (range || 1)
  
  const r = Math.round(start.r + factor * (end.r - start.r))
  const g = Math.round(start.g + factor * (end.g - start.g))
  const b = Math.round(start.b + factor * (end.b - start.b))
  
  return { r, g, b, rgb: `rgb(${r},${g},${b})`, hex: `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}` }
}

const scoreColor = computed(() => {
  const s = overallScore.value
  const c = getSmoothColor(s)
  const cStart = getSmoothColor(s - 20) // Create a trailing gradient effect
  
  // To create a gradient effect on the bar itself, we can shift the color slightly
  // or just use the same base color for a solid but smooth look.
  // Let's make 'start' slightly brighter/lighter and 'end' the pure color for depth.
  
  return { 
    start: cStart.hex, 
    end: c.hex, 
    shadow: `rgba(${c.r},${c.g},${c.b},0.6)`, 
    stop1: `rgba(${c.r},${c.g},${c.b},0.8)`, 
    stop2: `rgba(${c.r},${c.g},${c.b},0.2)` 
  }
})


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




const DEFAULT_UNITS: Record<string, string> = {
  'H2': 'ppm',
  '氢气（H2）': 'ppm',
  'CH4': '%LEL',
  '甲烷（CH4）': '%LEL',
  'CO': 'ppm',
  'CO2': 'ppm',
  'O2': '%VOL',
  'H2S': 'ppm',
  'VOC': 'ppm',
  'VOCs': 'ppm',
  'PM2.5': 'ug/m³',
  'PM10': 'ug/m³',
  'TEMP': '°C',
  'Temperature': '°C',
  'HUM': '%RH',
  'Humidity': '%RH',
  'EX': '%LEL'
}

const METRIC_CARDS = [
  { key: 'H2', label: '氢气浓度', sources: ['H2', '氢气', '氢气（H2）'] },
  { key: 'CH4', label: '甲烷浓度', sources: ['CH4', '甲烷', '甲烷（CH4）'] },
  { key: 'TEMP', label: '环境温度', sources: ['Temperature', 'TEMP', '温度'] },
  { key: 'HUM', label: '环境湿度', sources: ['Humidity', 'HUM', '湿度'] },
  { key: 'PM2.5', label: 'PM2.5', sources: ['PM2.5'] },
  { key: 'VOCs', label: 'VOC浓度', sources: ['VOCs', 'VOC'] }
]

const metrics = computed(() => {
  return METRIC_CARDS.map(card => {
    let maxVal = 0
    let unit = ''
    let hasData = false
    
    devices.value.forEach(d => {
      const type = d.sensor_type ? d.sensor_type.trim() : ''
      // Case-insensitive check
      if (card.sources.some(s => s.toLowerCase() === type.toLowerCase())) {
        const val = d.ppm !== null && d.ppm !== undefined ? d.ppm : 0
        if (!hasData || val > maxVal) {
          maxVal = val
          unit = d.unit || DEFAULT_UNITS[card.key] || ''
          hasData = true
        }
      }
    })
    
    return {
      label: card.label,
      value: hasData ? maxVal.toFixed(maxVal < 10 ? 2 : 1) : '0.0',
      unit: unit || (DEFAULT_UNITS[card.key] || '')
    }
  })
})


// Format time (database already stores Beijing time)
function fmtTime(t: string) { 
  const date = new Date(t)
  return date.toLocaleTimeString('zh-CN', { 
    hour: '2-digit', 
    minute: '2-digit'
  }) 
}

// Format alarm type to Chinese display
function fmtAlarmType(type: string | undefined): string {
  if (!type) return '未知'
  const typeMap: Record<string, string> = {
    'HIGH': '浓度超标',
    'LOW': '浓度过低',
    'OFFLINE': '设备离线',
    'LOW_BAT': '电量不足',
    'WEAK_SIGNAL': '信号不好'
  }
  return typeMap[type.toUpperCase()] || type
}

// Get alarm type color
function getAlarmTypeClass(type: string | undefined): string {
  if (!type) return 'type-unknown'
  const t = type.toUpperCase()
  if (t === 'HIGH') return 'type-high'
  if (t === 'OFFLINE') return 'type-offline'
  if (t === 'LOW_BAT') return 'type-battery'
  if (t === 'WEAK_SIGNAL') return 'type-signal'
  return 'type-unknown'
}

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
    const newDeviceList = dv.data || []
    const newAlarmList = al.data?.data || []
    
    // Build set of SNs with unhandled (active) alarms
    const unhandledAlarmSNs = new Set<string>()
    newAlarmList.forEach((alarm: Alarm) => {
      if (alarm.status === 'active') {
        unhandledAlarmSNs.add(alarm.sn)
      }
    })
    
    // Smart update: Update devices in-place to preserve scroll animation
    // Only replace array if new device added/removed, otherwise update in place
    const existingDeviceSNs = new Set(devices.value.map((d: Device) => d.sn))
    const newDeviceSNs = new Set(newDeviceList.map((d: Device) => d.sn))
    
    const devicesChanged = existingDeviceSNs.size !== newDeviceSNs.size ||
      [...existingDeviceSNs].some(sn => !newDeviceSNs.has(sn))
    
    if (devicesChanged || devices.value.length === 0) {
      // New devices or structure changed - full replace needed
      devices.value = newDeviceList.map((d: Device) => ({
        ...d,
        hasUnhandledAlarm: unhandledAlarmSNs.has(d.sn)
      }))
    } else {
      // Update existing devices in-place (preserve animation)
      const deviceMap = new Map<string, Device>(newDeviceList.map((d: Device) => [d.sn, d]))
      for (let idx = 0; idx < devices.value.length; idx++) {
        const device = devices.value[idx]
        if (!device) continue
        const sn = device.sn
        const newData = deviceMap.get(sn)
        if (newData) {
          // Update properties directly without replacing the object reference in array
          device.ppm = newData.ppm
          device.temp = newData.temp
          device.status = newData.status
          device.network = newData.network
          device.rssi = newData.rssi
          device.hasUnhandledAlarm = unhandledAlarmSNs.has(sn)
        }
      }
    }
    
    // Smart update for alarms: same logic
    const existingAlarmIds = new Set(alarms.value.map((a: Alarm) => a.id))
    const newAlarmIds = new Set(newAlarmList.map((a: Alarm) => a.id))
    
    const alarmsChanged = existingAlarmIds.size !== newAlarmIds.size ||
      [...existingAlarmIds].some(id => !newAlarmIds.has(id))
    
    if (alarmsChanged || alarms.value.length === 0) {
      // Alarms changed - full replace
      alarms.value = newAlarmList
    }
    // If alarms haven't changed structurally, don't update (they don't have dynamic values like PPM)
    
    // Update alarm stats - try to get today count from API
    if (alStats.data) {
      alarmStats.today = alStats.data.today || alStats.data.today_count || 0
      alarmStats.total = alStats.data.total || 0
    }
    
    // Process instruments with sensor aggregation
    // API returns { total, data: [...] } so access .data.data
    const instList = instRes.data?.data || instRes.data || []
    // Use backend sensor_count directly - it's calculated from instrument_id relation
    instruments.value = instList.map((inst: Instrument) => ({
      ...inst,
      sensor_count: inst.sensor_count || 0,
      sensor_types: '传感器设备'
    }))

    // Select first instrument for chart by default if none selected
    const firstInst = instruments.value[0]
    if (firstInst && !activeChartInstrumentId.value) {
      selectChartInstrument(firstInst.id)
    }
    
    // Refresh chart data if instrument is selected
    if (activeChartInstrumentId.value) {
        fetchInstrumentHistory(activeChartInstrumentId.value)
    }
    
    const avg = devices.value.reduce((s: number, d: Device) => s + (d.ppm || 0), 0) / (devices.value.length || 1)
    trend.value.push(avg); if (trend.value.length > 20) trend.value.shift()
    trendLabels.value.push(new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })); if (trendLabels.value.length > 20) trendLabels.value.shift()
  } catch (e) { console.error(e) }
}

function getWeatherIcon(code: string) {
  const c = parseInt(code)
  if (c <= 3) return '☀️' // Sunny
  if (c <= 9) return '☁️' // Cloudy
  if (c <= 19) return '🌧️' // Rain
  if (c <= 29) return '❄️' // Snow
  if (c <= 38) return '🌫️' // Fog/Dust
  return '🌥️'
}

async function fetchWeather() {
  weather.loading = true
  weather.error = ''
  try {
    // 1. Get Config
    const configRes = await configApi.getWeather()
    const config = configRes.data
    
    if (!config.enabled || !config.api_key || !config.city_pinyin) {
      weather.error = '未配置或未启用'
      return
    }

    // 2. Call Seniverse API
    const url = `https://api.seniverse.com/v3/weather/daily.json?key=${config.api_key}&location=${config.city_pinyin}&language=zh-Hans&unit=c&start=0&days=2`
    const res = await fetch(url)
    const data = await res.json()
    
    if (data.results && data.results.length > 0) {
      const result = data.results[0]
      weather.location = result.location.name
      if (result.daily && result.daily.length >= 2) {
        weather.today = result.daily[0]
        weather.tomorrow = result.daily[1]
      }
    } else {
      weather.error = '数据获取失败'
    }
  } catch (e) {
    console.error('Weather fetch error:', e)
    weather.error = '连接失败'
  } finally {
    weather.loading = false
  }
}

async function fetchAI() {
  if (aiLoading.value) return
  aiLoading.value = true
  aiThinking.value = '正在获取智能分析报告...'
  
  try {
    const res = await dashboardApi.getAISummary()
    if (res.data) {
      aiSummary.value = res.data.content
    } else {
      aiSummary.value = '暂无分析数据'
    }
  } catch (e) {
    console.error('AI Fetch Error:', e)
    aiSummary.value = '获取分析报告失败，请检查配置'
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

// Dashboard Configuration
const dashboardTitle = ref('元芯物联网智慧云平台')
const refreshRate = ref(5) // default 5 seconds

function updateFavicon(url: string) {
  let link = document.querySelector("link[rel~='icon']") as HTMLLinkElement
  if (!link) {
    link = document.createElement('link')
    link.rel = 'icon'
    document.head.appendChild(link)
  }
  link.href = url
}

async function fetchConfigs() {
  try {
    const [dashRes, siteRes] = await Promise.all([
      configApi.getDashboard(),
      configApi.getSite()
    ])
    
    // Dashboard Config
    if (dashRes.data) {
      dashboardTitle.value = dashRes.data.title || '元芯物联网智慧云平台'
      refreshRate.value = (dashRes.data.refresh_rate && dashRes.data.refresh_rate >= 1) ? dashRes.data.refresh_rate : 5
    }

    // Site Config
    if (siteRes.data) {
       if (siteRes.data.browser_title) {
         document.title = siteRes.data.browser_title
       }
       if (siteRes.data.logo_url) {
         updateFavicon(siteRes.data.logo_url)
       }
    }
  } catch (e) {
    console.error('Failed to load configs', e)
  }
}

// Watch refresh rate to update timer
watch(refreshRate, (newRate) => {
  if (timer) clearInterval(timer)
  timer = setInterval(() => { 
      currentDate.value = new Date().toLocaleDateString('zh-CN')
      fetchData() 
  }, newRate * 1000)
})

onMounted(() => {
  loadLayoutSizes() // Restore saved panel sizes
  currentDate.value = new Date().toLocaleDateString('zh-CN')
  
  // Initial data fetch
  fetchData(); fetchWeather(); fetchAI(); fetchScreenBg()
  
  // Start instrument carousel timer
  startCarouselTimer()
  
  // Fetch configs and setup timer
  fetchConfigs().then(() => {
    // If watch didn't trigger (rate is same as default), set timer manually
    if (!timer) {
        timer = setInterval(() => { 
            currentDate.value = new Date().toLocaleDateString('zh-CN')
            fetchData() 
        }, refreshRate.value * 1000)
    }
  })

  aiTimer = setInterval(fetchAI, 60000) // Refresh AI summary every minute
})
onUnmounted(() => { clearInterval(timer); clearInterval(aiTimer); stopCarouselTimer() })
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
  height: 80px; /* Increased height for decorations */
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 30px;
  background: transparent;
  position: relative;
  z-index: 100;
  overflow: hidden;
}

/* Background Decoration */
.header-bg-deco {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%;
  background: 
    linear-gradient(to bottom, rgba(15,23,42,1) 0%, rgba(15,23,42,0.8) 60%, transparent 100%),
    repeating-linear-gradient(90deg, transparent, transparent 49px, rgba(34,211,238,0.05) 49px, rgba(34,211,238,0.05) 50px);
  z-index: -1;
  pointer-events: none;
}
.header-bg-deco::after {
  content: ''; position: absolute; bottom: 0; left: 0; width: 100%; height: 1px;
  background: linear-gradient(90deg, transparent 0%, rgba(34,211,238,0.3) 20%, rgba(34,211,238,0.3) 80%, transparent 100%);
}

.header-center {
  position: absolute;
  left: 50%; top: 0;
  transform: translateX(-50%);
  height: 100%;
  display: flex; align-items: center; justify-content: center;
}

/* Center Title Box */
.title-box {
  position: relative;
  padding: 0 40px;
  height: 50px;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(to bottom, rgba(30,41,59,0.8), rgba(15,23,42,0.9));
  transform: skewX(-15deg); /* Tech slant */
  border: 1px solid rgba(34,211,238,0.3);
  box-shadow: 0 0 20px rgba(15,23,42,0.8);
}
.title-box h1 {
  transform: skewX(15deg); /* Counter slant for text */
  margin: 0; font-size: 32px; font-weight: 700; letter-spacing: 6px;
  color: #fff;
  text-shadow: 0 0 10px rgba(34,211,238,0.8), 0 0 20px rgba(34,211,238,0.4);
  font-family: 'Orbitron', sans-serif;
  text-transform: uppercase;
  z-index: 2;
  background: linear-gradient(to bottom, #ffffff, #94a3b8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

/* Chip/PCB Decorations */
.title-deco-left, .title-deco-right {
  height: 100%; width: 200px;
  position: relative;
  display: flex; flex-direction: column;
  justify-content: center;
  pointer-events: none;
}
.title-deco-left {
  align-items: flex-end;
  margin-right: -25px;
  padding-right: 25px;
}
.title-deco-right {
  align-items: flex-start;
  margin-left: -25px;
  padding-left: 25px;
}

/* Deco Block (The "Wings") */
.deco-block {
  width: 60px; height: 24px;
  background: linear-gradient(180deg, rgba(34,211,238,0.05) 0%, rgba(34,211,238,0.15) 100%);
  border-top: 1px solid rgba(34,211,238,0.4);
  border-bottom: 1px solid rgba(34,211,238,0.4);
  position: relative;
  margin-bottom: 4px;
  backdrop-filter: blur(2px);
}
.title-deco-left .deco-block {
  transform: skewX(-20deg);
  border-left: 1px solid rgba(34,211,238,0.2);
  margin-right: 5px;
}
.title-deco-right .deco-block {
  transform: skewX(20deg);
  border-right: 1px solid rgba(34,211,238,0.2);
  margin-left: 5px;
}

/* Deco Block Accents */
.deco-block::after {
  content: ''; position: absolute; top: 50%; transform: translateY(-50%);
  width: 4px; height: 12px;
  background: #22d3ee;
  box-shadow: 0 0 8px #22d3ee;
}
.title-deco-left .deco-block::after { right: 6px; }
.title-deco-right .deco-block::after { left: 6px; }

/* Lines */
.deco-line-1, .deco-line-2 {
  height: 2px;
  background: #22d3ee;
  position: relative;
  margin: 3px 0;
}

/* Top Line (Long) */
.deco-line-1 {
  width: 100%;
  opacity: 0.6;
}
.title-deco-left .deco-line-1 {
  background: linear-gradient(90deg, transparent 0%, rgba(34,211,238,0.5) 50%, #22d3ee 100%);
}
.title-deco-right .deco-line-1 {
  background: linear-gradient(270deg, transparent 0%, rgba(34,211,238,0.5) 50%, #22d3ee 100%);
}

/* Bottom Line (Short) */
.deco-line-2 {
  width: 60%;
  opacity: 0.3;
}
.title-deco-left .deco-line-2 {
  background: linear-gradient(90deg, transparent, #22d3ee);
}
.title-deco-right .deco-line-2 {
  background: linear-gradient(270deg, transparent, #22d3ee);
}

/* Add some floating particles/dots */
.title-deco-left::before, .title-deco-right::before {
  content: ''; position: absolute;
  width: 120px; height: 1px;
  bottom: 25px;
  background-image: repeating-linear-gradient(90deg, #22d3ee, #22d3ee 2px, transparent 2px, transparent 10px);
  opacity: 0.3;
}
.title-deco-left::before { right: 70px; }
.title-deco-right::before { left: 70px; }

/* Chip Lines inside Title Box */
.chip-lines {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%;
  pointer-events: none;
  overflow: hidden;
}
.chip-lines::before, .chip-lines::after {
  content: ''; position: absolute; width: 20px; height: 100%;
  border-left: 2px dashed rgba(34,211,238,0.2);
  border-right: 2px dashed rgba(34,211,238,0.2);
}
.chip-lines::before { left: 10px; }
.chip-lines::after { right: 10px; }

/* Glowing Light Effect */
.chip-light {
  position: absolute; bottom: -2px; left: 50%;
  transform: translateX(-50%);
  width: 60%; height: 4px;
  background: #22d3ee;
  box-shadow: 0 0 20px #22d3ee, 0 0 40px #22d3ee;
  border-radius: 50%;
  opacity: 0.8;
  animation: pulse-light 3s infinite ease-in-out;
}
@keyframes pulse-light {
  0%, 100% { opacity: 0.5; width: 50%; }
  50% { opacity: 1; width: 70%; }
}

.header p { display: none; }
.header-right { 
  display: flex; gap: 20px; font-size: 15px; color: #94a3b8; 
  font-family: 'Chakra Petch', monospace; font-weight: 500; 
  position: absolute; right: 30px; bottom: 15px; /* Adjust position */
}
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
.col-left { gap: 8px; overflow: hidden; }
.col-left .panel { width: 100%; }

/* Splitpanes splitter styling - make them more visible and on-theme */
:deep(.splitpanes__splitter) {
  position: relative;
  background: rgba(100,116,139,0.25);
}
/* Remove default grip dots */
:deep(.splitpanes__splitter::before),
:deep(.splitpanes__splitter::after) {
  display: none !important;
}

:deep(.splitpanes__splitter:hover) { background: rgba(100,116,139,0.35); }
:deep(.splitpanes--horizontal > .splitpanes__splitter) { height: 2px; }
:deep(.splitpanes--horizontal > .splitpanes__splitter:hover) { background: rgba(148,163,184,0.2); }
:deep(.splitpanes--vertical > .splitpanes__splitter) { width: 2px; }
:deep(.splitpanes--vertical > .splitpanes__splitter:hover) { background: rgba(148,163,184,0.2); }

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
.panel::before { content: none; }
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
.panel-sm { 
  /* flex: 35; - Controlled by Splitpanes */
  min-height: 0;
  display: flex; 
  flex-direction: column;
}

/* AI Panel styling */
.panel-ai { min-height: 0; /* flex: 20; - Controlled by Splitpanes */ }
.ai-content {
  flex: 1; padding: 12px; display: flex; flex-direction: column;
  justify-content: center; overflow-y: auto;
}
.ai-summary {
  font-size: 15px; line-height: 1.7; color: #e2e8f0;
}
.ai-summary p { margin: 0; }
.ai-thinking {
  color: #22d3ee; font-style: italic;
  animation: pulse-text 1.5s ease-in-out infinite;
}
.ai-error { color: #94a3b8; }
@keyframes pulse-text { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

/* ========== Safety Supervision Panel ========== */
.panel-safety { 
  /* flex: 45; - Controlled by Splitpanes */
  display: flex; flex-direction: column; overflow: hidden;
  background: transparent;
  padding: 0; min-height: 0;
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
  border: 1px dashed var(--score-shadow, rgba(34,211,238,0.3));
  border-radius: 50%;
  animation: spin 10s linear infinite;
  pointer-events: none;
}
.tech-ring::before {
  content: ''; position: absolute; top: -2px; left: 50%;
  width: 10px; height: 4px; background: var(--score-color, #22d3ee);
  transform: translateX(-50%);
  box-shadow: 0 0 10px var(--score-color, #22d3ee);
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
  overflow: hidden;
}

/* Tech Stripes Pattern */
.p-bar::before {
  content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
  background-image: repeating-linear-gradient(
    45deg,
    rgba(255,255,255,0.15) 0px,
    rgba(255,255,255,0.15) 6px,
    transparent 6px,
    transparent 12px
  );
  z-index: 1;
}

/* Shine/Scan Animation */
.p-bar::after {
  content: ''; position: absolute; top: 0; left: 0; bottom: 0; width: 100%;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255,255,255,0.6) 50%,
    transparent 100%
  );
  transform: translateX(-100%);
  animation: bar-shine 2.5s infinite ease-in-out;
  z-index: 2;
}

@keyframes bar-shine {
  0% { transform: translateX(-100%); }
  60%, 100% { transform: translateX(100%); }
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

.tooltip {
  background: rgba(15,23,42,0.95); backdrop-filter: blur(10px);
  border: 1px solid #22d3ee; padding: 0; font-size: 11px; width: 220px;
  border-radius: 8px;
  box-shadow: 0 0 30px rgba(34,211,238,0.3);
  overflow: hidden;
}

.global-tooltip {
  position: fixed;
  z-index: 9999 !important;
  margin-bottom: 0;
  pointer-events: none; /* Let clicks pass through if needed, or auto to allow interaction */
  transition: opacity 0.2s, transform 0.2s;
}

.global-tooltip.top {
  transform: translate(-50%, -100%);
}

.global-tooltip.bottom {
  transform: translate(-50%, 0);
}

/* ========== LEFT COLUMN: Instruments Grid ========== */
.instruments-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  grid-template-rows: repeat(2, minmax(0, 1fr)); /* Allow shrinking below content size */
  gap: 8px; /* Slightly reduced gap */
  padding: 8px; /* Slightly reduced padding */
  flex: 1;
  min-height: 0; /* Critical for flex child to shrink */
  overflow: hidden;
}
.instrument-card {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 0; /* Critical for grid item to shrink */
  overflow: hidden; /* Ensure content doesn't spill */
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
  margin-bottom: 4px;
  padding-bottom: 4px;
  border-bottom: 1px dashed rgba(255,255,255,0.1);
  min-height: 24px;
}
.inst-name {
  font-size: 14px; font-weight: 700; color: #fff;
  text-shadow: 0 0 10px rgba(255,255,255,0.3);
  letter-spacing: 0.5px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.inst-color {
  width: 6px; height: 6px; border-radius: 50%;
  background-color: var(--card-color);
  box-shadow: 0 0 8px var(--card-color), 0 0 14px var(--card-color);
  animation: pulse-dot 2s infinite;
  flex-shrink: 0; margin-left: 8px;
}
@keyframes pulse-dot { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }

.inst-desc {
  font-size: 11px; color: #cbd5e1;
  margin-bottom: auto; /* Push footer to bottom */
  line-height: 1.3;
  overflow: hidden; text-overflow: ellipsis; 
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
}

.inst-footer {
  display: flex; align-items: flex-end; justify-content: space-between;
  margin-top: 4px;
}
.sensor-count {
  font-size: 20px; font-weight: 700;
  color: var(--card-color, #22d3ee);
  font-family: 'Chakra Petch', monospace;
  line-height: 1;
  text-shadow: 0 0 15px rgba(34, 211, 238, 0.4);
}
.sensor-types {
  font-size: 11px; color: #94a3b8;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 2px;
  font-family: 'Rajdhani', sans-serif;
}
.empty-instruments {
  text-align: center; color: #475569;
  padding: 15px; font-size: 11px; line-height: 1.5;
}

/* Carousel Transition */
.inst-fade-enter-active,
.inst-fade-leave-active {
  transition: opacity 0.4s ease, transform 0.4s ease;
}
.inst-fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}
.inst-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* Carousel Pagination Dots */
.carousel-dots {
  grid-column: 1 / -1;
  display: flex;
  justify-content: center;
  gap: 6px;
  padding: 6px 0;
}
.carousel-dots .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(148, 163, 184, 0.3);
  cursor: pointer;
  transition: all 0.3s ease;
}
.carousel-dots .dot.active {
  background: #22d3ee;
  box-shadow: 0 0 8px #22d3ee;
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
.donut-label .txt { font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 2px; font-family: 'Rajdhani', sans-serif; font-weight: 600; }

/* ========== CENTER: Alert Bar ========== */
.col-center { display: flex; flex-direction: column; gap: 10px; }
.center-top { flex: 2; display: flex; flex-direction: column; gap: 8px; min-height: 0; }

/* ========== CENTER: Map Area ========== */
.map-box {
  flex: 1; position: relative; min-height: 0;
  background: radial-gradient(ellipse at center, rgba(30,41,59,0.8) 0%, rgba(15,23,42,0.95) 70%);
  border: 1px solid rgba(34,211,238,0.15);
  border-radius: 8px;
}
/* Placeholder 3D Building Image */
.map-bg-image {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%;
  object-fit: cover; opacity: 0.6; pointer-events: none;
}
.map-3d { width: 100%; height: 100%; position: relative; z-index: 1; }

/* ========== Markers: Breathing Light Bubbles ========== */
.marker { position: absolute; cursor: pointer; transform: translate(-50%, -50%); z-index: 10; }
.marker.z-top { z-index: 2000; }
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
  display: none; /* Hide original tooltip styles just in case */
}
.tt-header {
  background: rgba(34,211,238,0.1); padding: 8px 12px;
  border-bottom: 1px solid rgba(34,211,238,0.2);
  display: flex; justify-content: space-between; align-items: center;
}
.tt-title { font-weight: 700; color: #fff; margin: 0; font-size: 13px; }
.tt-status { margin: 0; font-size: 10px; padding: 2px 6px; border-radius: 4px; background: rgba(34,211,238,0.2); color: #22d3ee; }
.tt-status.alarm-text { background: rgba(239,68,68,0.2); color: #ef4444; }

.tt-stats { display: flex; padding: 8px 12px; border-bottom: 1px solid rgba(255,255,255,0.05); gap: 8px; }
.tt-stat-item { flex: 1; display: flex; flex-direction: column; align-items: center; }
.tt-stat-item span { font-size: 9px; color: #94a3b8; }
.tt-stat-item b { font-size: 14px; color: #fff; font-family: 'Chakra Petch', sans-serif; }
.tt-stat-item .warn-val { color: #fbbf24; }

.tt-sensors { padding: 8px 12px; max-height: 150px; overflow-y: auto; }
.tt-sensor-row { display: flex; justify-content: space-between; margin-bottom: 4px; padding-bottom: 4px; border-bottom: 1px dashed rgba(255,255,255,0.1); }
.tt-sensor-row:last-child { border-bottom: none; margin-bottom: 0; }
.tt-sensors .s-name { color: #cbd5e1; }
.tt-sensors .s-val { color: #22d3ee; font-weight: 700; font-family: 'Courier New', monospace; }
.tt-sensors .alarm-val { color: #ef4444; animation: blink 1s infinite; }


/* ========== CENTER: Metrics Grid ========== */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 8px;
  height: 65px;
}

.metric-card {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(34, 211, 238, 0.2);
  /* Cut corners */
  clip-path: polygon(
    0 8px, 8px 0, 
    100% 0, 100% calc(100% - 8px), 
    calc(100% - 8px) 100%, 0 100%
  );
  padding: 6px 8px;
  transition: all 0.3s ease;
  box-shadow: inset 0 0 15px rgba(0,0,0,0.3);
}

.metric-card:hover {
  background: rgba(34, 211, 238, 0.1);
  border-color: rgba(34, 211, 238, 0.4);
  transform: translateY(-2px);
  box-shadow: inset 0 0 20px rgba(34, 211, 238, 0.1), 0 5px 15px rgba(0,0,0,0.3);
}

.mc-header {
  display: flex;
  align-items: center;
  gap: 6px;
  border-bottom: 1px dashed rgba(255,255,255,0.1);
  padding-bottom: 4px;
  margin-bottom: 2px;
}

.mc-dot {
  width: 6px;
  height: 6px;
  background: #22d3ee;
  border-radius: 50%;
  box-shadow: 0 0 8px #22d3ee;
  animation: pulse-dot 2s infinite;
}

.mc-label {
  font-size: 13px;
  color: #e2e8f0;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mc-body {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 2px;
  flex: 1;
}

.mc-value {
  font-size: 22px;
  font-weight: 700;
  color: #fff;
  font-family: 'Chakra Petch', monospace;
  text-shadow: 0 0 15px rgba(34, 211, 238, 0.5);
}

.mc-unit {
  font-size: 12px;
  color: #94a3b8;
  font-weight: 500;
}

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
.weather-panel { flex: 1; min-height: 0; }
.weather-main { display: flex; align-items: center; justify-content: center; gap: 16px; padding: 12px; }
.weather-main .icon { font-size: 40px; filter: drop-shadow(0 0 10px rgba(255,200,100,0.4)); }
.weather-main .temp {
  font-size: 36px; font-weight: 300;
  font-family: 'Courier New', monospace;
  color: #22d3ee;
  text-shadow: 0 0 15px rgba(34,211,238,0.5);
}
.weather-main .temp small { font-size: 16px; color: #64748b; }
.weather-details { display: flex; justify-content: space-around; padding: 10px; border-top: 1px solid rgba(34,211,238,0.1); font-size: 14px; }
.weather-details div { text-align: center; padding: 6px 10px; background: rgba(34,211,238,0.05); border-radius: 6px; }
.weather-details span { display: block; color: #cbd5e1; font-size: 12px; margin-bottom: 3px; }
.weather-details b { color: #f1f5f9; font-weight: 600; font-family: 'Courier New', monospace; font-size: 14px; }
.weather-details .good { color: #22c55e; text-shadow: 0 0 8px rgba(34,197,94,0.4); }

/* ========== RIGHT: Device List ========== */
.device-panel { flex: 2; min-height: 0; }
.device-list { flex: 1; overflow: hidden; padding: 6px; position: relative; }
.device-item {
  display: flex; align-items: center; padding: 8px 10px;
  border-radius: 6px; margin-bottom: 4px; gap: 8px;
  background: rgba(30,41,59,0.4);
  border: 1px solid transparent; transition: all 0.2s; cursor: pointer;
}
.device-item:hover { background: rgba(34,211,238,0.08); border-color: rgba(34,211,238,0.2); }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: #475569; }
.status-dot.online { background: #22c55e; box-shadow: 0 0 8px rgba(34,197,94,0.6); }
.d-name { flex: 1; font-size: 13px; font-weight: 500; color: #e2e8f0; }
.d-val {
  font-size: 14px; font-weight: 700;
  font-family: 'Courier New', monospace;
  color: #22d3ee;
  text-shadow: 0 0 8px rgba(34,211,238,0.4);
}
.d-val.alarm { color: #f87171; text-shadow: 0 0 8px rgba(248,113,113,0.4); }
.d-val small { font-size: 11px; color: #94a3b8; font-weight: 400; }

/* Signal Type & Bars */
.d-signal {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-right: 8px;
}
.signal-type {
  font-size: 10px;
  font-weight: 600;
  color: #94a3b8;
  background: rgba(100, 116, 139, 0.25);
  padding: 2px 5px;
  border-radius: 3px;
}
.wifi-signal {
  position: relative;
  width: 16px;
  height: 12px;
  display: flex;
  justify-content: center;
  align-items: flex-end;
  margin-right: 2px;
  overflow: hidden;
}
.wifi-arc {
  position: absolute;
  border-radius: 50%;
  border: 2px solid rgba(148, 163, 184, 0.3);
  border-bottom-color: transparent !important;
  border-left-color: transparent !important;
  border-right-color: transparent !important;
  opacity: 1; /* Always visible but dim */
}
/* Dot */
.wifi-arc.arc-1 { width: 3px; height: 3px; background: rgba(148, 163, 184, 0.3); border: none; bottom: 0; left: 50%; transform: translateX(-50%); border-radius: 50%; }
.wifi-arc.arc-1.active { background: #22d3ee; box-shadow: 0 0 5px rgba(34, 211, 238, 0.8); }

/* Arcs */
.wifi-arc.arc-2 { width: 10px; height: 10px; bottom: -3px; left: 50%; transform: translateX(-50%); }
.wifi-arc.arc-3 { width: 16px; height: 16px; bottom: -6px; left: 50%; transform: translateX(-50%); }
.wifi-arc.arc-4 { width: 22px; height: 22px; bottom: -9px; left: 50%; transform: translateX(-50%); }

.wifi-arc.active { border-color: #22d3ee; box-shadow: 0 -1px 3px rgba(34, 211, 238, 0.3); }

/* Cell Bars (Improved) */
.cell-signal {
  display: flex;
  align-items: flex-end;
  gap: 1.5px;
  height: 12px;
  padding-bottom: 1px;
}
.cell-signal .bar {
  width: 3px;
  background: rgba(100, 116, 139, 0.3);
  border-radius: 1px;
}
.cell-signal .bar:nth-child(1) { height: 3px; }
.cell-signal .bar:nth-child(2) { height: 6px; }
.cell-signal .bar:nth-child(3) { height: 9px; }
.cell-signal .bar:nth-child(4) { height: 12px; }
.cell-signal .bar.active {
  background: #22d3ee;
  box-shadow: 0 0 4px rgba(34, 211, 238, 0.5);
}

/* Critical / Warning State */
.wifi-signal.signal-critical .wifi-arc.active { border-color: #f87171; box-shadow: 0 -1px 3px rgba(248, 113, 113, 0.4); animation: signal-pulse 1.5s infinite; }
.wifi-signal.signal-critical .wifi-arc.arc-1.active { background: #f87171; box-shadow: 0 0 5px rgba(248, 113, 113, 0.8); }
.cell-signal.signal-critical .bar.active {
  background: #f87171;
  box-shadow: 0 0 4px rgba(248, 113, 113, 0.6);
  animation: signal-pulse 1.5s ease-in-out infinite;
}
@keyframes signal-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Device Alarm Glow Animation */
@keyframes alarm-glow {
  0%, 100% {
    box-shadow: 0 0 5px rgba(239, 68, 68, 0.4), inset 0 0 10px rgba(239, 68, 68, 0.1);
    border-color: rgba(239, 68, 68, 0.4);
  }
  50% {
    box-shadow: 0 0 15px rgba(239, 68, 68, 0.7), 0 0 30px rgba(239, 68, 68, 0.4), inset 0 0 15px rgba(239, 68, 68, 0.2);
    border-color: rgba(239, 68, 68, 0.8);
  }
}
.device-item.device-alarm {
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.4);
  animation: alarm-glow 1.5s ease-in-out infinite;
}
.device-item.device-alarm .d-name {
  color: #fca5a5;
}

/* ========== RIGHT: Alarm List ========== */
.alarm-panel { flex: 1; min-height: 0; }
.alarm-list { flex: 1; overflow: hidden; padding: 6px; position: relative; }
.alarm-item {
  display: flex; 
  align-items: center;
  gap: 10px;
  padding: 8px 10px; 
  border-radius: 6px; 
  margin-bottom: 4px;
  background: rgba(239,68,68,0.06); 
  border-left: 3px solid #f87171;
  font-size: 12px;
  transition: all 0.2s;
}
.alarm-item:hover {
  background: rgba(239,68,68,0.12);
}
.a-time { 
  flex-shrink: 0;
  color: #cbd5e1; 
  font-family: 'Courier New', monospace;
  font-size: 12px;
  font-weight: 600;
}
.a-info {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}
.a-name { 
  color: #f1f5f9;
  font-weight: 500;
  font-size: 13px;
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.a-type {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  white-space: nowrap;
}
/* Alarm type colors */
.a-type.type-high {
  background: rgba(239, 68, 68, 0.2);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.3);
}
.a-type.type-offline {
  background: rgba(100, 116, 139, 0.2);
  color: #94a3b8;
  border: 1px solid rgba(100, 116, 139, 0.3);
}
.a-type.type-battery {
  background: rgba(251, 191, 36, 0.2);
  color: #fbbf24;
  border: 1px solid rgba(251, 191, 36, 0.3);
}
.a-type.type-signal {
  background: rgba(168, 85, 247, 0.2);
  color: #a855f7;
  border: 1px solid rgba(168, 85, 247, 0.3);
}
.a-type.type-unknown {
  background: rgba(100, 116, 139, 0.15);
  color: #64748b;
  border: 1px solid rgba(100, 116, 139, 0.2);
}
.empty { text-align: center; color: #475569; padding: 24px; font-size: 12px; }

/* ========== WEATHER PANEL ========== */
.weather-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
  padding: 10px 0;
}

.weather-day {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.day-title {
  font-size: 18px;
  color: #e2e8f0;
  font-weight: 600;
}

.day-main {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.w-icon {
  font-size: 36px;
  line-height: 1;
  filter: drop-shadow(0 0 10px rgba(255, 255, 255, 0.3));
  animation: float-weather 3s ease-in-out infinite;
}

.w-temp {
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  font-family: 'Orbitron', sans-serif;
  text-shadow: 0 0 10px rgba(34, 211, 238, 0.4);
}

.day-detail {
  display: flex;
  flex-direction: column;
  align-items: center;
  font-size: 15px;
  color: #cbd5e1;
  gap: 3px;
}

.weather-divider {
  width: 1px;
  height: 60%;
  background: linear-gradient(to bottom, transparent, rgba(34, 211, 238, 0.3), transparent);
  margin: 0 10px;
}

.weather-loading, .weather-location {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: #94a3b8;
  font-size: 14px;
}

.weather-location {
  position: absolute;
  top: 10px;
  right: 15px;
  font-size: 12px;
  color: #64748b;
}

/* ========== ANIMATIONS ========== */
@keyframes float-weather {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-5px); }
}

.scroll-wrapper {
  display: flex;
  flex-direction: column;
  animation: scrollVertical linear infinite;
  will-change: transform;
}

.device-list:hover .scroll-wrapper,
.alarm-list:hover .scroll-wrapper {
  animation-play-state: paused;
}

@keyframes scrollVertical {
  0% { transform: translateY(0); }
  100% { transform: translateY(-50%); }
}

/* ========== SCROLLBAR ========== */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: rgba(30,41,59,0.3); border-radius: 2px; }
::-webkit-scrollbar-thumb { background: rgba(34,211,238,0.3); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: rgba(34,211,238,0.5); }
</style>

<!-- Global overrides for Splitpanes to ensure dots are removed -->
<style>
.splitpanes__splitter::before,
.splitpanes__splitter::after,
.default-theme.splitpanes .splitpanes__splitter::before,
.default-theme.splitpanes .splitpanes__splitter::after {
  display: none !important;
  content: '' !important;
  width: 0 !important;
  height: 0 !important;
  background: transparent !important;
}
</style>
