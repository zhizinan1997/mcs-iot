<!--
  MCS-IOT 仪表管理页面 (Instrument Management)

  该文件负责管理“仪表”(Instrument) 实体，仪表是传感器的逻辑分组单元。
  主要职责：
  1. 仪表 CRUD：支持仪表的创建、编辑与删除，包含名称、描述、主题颜色及排序配置。
  2. 传感器关联管理：提供交互式弹出层，允许用户为特定仪表批量分配或移除传感器 (SN 关联)。
  3. 数据表格：以卡片式布局展示所有仪表及其绑定的传感器数量。

  技术栈：Vue 3 (setup), Element Plus Table, Dialog & ColorPicker.
-->
<template>
  <div class="instruments-page">
    <el-card class="full-card">
      <template #header>
        <div class="card-header">
          <el-button type="primary" @click="showAddDialog">
            <el-icon><Plus /></el-icon> 添加仪表
          </el-button>
        </div>
      </template>

      <el-table :data="instruments" stripe v-loading="loading" style="width: 100%">
        <el-table-column type="index" label="#" width="50" align="center" />
        <el-table-column prop="name" label="仪表名称" min-width="180">
          <template #default="{ row }">
            <span class="instrument-name">
              <span class="color-dot" :style="{ backgroundColor: row.color || '#409eff' }"></span>
              {{ row.name }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200">
          <template #default="{ row }">
            {{ row.description || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="sensor_count" label="传感器数" width="100" align="center">
          <template #default="{ row }">
            <el-tag type="info">{{ row.sensor_count }} 个</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="sort_order" label="排序" width="70" align="center" />
        <el-table-column label="操作" width="240" fixed="right" align="center">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="manageSensors(row)">管理传感器</el-button>
            <el-button size="small" @click="editInstrument(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteInstrument(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Add/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑仪表' : '添加仪表'"
      width="500px"
    >
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="如: 北京大学监控仪表" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="仪表描述信息" />
        </el-form-item>
        <el-form-item label="颜色">
          <el-color-picker v-model="form.color" />
        </el-form-item>

        <el-form-item label="排序号">
          <el-input-number v-model="form.sort_order" :min="0" :max="999" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveInstrument" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- Sensor Selection Dialog -->
    <el-dialog
      v-model="sensorDialogVisible"
      :title="`管理传感器 - ${currentInstrument?.name || ''}`"
      width="700px"
    >
      <p style="margin-bottom: 16px; color: #666;">勾选属于该仪表的传感器：</p>
      <el-table 
        :data="allDevices" 
        v-loading="loadingDevices"
        @selection-change="handleSelectionChange"
        ref="sensorTable"
        max-height="400"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="sn" label="设备编号" width="120" />
        <el-table-column prop="name" label="设备名称" min-width="150">
          <template #default="{ row }">
            {{ row.name || row.sn }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'online' ? 'success' : 'info'" size="small">
              {{ row.status === 'online' ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="当前仪表" width="140">
          <template #default="{ row }">
            <el-tag v-if="row.instrument_name" type="warning" size="small">{{ row.instrument_name }}</el-tag>
            <span v-else style="color: #999">未分配</span>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="sensorDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveSensorAssignment" :loading="savingSensors">
          保存分配 ({{ selectedSensors.length }} 个)
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { instrumentsApi, devicesApi } from '../../api'

interface Instrument {
  id: number
  name: string
  description: string | null
  color: string
  sort_order: number
  sensor_count: number
}



interface Device {
  sn: string
  name: string | null
  status: string
  instrument_id: number | null
  instrument_name: string | null
}

const instruments = ref<Instrument[]>([])
const allDevices = ref<Device[]>([])
const loading = ref(false)
const saving = ref(false)
const loadingDevices = ref(false)
const savingSensors = ref(false)

const dialogVisible = ref(false)
const sensorDialogVisible = ref(false)
const isEdit = ref(false)
const currentInstrumentId = ref<number | null>(null)
const currentInstrument = ref<Instrument | null>(null)
const selectedSensors = ref<Device[]>([])
const sensorTable = ref<any>(null)

const form = reactive({
  name: '',
  description: '',
  color: '#409eff',
  sort_order: 0
})

async function fetchInstruments() {
  loading.value = true
  try {
    const res = await instrumentsApi.list()
    instruments.value = res.data.data
  } catch (error) {
    ElMessage.error('获取仪表列表失败')
  } finally {
    loading.value = false
  }
}



async function loadAllDevices() {
  loadingDevices.value = true
  try {
    const res = await devicesApi.list(1, 100)
    allDevices.value = res.data.data
  } catch (error) {
    ElMessage.error('获取设备列表失败')
  } finally {
    loadingDevices.value = false
  }
}

function showAddDialog() {
  isEdit.value = false
  currentInstrumentId.value = null
  Object.assign(form, {
    name: '',
    description: '',
    color: '#409eff',
    sort_order: 0
  })
  dialogVisible.value = true
}

function editInstrument(instrument: Instrument) {
  isEdit.value = true
  currentInstrumentId.value = instrument.id
  Object.assign(form, {
    name: instrument.name,
    description: instrument.description || '',
    color: instrument.color || '#409eff',
    sort_order: instrument.sort_order
  })
  dialogVisible.value = true
}

async function saveInstrument() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入仪表名称')
    return
  }
  
  saving.value = true
  try {
    if (isEdit.value && currentInstrumentId.value) {
      await instrumentsApi.update(currentInstrumentId.value, form)
      ElMessage.success('仪表更新成功')
    } else {
      await instrumentsApi.create(form)
      ElMessage.success('仪表添加成功')
    }
    dialogVisible.value = false
    fetchInstruments()
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function deleteInstrument(id: number) {
  try {
    await ElMessageBox.confirm('确定要删除该仪表吗？关联的传感器将被取消关联。', '确认删除', {
      type: 'warning'
    })
    await instrumentsApi.delete(id)
    ElMessage.success('删除成功')
    fetchInstruments()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

async function manageSensors(instrument: Instrument) {
  currentInstrument.value = instrument
  currentInstrumentId.value = instrument.id
  sensorDialogVisible.value = true
  
  await loadAllDevices()
  
  // 在数据加载完成后设置选中状态
  await nextTick()
  if (sensorTable.value) {
    allDevices.value.forEach(device => {
      if (device.instrument_id === instrument.id) {
        sensorTable.value.toggleRowSelection(device, true)
      }
    })
  }
}

function handleSelectionChange(selection: Device[]) {
  selectedSensors.value = selection
}

async function saveSensorAssignment() {
  if (!currentInstrumentId.value) return
  
  savingSensors.value = true
  try {
    // 遍历所有设备，更新其 instrument_id
    const updates: Promise<any>[] = []
    
    for (const device of allDevices.value) {
      const wasSelected = device.instrument_id === currentInstrumentId.value
      const isSelected = selectedSensors.value.some(s => s.sn === device.sn)
      
      if (isSelected && !wasSelected) {
        // 新增分配到此仪表
        updates.push(devicesApi.update(device.sn, {
          ...device,
          instrument_id: currentInstrumentId.value,
          sensor_order: selectedSensors.value.findIndex(s => s.sn === device.sn)
        }))
      } else if (!isSelected && wasSelected) {
        // 从此仪表移除
        updates.push(devicesApi.update(device.sn, {
          ...device,
          instrument_id: null,
          sensor_order: 0
        }))
      }
    }
    
    await Promise.all(updates)
    ElMessage.success('传感器分配已保存')
    sensorDialogVisible.value = false
    fetchInstruments()
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    savingSensors.value = false
  }
}

onMounted(() => {
  fetchInstruments()
})
</script>

<style scoped>
.instruments-page {
  padding: 0;
  height: 100%;
  padding: 24px;
}

:deep(.full-card) {
  height: 100%;
  border-radius: 24px !important;
  border: 1px solid rgba(255, 255, 255, 0.6) !important;
  background: rgba(255, 255, 255, 0.65) !important;
  backdrop-filter: blur(20px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.04) !important;
  display: flex;
  flex-direction: column;
}

:deep(.full-card .el-card__header) {
  padding: 20px 32px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  background: transparent;
  flex-shrink: 0;
}

:deep(.full-card .el-card__body) {
  padding: 0;
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.card-header {
  display: flex;
  justify-content: flex-end;
  align-items: center;
}

/* Glass Table Styling */
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

/* Dialog Glass */
:deep(.el-dialog) {
  border-radius: 24px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  box-shadow: 0 20px 40px rgba(0,0,0,0.1);
}

:deep(.el-dialog__header) {
  margin-right: 0;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

:deep(.el-dialog__title) {
  font-weight: 600;
  color: #1d1d1f;
}

:deep(.el-dialog__body) {
  padding: 24px;
}

.instrument-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #1d1d1f;
}

.color-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
</style>
