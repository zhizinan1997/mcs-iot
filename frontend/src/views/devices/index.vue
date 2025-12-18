<template>
  <div class="devices-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>传感器管理</span>
          <el-button type="primary" @click="showAddDialog">
            <el-icon><Plus /></el-icon> 添加传感器
          </el-button>
        </div>
      </template>

      <el-table :data="devices" stripe v-loading="loading" style="width: 100%" @sort-change="handleSortChange">
        <el-table-column type="index" label="#" width="50" align="center" />
        <el-table-column prop="instrument_name" label="仪表" min-width="140" sortable="custom">
          <template #default="{ row }">
            <span v-if="row.instrument_name" class="instrument-cell">
              <span class="color-dot" :style="{ backgroundColor: row.instrument_color || '#409eff' }"></span>
              {{ row.instrument_name }}
            </span>
            <span v-else style="color: #999">未分组</span>
          </template>
        </el-table-column>
        <el-table-column prop="sn" label="传感器编号" min-width="120" sortable="custom" />
        <el-table-column prop="name" label="传感器名称" min-width="150" sortable="custom">
          <template #default="{ row }">
            <el-input
              v-model="row.name"
              size="small"
              @change="() => handleQuickNameChange(row)"
              placeholder="输入名称"
            />
          </template>
        </el-table-column>
        <el-table-column prop="sensor_type" label="监测类型" width="160" align="center">
          <template #default="{ row }">
            <el-select
              v-model="row.sensor_type"
              size="small"
              @change="(val: string) => handleQuickTypeChange(row, val)"
            >
              <el-option
                v-for="type in sensorTypes"
                :key="type.value"
                :label="type.label"
                :value="type.value"
              />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column prop="unit" label="单位" width="120" align="center">
          <template #default="{ row }">
            <el-select
              v-model="row.unit"
              size="small"
              filterable
              allow-create
              @change="() => handleQuickUnitChange(row)"
            >
              <el-option
                v-for="unit in getUnitsForType(row.sensor_type)"
                :key="unit"
                :label="unit"
                :value="unit"
              />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80" align="center" sortable="custom">
          <template #default="{ row }">
            <el-tag
              :type="row.status === 'online' ? 'success' : 'info'"
              size="small"
            >
              {{ row.status === "online" ? "在线" : "离线" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="battery" label="电池" width="70" align="center" sortable="custom">
          <template #default="{ row }">
            <span
              v-if="row.battery != null"
              :style="{
                color:
                  row.battery < 20
                    ? '#F56C6C'
                    : row.battery < 50
                    ? '#E6A23C'
                    : '#67C23A',
              }"
            >
              {{ row.battery }}%
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="rssi" label="信号" width="85" align="center" sortable="custom">
          <template #default="{ row }">
            <span
              v-if="row.rssi != null"
              :style="{
                color:
                  row.rssi < -80
                    ? '#F56C6C'
                    : row.rssi < -70
                    ? '#E6A23C'
                    : '#67C23A',
              }"
            >
              {{ row.rssi }}dBm
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="network" label="网络" width="60" align="center">
          <template #default="{ row }">
            {{ row.network || "-" }}
          </template>
        </el-table-column>
        <el-table-column prop="last_ppm" label="当前浓度" width="110" align="right" sortable="custom">
          <template #default="{ row }">
            <span v-if="row.last_ppm != null" :class="{ 'alarm-value': row.last_ppm > row.high_limit }">
              {{ row.last_ppm.toFixed(1) }} {{ row.unit || 'ppm' }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="high_limit" label="报警阈值" width="100" align="center" sortable="custom">
          <template #default="{ row }">
            <el-input-number
              v-model="row.high_limit"
              size="small"
              :min="0"
              :step="10"
              controls-position="right"
              @change="() => handleQuickLimitChange(row)"
              style="width: 100%"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right" align="center">
          <template #default="{ row }">
            <el-button size="small" @click="editDevice(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteDevice(row.sn)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        :page-size="20"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="fetchDevices"
        class="pagination"
      />
    </el-card>

    <!-- Add/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑传感器' : '添加传感器'"
      width="600px"
    >
      <el-form :model="form" label-width="100px">
        <el-form-item label="传感器编号" required>
          <el-input
            v-model="form.sn"
            :disabled="isEdit"
            placeholder="如: A001"
          />
        </el-form-item>
        <el-form-item label="传感器名称">
          <el-input v-model="form.name" placeholder="如: 1号检测点" />
        </el-form-item>
        <el-form-item label="传感器型号">
          <el-input v-model="form.model" placeholder="如: MCS-100" />
        </el-form-item>
        <el-form-item label="监测类型">
          <el-select v-model="form.sensor_type" @change="handleTypeChange" placeholder="选择类型">
            <el-option
              v-for="type in sensorTypes"
              :key="type.value"
              :label="type.label"
              :value="type.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="单位">
          <el-select
            v-if="availableUnits.length > 0 && form.sensor_type !== 'custom'"
            v-model="form.unit"
            placeholder="选择单位"
          >
            <el-option
              v-for="unit in availableUnits"
              :key="unit"
              :label="unit"
              :value="unit"
            />
          </el-select>
          <el-input v-else v-model="form.unit" placeholder="输入单位" />
        </el-form-item>
        <el-form-item label="所属仪表">
          <el-select v-model="form.instrument_id" placeholder="选择仪表" clearable style="width: 100%">
            <el-option
              v-for="inst in instruments"
              :key="inst.id"
              :label="inst.name"
              :value="inst.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="传感器序号">
          <el-input-number v-model="form.sensor_order" :min="0" :max="99" />
          <span style="margin-left: 8px; color: #999">仪表内排序</span>
        </el-form-item>


        <el-divider>校准参数</el-divider>
        <el-alert
          title="PPM 计算公式"
          type="info"
          :closable="false"
          style="margin-bottom: 16px"
        >
          <div style="font-family: monospace; font-size: 14px">
            <strong>PPM = K × V_raw + B + T_coef × (T - 25)</strong>
          </div>
          <div style="margin-top: 8px; color: #666; font-size: 12px">
            其中 V_raw 为传感器原始电压，T 为环境温度
          </div>
        </el-alert>

        <el-form-item>
          <template #label>
            <span>K值 (斜率)</span>
            <el-tooltip content="线性校准斜率，通常为1.0" placement="top">
              <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
            </el-tooltip>
          </template>
          <el-input-number v-model="form.k_val" :precision="4" :step="0.1" />
          <span style="margin-left: 8px; color: #999">默认: 1.0</span>
        </el-form-item>

        <el-form-item>
          <template #label>
            <span>B值 (截距)</span>
            <el-tooltip content="线性校准截距，用于零点校正" placement="top">
              <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
            </el-tooltip>
          </template>
          <el-input-number v-model="form.b_val" :precision="4" :step="0.1" />
          <span style="margin-left: 8px; color: #999">默认: 0.0</span>
        </el-form-item>

        <el-form-item>
          <template #label>
            <span>温补系数</span>
            <el-tooltip
              content="温度补偿系数，补偿温度对传感器的影响"
              placement="top"
            >
              <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
            </el-tooltip>
          </template>
          <el-input-number v-model="form.t_coef" :precision="4" :step="0.01" />
          <span style="margin-left: 8px; color: #999">默认: 0.0 (无温补)</span>
        </el-form-item>

        <el-divider>报警阈值</el-divider>
        <el-form-item label="高报阈值">
          <el-input-number v-model="form.high_limit" :min="0" />
          <span style="margin-left: 8px; color: #999">ppm</span>
        </el-form-item>
        <el-form-item label="低报阈值">
          <el-input-number v-model="form.low_limit" :min="0" />
          <span style="margin-left: 8px; color: #999">ppm (可选)</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveDevice" :loading="saving"
          >保存</el-button
        >
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { QuestionFilled } from "@element-plus/icons-vue";
import { devicesApi, instrumentsApi } from "../../api";

interface Device {
  sn: string;
  name: string;
  model: string;
  sensor_type: string;
  unit: string;
  k_val: number;
  b_val: number;
  t_coef: number;
  high_limit: number;
  low_limit: number | null;
  instrument_id: number | null;
  instrument_name: string | null;
  sensor_order: number;
  status: string;
  last_ppm: number | null;
  battery: number | null;
  rssi: number | null;
  network: string | null;
}



interface Instrument {
  id: number;
  name: string;
}

const devices = ref<Device[]>([]);
const instruments = ref<Instrument[]>([]);
const loading = ref(false);
const saving = ref(false);
const page = ref(1);
const total = ref(0);

const dialogVisible = ref(false);
const isEdit = ref(false);

const form = reactive({
  sn: "",
  name: "",
  model: "",
  sensor_type: "custom",
  unit: "ppm",
  k_val: 1.0,
  b_val: 0.0,
  t_coef: 0.0,
  high_limit: 1000,
  low_limit: null as number | null,
  instrument_id: null as number | null,
  sensor_order: 0,
});

const sensorTypes = [
  { label: '氢气 (H2)', value: 'H2', units: ['ppm', '%'] },
  { label: '甲烷 (CH4)', value: 'CH4', units: ['ppm', '%'] },
  { label: '温度', value: 'Temperature', units: ['°C', '°F'] },
  { label: '湿度', value: 'Humidity', units: ['%RH'] },
  { label: 'VOCs', value: 'VOCs', units: ['ppm', '%'] },
  { label: 'PM2.5', value: 'PM2.5', units: ['μg/m³'] },
  { label: '自定义', value: 'custom', units: [] }
];

const availableUnits = ref<string[]>([]);

function handleTypeChange(val: string) {
  const type = sensorTypes.find(t => t.value === val);
  if (type) {
    availableUnits.value = type.units;
    if (type.value === 'custom') {
      form.unit = '';
    } else if (type.units.length > 0) {
      form.unit = type.units[0] || ''; // Default to first unit
    }
  } else {
    availableUnits.value = [];
  }
}

function getUnitsForType(typeVal: string) {
  const type = sensorTypes.find(t => t.value === typeVal);
  return type ? type.units : [];
}

async function handleQuickTypeChange(row: Device, newType: string) {
  // Update unit default if possible
  const typeDef = sensorTypes.find(t => t.value === newType);
  if (typeDef && typeDef.units.length > 0) {
    row.unit = typeDef.units[0] || '';
  }
  
  await updateDeviceRow(row);
}

async function handleQuickUnitChange(row: Device) {
  await updateDeviceRow(row);
}

async function handleQuickNameChange(row: Device) {
  await updateDeviceRow(row);
}

async function handleQuickLimitChange(row: Device) {
  await updateDeviceRow(row);
}

async function updateDeviceRow(row: Device) {
  try {
    const payload = {
        sn: row.sn,
        name: row.name,
        model: row.model,
        sensor_type: row.sensor_type,
        unit: row.unit,
        high_limit: row.high_limit,
        low_limit: row.low_limit,
        k_val: row.k_val,
        b_val: row.b_val,
        t_coef: row.t_coef,
        instrument_id: row.instrument_id,
        sensor_order: row.sensor_order
    };
    
    await devicesApi.update(row.sn, payload);
    ElMessage.success(`传感器 ${row.name || row.sn} 更新成功`);
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || "更新失败");
    fetchDevices(); // Refresh to restore state on error
  }
}

async function loadInstruments() {
  try {
    const res = await instrumentsApi.list();
    instruments.value = res.data.data;
  } catch (error) {
    console.error('Failed to load instruments:', error);
  }
}

async function fetchDevices() {
  loading.value = true;
  try {
    const res = await devicesApi.list(page.value);
    devices.value = res.data.data;
    total.value = res.data.total;
  } catch (error) {
    ElMessage.error("获取传感器列表失败");
  } finally {
    loading.value = false;
  }
}

function showAddDialog() {
  isEdit.value = false;
  Object.assign(form, {
    sn: "",
    name: "",
    model: "",
    sensor_type: "custom",
    unit: "ppm",
    k_val: 1.0,
    b_val: 0.0,
    t_coef: 0.0,
    high_limit: 1000,
    low_limit: null,
    instrument_id: null,
    sensor_order: 0,
  });
  handleTypeChange('custom');
  dialogVisible.value = true;
}

function editDevice(device: Device) {
  isEdit.value = true;
  Object.assign(form, device);
  // Initial unit options
  handleTypeChange(device.sensor_type);
  // Restore unit (handleTypeChange might reset it)
  form.unit = device.unit;
  dialogVisible.value = true;
}

async function saveDevice() {
  saving.value = true;
  try {
    if (isEdit.value) {
      await devicesApi.update(form.sn, form);
      ElMessage.success("传感器更新成功");
    } else {
      await devicesApi.create(form);
      ElMessage.success("传感器添加成功");
    }
    dialogVisible.value = false;
    fetchDevices();
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || "操作失败");
  } finally {
    saving.value = false;
  }
}

async function deleteDevice(sn: string) {
  try {
    await ElMessageBox.confirm("确定删除该传感器吗？", "确认删除", {
      type: "warning",
    });
    await devicesApi.delete(sn);
    ElMessage.success("传感器已删除");
    fetchDevices();
  } catch {}
}

function handleSortChange({ prop, order }: { prop: string; order: string | null }) {
  if (!order) {
    // 取消排序时恢复默认顺序
    fetchDevices();
    return;
  }
  
  const direction = order === 'ascending' ? 1 : -1;
  devices.value = [...devices.value].sort((a: any, b: any) => {
    let aVal = a[prop];
    let bVal = b[prop];
    
    // 处理 null 值
    if (aVal == null) aVal = '';
    if (bVal == null) bVal = '';
    
    // 数字比较
    if (typeof aVal === 'number' && typeof bVal === 'number') {
      return (aVal - bVal) * direction;
    }
    
    // 字符串比较
    return String(aVal).localeCompare(String(bVal)) * direction;
  });
}

onMounted(() => {
  fetchDevices();
  loadInstruments();
});
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination {
  margin-top: 20px;
  justify-content: flex-end;
}



.alarm-value {
  color: #f56c6c;
  font-weight: bold;
}

.instrument-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}

.color-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}
</style>
