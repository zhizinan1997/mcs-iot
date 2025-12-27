<template>
  <div class="users-container">
    <el-card class="main-card">
      <template #header>
        <div class="card-header">
          <span>子账号管理</span>
          <el-button type="primary" @click="showAddDialog">
            <el-icon><Plus /></el-icon>
            新增子账号
          </el-button>
        </div>
      </template>
      
      <el-table :data="users" v-loading="loading" stripe>
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="email" label="邮箱" width="180">
          <template #default="{ row }">
            {{ row.email || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="phone" label="手机号" width="140">
          <template #default="{ row }">
            {{ row.phone || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="权限" min-width="300">
          <template #default="{ row }">
            <div class="permission-tags">
              <el-tag 
                v-for="(label, key) in permissionLabels" 
                :key="key"
                :type="row.permissions[key] ? 'success' : 'info'"
                size="small"
                :effect="row.permissions[key] ? 'dark' : 'plain'"
              >
                {{ label }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showEditDialog(row)">编辑权限</el-button>
            <el-button size="small" type="warning" @click="showPasswordDialog(row)">改密</el-button>
            <el-popconfirm
              title="确定要删除该用户吗？"
              @confirm="handleDelete(row.id)"
            >
              <template #reference>
                <el-button size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑子账号' : '新增子账号'"
      width="600px"
      destroy-on-close
    >
      <el-form :model="form" label-width="100px" :rules="formRules" ref="formRef">
        <el-form-item label="用户名" prop="username" v-if="!isEdit">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="用户名" v-else>
          <el-input :value="form.username" disabled />
        </el-form-item>
        <el-form-item label="密码" prop="password" v-if="!isEdit">
          <el-input v-model="form.password" type="password" placeholder="请输入密码 (至少6位)" show-password />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="可选" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" placeholder="可选" />
        </el-form-item>
        <el-form-item label="状态" v-if="isEdit">
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="禁用" />
        </el-form-item>
        <el-form-item label="功能权限">
          <div class="permission-grid">
            <el-checkbox
              v-for="(label, key) in permissionLabels"
              :key="key"
              :model-value="form.permissions[key as keyof typeof form.permissions]"
              @update:model-value="(val: boolean) => form.permissions[key as keyof typeof form.permissions] = val"
            >
              {{ label }}
            </el-checkbox>
          </div>
          <div class="permission-actions">
            <el-button size="small" @click="selectAllPermissions">全选</el-button>
            <el-button size="small" @click="clearAllPermissions">清空</el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 修改密码对话框 -->
    <el-dialog v-model="passwordDialogVisible" title="修改密码" width="400px">
      <el-form :model="passwordForm" label-width="80px" :rules="passwordRules" ref="passwordFormRef">
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="passwordForm.new_password" type="password" placeholder="请输入新密码 (至少6位)" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input v-model="passwordForm.confirm_password" type="password" placeholder="请再次输入新密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handlePasswordChange" :loading="submitting">确认修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { usersApi } from '../../api'

interface UserPermissions {
  dashboard: boolean
  devices: boolean
  instruments: boolean
  alarms: boolean
  logs: boolean
  ai: boolean
  license: boolean
  archive: boolean
  health: boolean
  config: boolean
  screen: boolean
}

interface User {
  id: number
  username: string
  role: string
  email: string | null
  phone: string | null
  permissions: UserPermissions
  is_active: boolean
  last_login: string | null
  created_at: string
}

const permissionLabels: Record<string, string> = {
  dashboard: '仪表盘',
  devices: '设备管理',
  instruments: '仪表管理',
  alarms: '报警记录',
  logs: '服务器日志',
  ai: 'AI接口',
  license: '授权管理',
  archive: '数据归档',
  health: '系统自检',
  config: '系统配置',
  screen: '可视化大屏'
}

const defaultPermissions = (): UserPermissions => ({
  dashboard: true,
  devices: false,
  instruments: false,
  alarms: true,
  logs: false,
  ai: false,
  license: false,
  archive: false,
  health: false,
  config: false,
  screen: true
})

const loading = ref(false)
const submitting = ref(false)
const users = ref<User[]>([])
const dialogVisible = ref(false)
const passwordDialogVisible = ref(false)
const isEdit = ref(false)
const editingUserId = ref<number | null>(null)
const formRef = ref()
const passwordFormRef = ref()

const form = reactive({
  username: '',
  password: '',
  email: '',
  phone: '',
  is_active: true,
  permissions: defaultPermissions()
})

const passwordForm = reactive({
  new_password: '',
  confirm_password: ''
})

const formRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 32, message: '用户名长度为 2-32 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 64, message: '密码长度为 6-64 个字符', trigger: 'blur' }
  ]
}

const passwordRules = {
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 64, message: '密码长度为 6-64 个字符', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (_rule: any, value: string, callback: any) => {
        if (value !== passwordForm.new_password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

onMounted(() => {
  loadUsers()
})

async function loadUsers() {
  loading.value = true
  try {
    const res = await usersApi.list()
    users.value = res.data.users || []
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '加载用户列表失败')
  } finally {
    loading.value = false
  }
}

function showAddDialog() {
  isEdit.value = false
  editingUserId.value = null
  form.username = ''
  form.password = ''
  form.email = ''
  form.phone = ''
  form.is_active = true
  form.permissions = defaultPermissions()
  dialogVisible.value = true
}

function showEditDialog(user: User) {
  isEdit.value = true
  editingUserId.value = user.id
  form.username = user.username
  form.password = ''
  form.email = user.email || ''
  form.phone = user.phone || ''
  form.is_active = user.is_active
  form.permissions = { ...defaultPermissions(), ...user.permissions }
  dialogVisible.value = true
}

function showPasswordDialog(user: User) {
  editingUserId.value = user.id
  passwordForm.new_password = ''
  passwordForm.confirm_password = ''
  passwordDialogVisible.value = true
}

function selectAllPermissions() {
  Object.keys(form.permissions).forEach(key => {
    form.permissions[key as keyof UserPermissions] = true
  })
}

function clearAllPermissions() {
  Object.keys(form.permissions).forEach(key => {
    form.permissions[key as keyof UserPermissions] = false
  })
}

async function handleSubmit() {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  
  submitting.value = true
  try {
    if (isEdit.value && editingUserId.value) {
      await usersApi.update(editingUserId.value, {
        permissions: form.permissions,
        email: form.email || null,
        phone: form.phone || null,
        is_active: form.is_active
      })
      ElMessage.success('更新成功')
    } else {
      await usersApi.create({
        username: form.username,
        password: form.password,
        permissions: form.permissions,
        email: form.email || null,
        phone: form.phone || null
      })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadUsers()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function handlePasswordChange() {
  if (!passwordFormRef.value) return
  
  try {
    await passwordFormRef.value.validate()
  } catch {
    return
  }
  
  if (!editingUserId.value) return
  
  submitting.value = true
  try {
    await usersApi.changePassword(editingUserId.value, passwordForm.new_password)
    ElMessage.success('密码修改成功')
    passwordDialogVisible.value = false
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '密码修改失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(id: number) {
  try {
    await usersApi.delete(id)
    ElMessage.success('删除成功')
    loadUsers()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '删除失败')
  }
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.users-container {
  padding: 0;
}

.main-card {
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.6);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 18px;
  font-weight: 600;
}

.permission-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.permission-tags .el-tag {
  font-size: 11px;
}

.permission-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px 8px;
}

.permission-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

:deep(.el-dialog) {
  border-radius: 16px;
}
</style>
