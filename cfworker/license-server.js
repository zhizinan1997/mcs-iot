/**
 * MCS-IoT License Server (Optimized)
 * Deployed on Cloudflare Workers
 */

export default {
    async fetch(request, env) {
        // Handle CORS preflight
        if (request.method === "OPTIONS") {
            return new Response(null, {
                headers: {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization",
                },
            });
        }

        const url = new URL(request.url);

        // Serve Web UI
        if (request.method === "GET" && url.pathname === "/admin") {
            return new Response(ADMIN_HTML, {
                headers: { "Content-Type": "text/html" }
            });
        }

        // Verify License API
        if (request.method === "POST" && url.pathname === "/verify") {
            return handleVerify(request, env);
        }

        // Admin API: Add/Update License
        if (request.method === "POST" && url.pathname === "/admin/add") {
            return handleAddLicense(request, env);
        }

        // Admin API: Delete License/Log
        if (request.method === "POST" && url.pathname === "/admin/delete") {
            return handleDelete(request, env);
        }

        // Admin API: List Licenses
        if (request.method === "GET" && url.pathname === "/admin/list") {
            return handleListLicenses(request, env);
        }

        // Admin API: Get Tamper Logs
        if (request.method === "GET" && url.pathname === "/admin/tamper-logs") {
            return handleTamperLogs(request, env);
        }

        return new Response("Not found", { status: 404 });
    },
};

// =============================================================================
// API Handlers
// =============================================================================

async function handleVerify(request, env) {
    try {
        const { device_id, integrity_hash } = await request.json();

        if (!device_id) {
            return Response.json(
                { valid: false, error: "Missing device_id" },
                { status: 400, headers: corsHeaders() }
            );
        }

        const licenseData = await env.LICENSES.get(`license:${device_id}`, "json");

        if (!licenseData) {
            return Response.json(
                { valid: false, error: "授权不存在", tampered: false },
                { headers: corsHeaders() }
            );
        }

        // Check Status
        if (licenseData.status === "disabled") {
             return Response.json(
                { valid: false, error: "授权已被禁用", tampered: false },
                { headers: corsHeaders() }
            );
        }

        // Check Expiry
        if (new Date(licenseData.expires_at) < new Date()) {
            return Response.json(
                { valid: false, error: "授权已过期", tampered: false },
                { headers: corsHeaders() }
            );
        }

        // Check integrity hash if provided
        let tampered = false;
        if (integrity_hash && licenseData.expected_hash) {
            if (integrity_hash !== licenseData.expected_hash) {
                tampered = true;
                
                // Auto-report tampering
                const tamperReport = {
                    device_id,
                    customer: licenseData.customer,
                    expected_hash: licenseData.expected_hash,
                    actual_hash: integrity_hash,
                    timestamp: new Date().toISOString()
                };
                
                const reportKey = `tamper:${device_id}:${Date.now()}`;
                await env.LICENSES.put(reportKey, JSON.stringify(tamperReport));
            }
        }

        return Response.json(
            {
                valid: true,
                customer: licenseData.customer,
                expires_at: licenseData.expires_at,
                features: licenseData.features || ["mqtt_external", "ai", "r2_archive", "notifications"],
                tampered: tampered
            },
            { headers: corsHeaders() }
        );
    } catch (e) {
        return Response.json(
            { valid: false, error: "Internal Server Error", tampered: false },
            { status: 500, headers: corsHeaders() }
        );
    }
}

async function handleAddLicense(request, env) {
    if (!checkAuth(request, env)) return new Response("Unauthorized", { status: 401, headers: corsHeaders() });

    try {
        const payload = await request.json();
        const { device_id, customer, expires_at, features, expected_hash, status } = payload;

        if (!device_id) return Response.json({ error: "Missing device ID" }, { status: 400, headers: corsHeaders() });

        // Check if exists to preserve created_at
        const existing = await env.LICENSES.get(`license:${device_id}`, "json");
        const created_at = existing ? existing.created_at : new Date().toISOString();

        const licenseData = {
            device_id,
            status: status || "active",
            customer,
            expires_at,
            features: features || ["mqtt_external", "ai", "r2_archive", "notifications"],
            expected_hash: expected_hash || "",
            created_at: created_at,
            updated_at: new Date().toISOString()
        };

        await env.LICENSES.put(`license:${device_id}`, JSON.stringify(licenseData));

        return Response.json({ success: true, data: licenseData }, { headers: corsHeaders() });
    } catch (e) {
        return Response.json({ error: e.message }, { status: 500, headers: corsHeaders() });
    }
}

async function handleListLicenses(request, env) {
    if (!checkAuth(request, env)) return new Response("Unauthorized", { status: 401, headers: corsHeaders() });

    try {
        const list = await env.LICENSES.list({ prefix: "license:" });
        const keys = list.keys;
        const licenses = [];

        // In a real production scenario with thousands of keys, this should be paginated or better managed.
        // For this scale, parallel fetching is fine.
        const promises = keys.map(key => env.LICENSES.get(key.name, "json"));
        const results = await Promise.all(promises);
        
        results.forEach(data => {
            if(data) licenses.push(data);
        });

        // Sort by created_at desc
        licenses.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

        return Response.json({ licenses }, { headers: corsHeaders() });
    } catch (e) {
        return Response.json({ error: e.message }, { status: 500, headers: corsHeaders() });
    }
}

async function handleDelete(request, env) {
    if (!checkAuth(request, env)) return new Response("Unauthorized", { status: 401, headers: corsHeaders() });

    try {
        const { device_id, type, key } = await request.json();
        let deleteKey = "";

        if (type === 'license') {
            if (!device_id) return Response.json({ error: "Missing device_id" }, { status: 400, headers: corsHeaders() });
            deleteKey = `license:${device_id}`;
            // Also clean up associated logs? No, keep logs for history or delete manually.
        } else if (type === 'log') {
            if (!key) return Response.json({ error: "Missing key" }, { status: 400, headers: corsHeaders() });
            deleteKey = key;
        } else {
            return Response.json({ error: "Invalid type" }, { status: 400, headers: corsHeaders() });
        }

        await env.LICENSES.delete(deleteKey);
        return Response.json({ success: true }, { headers: corsHeaders() });
    } catch (e) {
        return Response.json({ error: e.message }, { status: 500, headers: corsHeaders() });
    }
}

async function handleTamperLogs(request, env) {
    if (!checkAuth(request, env)) return new Response("Unauthorized", { status: 401, headers: corsHeaders() });

    try {
        const list = await env.LICENSES.list({ prefix: "tamper:" });
        const keys = list.keys;
        
        const promises = keys.map(async key => {
             const data = await env.LICENSES.get(key.name, "json");
             if(data) {
                 data.key = key.name;
                 return data;
             }
             return null;
        });
        
        const results = await Promise.all(promises);
        const tamperLogs = results.filter(r => r !== null);

        // Sort by timestamp descending
        tamperLogs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

        return Response.json({ tamper_logs: tamperLogs }, { headers: corsHeaders() });
    } catch (e) {
        return Response.json({ error: e.message }, { status: 500, headers: corsHeaders() });
    }
}

function checkAuth(request, env) {
    const authHeader = request.headers.get("Authorization");
    return authHeader === `Bearer ${env.ADMIN_TOKEN}`;
}

function corsHeaders() {
    return {
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/json",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    };
}

// =============================================================================
// Web UI Template (Modernized)
// =============================================================================

const ADMIN_HTML = `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCS-IoT License Manager</title>
    <link rel="stylesheet" href="https://unpkg.com/element-plus/dist/index.css" />
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
    <script src="https://unpkg.com/element-plus"></script>
    <script src="https://unpkg.com/@element-plus/icons-vue"></script>
    <style>
        :root { --el-color-primary: #409eff; --bg-color: #f0f2f5; }
        body { margin: 0; padding: 0; background: var(--bg-color); font-family: -apple-system, system-ui, sans-serif; }
        
        .app-container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        
        /* Login */
        .login-wrapper { height: 100vh; display: flex; align-items: center; justify-content: center; background: #2d3a4b; }
        .login-box { width: 400px; padding: 40px; background: white; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
        .login-title { text-align: center; font-size: 24px; font-weight: bold; margin-bottom: 30px; color: #333; }
        
        /* Dashboard */
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05); }
        .brand { display: flex; align-items: center; font-size: 20px; font-weight: 600; color: #1f2f3d; }
        .brand-icon { margin-right: 10px; font-size: 24px; color: var(--el-color-primary); }
        
        .main-card { border-radius: 8px; border: none; box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05); }
        .toolbar { display: flex; justify-content: space-between; margin-bottom: 20px; flex-wrap: wrap; gap: 10px; }
        .search-input { width: 300px; }
        
        .feature-tag { margin-right: 6px; }
        .status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 5px; }
        .status-active { background: #67c23a; }
        .status-expired { background: #f56c6c; }
        .status-disabled { background: #909399; }
        
        .code-box { background: #f4f4f5; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 12px; color: #909399; }
        
        /* Dialog */
        .dialog-footer { text-align: right; margin-top: 20px; }
    </style>
</head>
<body>
    <div id="app">
        <!-- Login Screen -->
        <div v-if="!token" class="login-wrapper">
            <div class="login-box">
                <div class="login-title">
                    <el-icon style="vertical-align: middle; margin-right: 8px;"><Key /></el-icon>
                    MCS License Admin
                </div>
                <el-form>
                    <el-form-item>
                        <el-input v-model="inputToken" placeholder="Enter Admin Token" prefix-icon="Lock" type="password" show-password @keyup.enter="login"></el-input>
                    </el-form-item>
                    <el-button type="primary" @click="login" style="width: 100%" :loading="loading" size="large">登 录</el-button>
                </el-form>
            </div>
        </div>

        <!-- Main Dashboard -->
        <div v-else class="app-container">
            <div class="header">
                <div class="brand">
                    <el-icon class="brand-icon"><Files /></el-icon>
                    设备授权管理系统
                </div>
                <div style="display: flex; align-items: center; gap: 15px;">
                    <el-tag type="info">Admin Mode</el-tag>
                    <el-button type="danger" plain size="small" icon="SwitchButton" @click="logout">退出</el-button>
                </div>
            </div>

            <el-card class="main-card">
                <el-tabs v-model="activeTab">
                    
                    <!-- LICENSE LIST TAB -->
                    <el-tab-pane label="授权列表" name="licenses">
                        <div class="toolbar">
                            <div style="display: flex; gap: 10px;">
                                <el-button type="primary" icon="Plus" @click="openAddDialog">新建授权</el-button>
                                <el-button icon="Refresh" @click="fetchList" circle></el-button>
                            </div>
                            <el-input v-model="searchQuery" placeholder="搜索 客户名称 / 设备ID" class="search-input" clearable prefix-icon="Search"></el-input>
                        </div>
                        
                        <el-table :data="filteredLicenses" v-loading="loadingData" stripe style="width: 100%">
                            <!-- Status Column -->
                            <el-table-column label="状态" width="100">
                                <template #default="{ row }">
                                    <div v-if="row.status === 'disabled'">
                                        <el-tag type="info" size="small" effect="dark">已禁用</el-tag>
                                    </div>
                                    <div v-else-if="isExpired(row.expires_at)">
                                        <el-tag type="danger" size="small" effect="dark">已过期</el-tag>
                                    </div>
                                    <div v-else>
                                        <el-tag type="success" size="small" effect="dark">正常</el-tag>
                                    </div>
                                </template>
                            </el-table-column>
                            
                            <!-- Customer Info -->
                            <el-table-column label="客户信息" min-width="180">
                                <template #default="{ row }">
                                    <div style="font-weight: bold;">{{ row.customer }}</div>
                                    <div style="font-size: 12px; color: #999;">创建于: {{ formatDate(row.created_at) }}</div>
                                </template>
                            </el-table-column>
                            
                            <!-- Device ID -->
                            <el-table-column label="设备 ID" width="240">
                                <template #default="{ row }">
                                    <el-tooltip content="点击复制" placement="top">
                                        <div class="code-box" style="cursor: pointer;" @click="copyToClipboard(row.device_id)">
                                            {{ row.device_id }}
                                        </div>
                                    </el-tooltip>
                                </template>
                            </el-table-column>
                            
                            <!-- Expiry -->
                            <el-table-column label="到期时间" width="150" prop="expires_at" sortable></el-table-column>
                            
                            <!-- Features -->
                            <el-table-column label="功能权限" min-width="200">
                                <template #default="{ row }">
                                    <el-tag v-for="tag in row.features" :key="tag" size="small" class="feature-tag" type="primary" effect="plain">{{ tag }}</el-tag>
                                </template>
                            </el-table-column>
                            
                            <!-- Actions -->
                            <el-table-column label="操作" width="180" fixed="right" align="right">
                                <template #default="{ row }">
                                    <el-button type="primary" text icon="Edit" @click="openEditDialog(row)">编辑</el-button>
                                    <el-button type="danger" text icon="Delete" @click="handleDeleteLicense(row)">删除</el-button>
                                </template>
                            </el-table-column>
                        </el-table>
                    </el-tab-pane>

                    <!-- SECURITY LOGS TAB -->
                    <el-tab-pane label="安全审计 (Tamper Logs)" name="logs">
                        <div class="toolbar">
                            <el-button icon="Refresh" @click="fetchLogs" circle></el-button>
                            <el-alert title="检测到任何哈希不匹配的请求将被记录在此" type="warning" show-icon :closable="false" style="width: auto; flex: 1;"></el-alert>
                        </div>
                        
                        <el-table :data="logs" v-loading="loadingLogs" style="width: 100%">
                            <el-table-column label="时间" width="180">
                                <template #default="{ row }">
                                    {{ new Date(row.timestamp).toLocaleString() }}
                                </template>
                            </el-table-column>
                            <el-table-column label="设备 / 客户" min-width="200">
                                <template #default="{ row }">
                                    <div>{{ row.device_id }}</div>
                                    <small style="color: #666">{{ row.customer || 'Unknown' }}</small>
                                </template>
                            </el-table-column>
                            <el-table-column label="哈希校验详情" min-width="300">
                                <template #default="{ row }">
                                    <div style="font-family: monospace; font-size: 12px;">
                                        <div style="color: #67c23a">EXPECT: {{ row.expected_hash }}</div>
                                        <div style="color: #f56c6c">ACTUAL: {{ row.actual_hash }}</div>
                                    </div>
                                </template>
                            </el-table-column>
                             <el-table-column label="操作" width="100" align="right">
                                <template #default="{ row }">
                                    <el-button type="danger" text icon="Delete" @click="handleDeleteLog(row)">删除</el-button>
                                </template>
                            </el-table-column>
                        </el-table>
                    </el-tab-pane>
                </el-tabs>
            </el-card>

            <!-- Dialog -->
            <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑授权' : '新建授权'" width="600px" destroy-on-close>
                <el-form :model="form" label-width="120px" :rules="rules" ref="formRef">
                    
                    <el-form-item label="设备 ID" prop="device_id">
                        <el-input v-model="form.device_id" placeholder="唯一设备标识符 (如 MAC 或 UUID)" :disabled="isEdit">
                             <template #append v-if="!isEdit">
                                <el-button icon="Refresh" @click="generateUUID" tooltip="生成UUID" />
                             </template>
                        </el-input>
                    </el-form-item>
                    
                    <el-form-item label="客户名称" prop="customer">
                        <el-input v-model="form.customer" placeholder="客户或项目名称"></el-input>
                    </el-form-item>
                    
                    <el-row>
                        <el-col :span="12">
                            <el-form-item label="过期日期" prop="expires_at">
                                <el-date-picker v-model="form.expires_at" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width: 100%"></el-date-picker>
                            </el-form-item>
                        </el-col>
                        <el-col :span="12">
                            <el-form-item label="当前状态" prop="status">
                                <el-select v-model="form.status" style="width: 100%">
                                    <el-option label="正常 (Active)" value="active"></el-option>
                                    <el-option label="禁用 (Disabled)" value="disabled"></el-option>
                                </el-select>
                            </el-form-item>
                        </el-col>
                    </el-row>

                    <el-form-item label="完整性哈希" prop="expected_hash">
                        <el-input v-model="form.expected_hash" placeholder="生产环境代码构建哈希 (SHA-256前16位)"></el-input>
                    </el-form-item>

                    <el-form-item label="功能模块">
                        <el-checkbox-group v-model="form.features">
                            <el-checkbox label="mqtt_external" border>MQTT 外网</el-checkbox>
                            <el-checkbox label="ai" border>AI 分析</el-checkbox>
                            <el-checkbox label="r2_archive" border>数据归档</el-checkbox>
                            <el-checkbox label="notifications" border>报警通知</el-checkbox>
                        </el-checkbox-group>
                    </el-form-item>
                </el-form>
                <div class="dialog-footer">
                     <el-button @click="dialogVisible = false">取消</el-button>
                     <el-button type="primary" @click="submitForm" :loading="submitting">保存提交</el-button>
                </div>
            </el-dialog>
        </div>
    </div>

    <script>
        const { createApp, ref, reactive, computed, onMounted } = Vue;

        const app = createApp({
            setup() {
                // State
                const token = ref(localStorage.getItem('admin_token') || '');
                const inputToken = ref('');
                const loading = ref(false);
                const activeTab = ref('licenses');
                const searchQuery = ref('');
                const licenses = ref([]);
                const logs = ref([]);
                const loadingData = ref(false);
                const loadingLogs = ref(false);

                // Dialog State
                const dialogVisible = ref(false);
                const isEdit = ref(false);
                const submitting = ref(false);
                const formRef = ref(null);
                
                const form = reactive({
                    device_id: '',
                    customer: '',
                    expires_at: '',
                    status: 'active',
                    expected_hash: '',
                    features: []
                });

                const rules = {
                    device_id: [{ required: true, message: '请输入设备ID', trigger: 'blur' }],
                    customer: [{ required: true, message: '请输入客户名称', trigger: 'blur' }],
                    expires_at: [{ required: true, message: '请选择过期时间', trigger: 'change' }]
                };

                // Icons
                // Registered globally via ElementPlusIconsVue

                // Computed
                const filteredLicenses = computed(() => {
                    const q = searchQuery.value.toLowerCase();
                    if (!q) return licenses.value;
                    return licenses.value.filter(item => 
                        item.device_id.toLowerCase().includes(q) || 
                        item.customer.toLowerCase().includes(q)
                    );
                });

                // Methods
                const login = () => {
                   if (!inputToken.value) return;
                   loading.value = true;
                   // Simple local check, real check is on API call
                   token.value = inputToken.value;
                   localStorage.setItem('admin_token', inputToken.value);
                   fetchList();
                   fetchLogs();
                   loading.value = false;
                };

                const logout = () => {
                    token.value = '';
                    localStorage.removeItem('admin_token');
                };

                const fetchList = async () => {
                    loadingData.value = true;
                    try {
                        const res = await apiCall('/admin/list');
                        licenses.value = res.licenses || [];
                    } catch (e) {
                         // Error handled in apiCall
                    } finally {
                        loadingData.value = false;
                    }
                };

                const fetchLogs = async () => {
                    loadingLogs.value = true;
                    try {
                        const res = await apiCall('/admin/tamper-logs');
                        logs.value = res.tamper_logs || [];
                    } catch (e) {
                    } finally {
                        loadingLogs.value = false;
                    }
                };

                const apiCall = async (endpoint, options = {}) => {
                    const headers = {
                        'Authorization': 'Bearer ' + token.value,
                        'Content-Type': 'application/json',
                        ...options.headers
                    };
                    
                    try {
                        const res = await fetch(endpoint, { ...options, headers });
                        if (res.status === 401) {
                            ElementPlus.ElMessage.error('Token 无效或已过期');
                            logout();
                            throw new Error('Unauthorized');
                        }
                        const data = await res.json();
                        if (data.error) {
                            ElementPlus.ElMessage.error(data.error);
                            throw new Error(data.error);
                        }
                        return data;
                    } catch (e) {
                         console.error(e);
                         throw e;
                    }
                };

                // CRUD
                const openAddDialog = () => {
                    isEdit.value = false;
                    Object.assign(form, {
                        device_id: '',
                        customer: '',
                        expires_at: new Date(new Date().setFullYear(new Date().getFullYear() + 1)).toISOString().split('T')[0], // Default 1 year
                        status: 'active',
                        expected_hash: '',
                        features: ['mqtt_external', 'ai', 'r2_archive', 'notifications']
                    });
                    dialogVisible.value = true;
                };

                const openEditDialog = (row) => {
                    isEdit.value = true;
                    Object.assign(form, JSON.parse(JSON.stringify(row))); // Deep copy
                    if(!form.status) form.status = 'active'; // Default for old records
                    dialogVisible.value = true;
                };
                
                const generateUUID = () => {
                    form.device_id = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                        var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
                        return v.toString(16);
                    });
                };

                const submitForm = async () => {
                    if (!formRef.value) return;
                    await formRef.value.validate(async (valid) => {
                        if (valid) {
                            submitting.value = true;
                            try {
                                await apiCall('/admin/add', {
                                    method: 'POST',
                                    body: JSON.stringify(form)
                                });
                                ElementPlus.ElMessage.success('保存成功');
                                dialogVisible.value = false;
                                fetchList();
                            } catch(e) {
                                // handled
                            } finally {
                                submitting.value = false;
                            }
                        }
                    });
                };

                const handleDeleteLicense = (row) => {
                    ElementPlus.ElMessageBox.confirm(
                        '确定要删除设备 ' + row.device_id + ' 的授权吗？该操作不可恢复。',
                        '危险操作',
                        { confirmButtonText: '删除', cancelButtonText: '取消', type: 'error' }
                    ).then(async () => {
                        await apiCall('/admin/delete', {
                            method: 'POST',
                            body: JSON.stringify({ device_id: row.device_id, type: 'license' })
                        });
                        ElementPlus.ElMessage.success('删除成功');
                        fetchList();
                    }).catch(() => {});
                };
                
                const handleDeleteLog = (row) => {
                     ElementPlus.ElMessageBox.confirm('确定要删除这条日志吗？', '提示', { type: 'warning' })
                     .then(async () => {
                        await apiCall('/admin/delete', {
                            method: 'POST',
                            body: JSON.stringify({ key: row.key, type: 'log' })
                        });
                        ElementPlus.ElMessage.success('已删除');
                        fetchLogs();
                     }).catch(() => {});
                }

                // Utils
                const isExpired = (dateStr) => new Date(dateStr) < new Date();
                const formatDate = (dateStr) => dateStr ? new Date(dateStr).toLocaleDateString() : '-';
                const copyToClipboard = (text) => {
                    navigator.clipboard.writeText(text).then(() => {
                        ElementPlus.ElMessage.success('已复制: ' + text);
                    });
                };

                // Init
                onMounted(() => {
                    if (token.value) {
                        fetchList();
                        fetchLogs();
                    }
                     // Register icons
                    for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
                        app.component(key, component)
                    }
                });

                return {
                    token, inputToken, login, logout, activeTab,
                    loading, loadingData, loadingLogs, submitting,
                    searchQuery, filteredLicenses, logs,
                    dialogVisible, isEdit, form, formRef, rules,
                    openAddDialog, openEditDialog, submitForm,
                    handleDeleteLicense, handleDeleteLog,
                    isExpired, formatDate, copyToClipboard, generateUUID
                };
            }
        });

        app.use(ElementPlus);
        app.mount('#app');
    </script>
</body>
</html>
`;
