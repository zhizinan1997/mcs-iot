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
      
      <el-table :data="devices" stripe>
        <el-table-column prop="sn" label="设备编号" width="150" />
        <el-table-column prop="name" label="设备名称" />
        <el-table-column prop="ppm" label="浓度 (PPM)">
          <template #default="{ row }">
            <span :class="{ 'alarm-value': row.ppm > 1000 }">
              {{ row.ppm?.toFixed(2) || '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="temp" label="温度 (°C)">
          <template #default="{ row }">
            {{ row.temp?.toFixed(1) || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'online' ? 'success' : 'info'">
              {{ row.status === 'online' ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { dashboardApi } from '../../api'

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
}

const stats = ref<Stats>({
  devices_total: 0,
  devices_online: 0,
  devices_offline: 0,
  devices_alarm: 0,
  alarms_today: 0
})

const devices = ref<Device[]>([])

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
</style>
