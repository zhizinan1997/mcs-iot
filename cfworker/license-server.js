/**
 * MCS-IoT 授权管理服务器
 * 部署于 Cloudflare Workers
 * 
 * 功能：
 * - 设备授权验证
 * - 授权管理 (增删改查)
 * - 代码篡改检测与记录
 */

export default {
    async fetch(request, env) {
        // 处理 CORS 预检请求
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

        try {
            // 管理界面
            if (request.method === "GET" && url.pathname === "/admin") {
                return new Response(ADMIN_HTML, {
                    headers: { "Content-Type": "text/html; charset=utf-8" }
                });
            }

            // 授权验证 API
            if (request.method === "POST" && url.pathname === "/verify") {
                return await handleVerify(request, env);
            }

            // 管理 API: 添加/更新授权
            if (request.method === "POST" && url.pathname === "/admin/add") {
                return await handleAddLicense(request, env);
            }

            // 管理 API: 删除授权/日志
            if (request.method === "POST" && url.pathname === "/admin/delete") {
                return await handleDelete(request, env);
            }

            // 管理 API: 授权列表
            if (request.method === "GET" && url.pathname === "/admin/list") {
                return await handleListLicenses(request, env);
            }

            // 管理 API: 篡改日志
            if (request.method === "GET" && url.pathname === "/admin/tamper-logs") {
                return await handleTamperLogs(request, env);
            }

            return jsonResponse({ error: "接口不存在" }, 404);
        } catch (e) {
            console.error("全局错误:", e);
            return jsonResponse({ error: "服务器内部错误" }, 500);
        }
    },
};

// =============================================================================
// API 处理函数
// =============================================================================

async function handleVerify(request, env) {
    let body;
    try {
        body = await request.json();
    } catch (e) {
        return jsonResponse({ valid: false, error: "请求格式错误", tampered: false }, 400);
    }

    const { device_id, integrity_hash } = body;

    if (!device_id) {
        return jsonResponse({ valid: false, error: "缺少设备ID", tampered: false }, 400);
    }

    try {
        const licenseData = await env.LICENSES.get(`license:${device_id}`, "json");

        if (!licenseData) {
            return jsonResponse({ valid: false, error: "授权不存在", tampered: false });
        }

        // 检查状态
        if (licenseData.status === "disabled") {
            return jsonResponse({ valid: false, error: "授权已被禁用", tampered: false });
        }

        // 检查过期
        const expiryDate = new Date(licenseData.expires_at);
        if (isNaN(expiryDate.getTime()) || expiryDate < new Date()) {
            return jsonResponse({ valid: false, error: "授权已过期", tampered: false });
        }

        // 完整性校验
        let tampered = false;
        if (integrity_hash && licenseData.expected_hash) {
            if (integrity_hash !== licenseData.expected_hash) {
                tampered = true;
                
                // 记录篡改行为
                const tamperReport = {
                    device_id,
                    customer: licenseData.customer || "未知",
                    expected_hash: licenseData.expected_hash,
                    actual_hash: integrity_hash,
                    timestamp: new Date().toISOString()
                };
                
                const reportKey = `tamper:${device_id}:${Date.now()}`;
                await env.LICENSES.put(reportKey, JSON.stringify(tamperReport));
            }
        }

        return jsonResponse({
            valid: true,
            customer: licenseData.customer,
            expires_at: licenseData.expires_at,
            features: licenseData.features || ["mqtt_external", "ai", "r2_archive", "notifications"],
            tampered: tampered
        });
    } catch (e) {
        console.error("验证授权失败:", e);
        return jsonResponse({ valid: false, error: "验证服务异常", tampered: false }, 500);
    }
}

async function handleAddLicense(request, env) {
    if (!checkAuth(request, env)) {
        return jsonResponse({ error: "未授权访问" }, 401);
    }

    let payload;
    try {
        payload = await request.json();
    } catch (e) {
        return jsonResponse({ error: "请求格式错误" }, 400);
    }

    const { device_id, customer, expires_at, features, expected_hash, status } = payload;

    if (!device_id) {
        return jsonResponse({ error: "缺少设备ID" }, 400);
    }

    if (!customer) {
        return jsonResponse({ error: "缺少客户名称" }, 400);
    }

    if (!expires_at) {
        return jsonResponse({ error: "缺少过期时间" }, 400);
    }

    try {
        // 检查是否已存在，保留创建时间
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

        return jsonResponse({ success: true, message: "保存成功", data: licenseData });
    } catch (e) {
        console.error("保存授权失败:", e);
        return jsonResponse({ error: "保存失败: " + e.message }, 500);
    }
}

async function handleListLicenses(request, env) {
    if (!checkAuth(request, env)) {
        return jsonResponse({ error: "未授权访问" }, 401);
    }

    try {
        const list = await env.LICENSES.list({ prefix: "license:" });
        const keys = list.keys;
        const licenses = [];

        // 并行获取所有授权数据
        const promises = keys.map(key => env.LICENSES.get(key.name, "json"));
        const results = await Promise.all(promises);
        
        results.forEach(data => {
            if (data) licenses.push(data);
        });

        // 按创建时间倒序排列
        licenses.sort((a, b) => {
            const dateA = new Date(a.created_at || 0);
            const dateB = new Date(b.created_at || 0);
            return dateB - dateA;
        });

        return jsonResponse({ licenses });
    } catch (e) {
        console.error("获取授权列表失败:", e);
        return jsonResponse({ error: "获取列表失败: " + e.message }, 500);
    }
}

async function handleDelete(request, env) {
    if (!checkAuth(request, env)) {
        return jsonResponse({ error: "未授权访问" }, 401);
    }

    let body;
    try {
        body = await request.json();
    } catch (e) {
        return jsonResponse({ error: "请求格式错误" }, 400);
    }

    const { device_id, type, key } = body;
    let deleteKey = "";

    if (type === 'license') {
        if (!device_id) {
            return jsonResponse({ error: "缺少设备ID" }, 400);
        }
        deleteKey = `license:${device_id}`;
    } else if (type === 'log') {
        if (!key) {
            return jsonResponse({ error: "缺少日志键值" }, 400);
        }
        deleteKey = key;
    } else {
        return jsonResponse({ error: "无效的删除类型" }, 400);
    }

    try {
        await env.LICENSES.delete(deleteKey);
        return jsonResponse({ success: true, message: "删除成功" });
    } catch (e) {
        console.error("删除失败:", e);
        return jsonResponse({ error: "删除失败: " + e.message }, 500);
    }
}

async function handleTamperLogs(request, env) {
    if (!checkAuth(request, env)) {
        return jsonResponse({ error: "未授权访问" }, 401);
    }

    try {
        const list = await env.LICENSES.list({ prefix: "tamper:" });
        const keys = list.keys;
        
        const promises = keys.map(async key => {
            const data = await env.LICENSES.get(key.name, "json");
            if (data) {
                data.key = key.name;
                return data;
            }
            return null;
        });
        
        const results = await Promise.all(promises);
        const tamperLogs = results.filter(r => r !== null);

        // 按时间倒序排列
        tamperLogs.sort((a, b) => {
            const dateA = new Date(a.timestamp || 0);
            const dateB = new Date(b.timestamp || 0);
            return dateB - dateA;
        });

        return jsonResponse({ tamper_logs: tamperLogs });
    } catch (e) {
        console.error("获取篡改日志失败:", e);
        return jsonResponse({ error: "获取日志失败: " + e.message }, 500);
    }
}

// =============================================================================
// 工具函数
// =============================================================================

function checkAuth(request, env) {
    const authHeader = request.headers.get("Authorization");
    if (!authHeader || !env.ADMIN_TOKEN) {
        return false;
    }
    return authHeader === `Bearer ${env.ADMIN_TOKEN}`;
}

function jsonResponse(data, status = 200) {
    return new Response(JSON.stringify(data), {
        status,
        headers: {
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "application/json; charset=utf-8",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }
    });
}

// =============================================================================
// 管理界面 HTML
// =============================================================================

const ADMIN_HTML = `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCS-IoT 授权管理系统</title>
    <link rel="stylesheet" href="https://unpkg.com/element-plus/dist/index.css" />
    <script src="https://unpkg.com/vue@3/dist/vue.global.prod.js"></script>
    <script src="https://unpkg.com/element-plus"></script>
    <script src="https://unpkg.com/@element-plus/icons-vue"></script>
    <style>
        :root { 
            --el-color-primary: #409eff; 
            --bg-color: #f0f2f5; 
        }
        * { box-sizing: border-box; }
        body { 
            margin: 0; 
            padding: 0; 
            background: var(--bg-color); 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; 
        }
        
        .app-container { 
            max-width: 1200px; 
            margin: 0 auto; 
            padding: 20px; 
        }
        
        /* 登录页面 */
        .login-wrapper { 
            height: 100vh; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        }
        .login-box { 
            width: 400px; 
            padding: 40px; 
            background: white; 
            border-radius: 12px; 
            box-shadow: 0 20px 60px rgba(0,0,0,0.3); 
        }
        .login-title { 
            text-align: center; 
            font-size: 22px; 
            font-weight: 600; 
            margin-bottom: 30px; 
            color: #1f2f3d; 
        }
        .login-title .el-icon { 
            font-size: 28px; 
            color: var(--el-color-primary); 
            vertical-align: middle;
            margin-right: 10px;
        }
        
        /* 仪表盘 */
        .header { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            margin-bottom: 25px; 
            background: white; 
            padding: 20px; 
            border-radius: 8px; 
            box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05); 
        }
        .brand { 
            display: flex; 
            align-items: center; 
            font-size: 20px; 
            font-weight: 600; 
            color: #1f2f3d; 
        }
        .brand-icon { 
            margin-right: 10px; 
            font-size: 26px; 
            color: var(--el-color-primary); 
        }
        
        .main-card { 
            border-radius: 8px; 
            border: none; 
            box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05); 
        }
        .toolbar { 
            display: flex; 
            justify-content: space-between; 
            margin-bottom: 20px; 
            flex-wrap: wrap; 
            gap: 10px; 
        }
        .search-input { 
            width: 300px; 
        }
        
        .feature-tag { 
            margin-right: 6px; 
            margin-bottom: 4px;
        }
        
        .code-box { 
            background: #f4f4f5; 
            padding: 4px 8px; 
            border-radius: 4px; 
            font-family: "SF Mono", Monaco, Consolas, monospace; 
            font-size: 12px; 
            color: #606266;
            user-select: all;
        }
        .code-box:hover {
            background: #e6e8eb;
        }
        
        /* 对话框 */
        .dialog-footer { 
            text-align: right; 
            margin-top: 20px; 
            padding-top: 20px;
            border-top: 1px solid #ebeef5;
        }

        /* 表格优化 */
        .el-table { font-size: 14px; }
        .el-table .cell { padding: 8px 12px; }
        
        /* 响应式 */
        @media (max-width: 768px) {
            .search-input { width: 100%; }
            .login-box { width: 90%; margin: 20px; }
        }
    </style>
</head>
<body>
    <div id="app">
        <!-- 登录页面 -->
        <div v-if="!token" class="login-wrapper">
            <div class="login-box">
                <div class="login-title">
                    <el-icon><Key /></el-icon>
                    MCS-IoT 授权管理
                </div>
                <el-form @submit.prevent="login">
                    <el-form-item>
                        <el-input 
                            v-model="inputToken" 
                            placeholder="请输入管理员密钥" 
                            prefix-icon="Lock" 
                            type="password" 
                            show-password 
                            size="large"
                            @keyup.enter="login"
                        ></el-input>
                    </el-form-item>
                    <el-button type="primary" @click="login" style="width: 100%" :loading="loading" size="large">
                        登 录
                    </el-button>
                </el-form>
            </div>
        </div>

        <!-- 主界面 -->
        <div v-else class="app-container">
            <div class="header">
                <div class="brand">
                    <el-icon class="brand-icon"><Files /></el-icon>
                    设备授权管理系统
                </div>
                <div style="display: flex; align-items: center; gap: 15px;">
                    <el-tag type="success">管理模式</el-tag>
                    <el-button type="danger" plain size="small" icon="SwitchButton" @click="logout">
                        退出登录
                    </el-button>
                </div>
            </div>

            <el-card class="main-card">
                <el-tabs v-model="activeTab">
                    
                    <!-- 授权列表标签页 -->
                    <el-tab-pane label="授权列表" name="licenses">
                        <div class="toolbar">
                            <div style="display: flex; gap: 10px;">
                                <el-button type="primary" icon="Plus" @click="openAddDialog">新建授权</el-button>
                                <el-button icon="Refresh" @click="fetchList" circle title="刷新列表"></el-button>
                            </div>
                            <el-input 
                                v-model="searchQuery" 
                                placeholder="搜索客户名称或设备ID" 
                                class="search-input" 
                                clearable 
                                prefix-icon="Search"
                            ></el-input>
                        </div>
                        
                        <el-table :data="filteredLicenses" v-loading="loadingData" stripe style="width: 100%">
                            <!-- 状态列 -->
                            <el-table-column label="状态" width="100" align="center">
                                <template #default="{ row }">
                                    <el-tag v-if="row.status === 'disabled'" type="info" size="small" effect="dark">已禁用</el-tag>
                                    <el-tag v-else-if="isExpired(row.expires_at)" type="danger" size="small" effect="dark">已过期</el-tag>
                                    <el-tag v-else type="success" size="small" effect="dark">正常</el-tag>
                                </template>
                            </el-table-column>
                            
                            <!-- 客户信息 -->
                            <el-table-column label="客户信息" min-width="180">
                                <template #default="{ row }">
                                    <div style="font-weight: 600; color: #303133;">{{ row.customer }}</div>
                                    <div style="font-size: 12px; color: #909399; margin-top: 4px;">
                                        创建于: {{ formatDate(row.created_at) }}
                                    </div>
                                </template>
                            </el-table-column>
                            
                            <!-- 设备 ID -->
                            <el-table-column label="设备ID" width="220">
                                <template #default="{ row }">
                                    <el-tooltip content="点击复制" placement="top">
                                        <div class="code-box" style="cursor: pointer;" @click="copyToClipboard(row.device_id)">
                                            {{ row.device_id }}
                                        </div>
                                    </el-tooltip>
                                </template>
                            </el-table-column>
                            
                            <!-- 到期时间 -->
                            <el-table-column label="到期时间" width="130" prop="expires_at" sortable>
                                <template #default="{ row }">
                                    <span :style="{ color: isExpired(row.expires_at) ? '#f56c6c' : '#606266' }">
                                        {{ row.expires_at }}
                                    </span>
                                </template>
                            </el-table-column>
                            
                            <!-- 功能权限 -->
                            <el-table-column label="功能权限" min-width="200">
                                <template #default="{ row }">
                                    <el-tag 
                                        v-for="tag in (row.features || [])" 
                                        :key="tag" 
                                        size="small" 
                                        class="feature-tag" 
                                        type="primary" 
                                        effect="plain"
                                    >{{ getFeatureLabel(tag) }}</el-tag>
                                </template>
                            </el-table-column>
                            
                            <!-- 操作 -->
                            <el-table-column label="操作" width="160" fixed="right" align="center">
                                <template #default="{ row }">
                                    <el-button type="primary" text icon="Edit" size="small" @click="openEditDialog(row)">编辑</el-button>
                                    <el-button type="danger" text icon="Delete" size="small" @click="handleDeleteLicense(row)">删除</el-button>
                                </template>
                            </el-table-column>
                        </el-table>
                        
                        <div v-if="filteredLicenses.length === 0 && !loadingData" style="text-align: center; padding: 40px; color: #909399;">
                            <el-icon style="font-size: 48px; margin-bottom: 16px;"><DocumentRemove /></el-icon>
                            <p>暂无授权记录</p>
                        </div>
                    </el-tab-pane>

                    <!-- 安全审计标签页 -->
                    <el-tab-pane label="安全审计" name="logs">
                        <div class="toolbar">
                            <el-button icon="Refresh" @click="fetchLogs" circle title="刷新日志"></el-button>
                            <el-alert 
                                title="检测到代码哈希不匹配的请求会被自动记录在此，用于追踪非授权修改" 
                                type="warning" 
                                show-icon 
                                :closable="false" 
                                style="flex: 1;"
                            ></el-alert>
                        </div>
                        
                        <el-table :data="logs" v-loading="loadingLogs" style="width: 100%">
                            <el-table-column label="记录时间" width="180">
                                <template #default="{ row }">
                                    {{ formatDateTime(row.timestamp) }}
                                </template>
                            </el-table-column>
                            <el-table-column label="设备/客户" min-width="200">
                                <template #default="{ row }">
                                    <div class="code-box" style="display: inline-block;">{{ row.device_id }}</div>
                                    <div style="color: #909399; font-size: 12px; margin-top: 4px;">
                                        {{ row.customer || '未知客户' }}
                                    </div>
                                </template>
                            </el-table-column>
                            <el-table-column label="哈希校验详情" min-width="320">
                                <template #default="{ row }">
                                    <div style="font-family: monospace; font-size: 12px;">
                                        <div style="color: #67c23a">
                                            <el-icon><Check /></el-icon> 预期: {{ row.expected_hash }}
                                        </div>
                                        <div style="color: #f56c6c; margin-top: 4px;">
                                            <el-icon><Close /></el-icon> 实际: {{ row.actual_hash }}
                                        </div>
                                    </div>
                                </template>
                            </el-table-column>
                            <el-table-column label="操作" width="100" align="center">
                                <template #default="{ row }">
                                    <el-button type="danger" text icon="Delete" size="small" @click="handleDeleteLog(row)">删除</el-button>
                                </template>
                            </el-table-column>
                        </el-table>
                        
                        <div v-if="logs.length === 0 && !loadingLogs" style="text-align: center; padding: 40px; color: #67c23a;">
                            <el-icon style="font-size: 48px; margin-bottom: 16px;"><CircleCheck /></el-icon>
                            <p>暂无异常记录，系统运行正常</p>
                        </div>
                    </el-tab-pane>
                </el-tabs>
            </el-card>

            <!-- 编辑对话框 -->
            <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑授权' : '新建授权'" width="600px" destroy-on-close>
                <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
                    
                    <el-form-item label="设备ID" prop="device_id">
                        <el-input v-model="form.device_id" placeholder="唯一设备标识符" :disabled="isEdit">
                            <template #append v-if="!isEdit">
                                <el-button icon="Refresh" @click="generateUUID" title="生成UUID"></el-button>
                            </template>
                        </el-input>
                        <div style="font-size: 12px; color: #909399; margin-top: 4px;" v-if="!isEdit">
                            设备ID一旦创建不可修改，请确保输入正确
                        </div>
                    </el-form-item>
                    
                    <el-form-item label="客户名称" prop="customer">
                        <el-input v-model="form.customer" placeholder="客户或项目名称"></el-input>
                    </el-form-item>
                    
                    <el-row :gutter="20">
                        <el-col :span="12">
                            <el-form-item label="过期日期" prop="expires_at">
                                <el-date-picker 
                                    v-model="form.expires_at" 
                                    type="date" 
                                    placeholder="选择日期" 
                                    value-format="YYYY-MM-DD" 
                                    style="width: 100%"
                                    :disabled-date="disablePastDate"
                                ></el-date-picker>
                            </el-form-item>
                        </el-col>
                        <el-col :span="12">
                            <el-form-item label="当前状态" prop="status">
                                <el-select v-model="form.status" style="width: 100%">
                                    <el-option label="正常" value="active"></el-option>
                                    <el-option label="禁用" value="disabled"></el-option>
                                </el-select>
                            </el-form-item>
                        </el-col>
                    </el-row>

                    <el-form-item label="完整性哈希">
                        <el-input v-model="form.expected_hash" placeholder="可选，用于代码完整性校验"></el-input>
                        <div style="font-size: 12px; color: #909399; margin-top: 4px;">
                            填写后将校验客户端代码是否被篡改（SHA-256前16位）
                        </div>
                    </el-form-item>

                    <el-form-item label="功能模块">
                        <el-checkbox-group v-model="form.features">
                            <el-checkbox label="mqtt_external" border>MQTT外网</el-checkbox>
                            <el-checkbox label="ai" border>AI分析</el-checkbox>
                            <el-checkbox label="r2_archive" border>数据归档</el-checkbox>
                            <el-checkbox label="notifications" border>报警通知</el-checkbox>
                        </el-checkbox-group>
                    </el-form-item>
                </el-form>
                <div class="dialog-footer">
                    <el-button @click="dialogVisible = false">取消</el-button>
                    <el-button type="primary" @click="submitForm" :loading="submitting">保存</el-button>
                </div>
            </el-dialog>
        </div>
    </div>

    <script>
        const { createApp, ref, reactive, computed, onMounted, nextTick } = Vue;

        const app = createApp({
            setup() {
                // ========== 状态 ==========
                const token = ref(localStorage.getItem('admin_token') || '');
                const inputToken = ref('');
                const loading = ref(false);
                const activeTab = ref('licenses');
                const searchQuery = ref('');
                const licenses = ref([]);
                const logs = ref([]);
                const loadingData = ref(false);
                const loadingLogs = ref(false);

                // 对话框状态
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

                // 功能标签映射
                const featureLabels = {
                    'mqtt_external': 'MQTT外网',
                    'ai': 'AI分析',
                    'r2_archive': '数据归档',
                    'notifications': '报警通知'
                };

                // ========== 计算属性 ==========
                const filteredLicenses = computed(() => {
                    const q = searchQuery.value.toLowerCase().trim();
                    if (!q) return licenses.value;
                    return licenses.value.filter(item => 
                        (item.device_id || '').toLowerCase().includes(q) || 
                        (item.customer || '').toLowerCase().includes(q)
                    );
                });

                // ========== 方法 ==========
                const login = async () => {
                    if (!inputToken.value.trim()) {
                        ElementPlus.ElMessage.warning('请输入管理员密钥');
                        return;
                    }
                    loading.value = true;
                    token.value = inputToken.value.trim();
                    localStorage.setItem('admin_token', token.value);
                    
                    try {
                        await fetchList();
                        await fetchLogs();
                    } catch (e) {
                        // 登录失败会在 apiCall 中处理
                    }
                    loading.value = false;
                };

                const logout = () => {
                    ElementPlus.ElMessageBox.confirm('确定要退出登录吗？', '提示', {
                        confirmButtonText: '确定',
                        cancelButtonText: '取消',
                        type: 'warning'
                    }).then(() => {
                        token.value = '';
                        localStorage.removeItem('admin_token');
                        inputToken.value = '';
                    }).catch(() => {});
                };

                const fetchList = async () => {
                    loadingData.value = true;
                    try {
                        const res = await apiCall('/admin/list');
                        licenses.value = res.licenses || [];
                    } catch (e) {
                        // 错误已在 apiCall 中处理
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
                        // 错误已在 apiCall 中处理
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
                    
                    const res = await fetch(endpoint, { ...options, headers });
                    
                    if (res.status === 401) {
                        ElementPlus.ElMessage.error('密钥无效或已过期，请重新登录');
                        token.value = '';
                        localStorage.removeItem('admin_token');
                        throw new Error('未授权');
                    }
                    
                    const data = await res.json();
                    
                    if (data.error) {
                        ElementPlus.ElMessage.error(data.error);
                        throw new Error(data.error);
                    }
                    
                    return data;
                };

                // ========== CRUD 操作 ==========
                const openAddDialog = () => {
                    isEdit.value = false;
                    const nextYear = new Date();
                    nextYear.setFullYear(nextYear.getFullYear() + 1);
                    
                    Object.assign(form, {
                        device_id: '',
                        customer: '',
                        expires_at: nextYear.toISOString().split('T')[0],
                        status: 'active',
                        expected_hash: '',
                        features: ['mqtt_external', 'ai', 'r2_archive', 'notifications']
                    });
                    dialogVisible.value = true;
                };

                const openEditDialog = (row) => {
                    isEdit.value = true;
                    Object.assign(form, {
                        device_id: row.device_id || '',
                        customer: row.customer || '',
                        expires_at: row.expires_at || '',
                        status: row.status || 'active',
                        expected_hash: row.expected_hash || '',
                        features: row.features || []
                    });
                    dialogVisible.value = true;
                };
                
                const generateUUID = () => {
                    form.device_id = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                        const r = Math.random() * 16 | 0;
                        const v = c === 'x' ? r : (r & 0x3 | 0x8);
                        return v.toString(16);
                    }).toUpperCase();
                };

                const submitForm = async () => {
                    if (!formRef.value) return;
                    
                    try {
                        await formRef.value.validate();
                    } catch (e) {
                        return;
                    }
                    
                    submitting.value = true;
                    try {
                        await apiCall('/admin/add', {
                            method: 'POST',
                            body: JSON.stringify(form)
                        });
                        ElementPlus.ElMessage.success(isEdit.value ? '修改成功' : '添加成功');
                        dialogVisible.value = false;
                        fetchList();
                    } catch(e) {
                        // 错误已在 apiCall 中处理
                    } finally {
                        submitting.value = false;
                    }
                };

                const handleDeleteLicense = (row) => {
                    ElementPlus.ElMessageBox.confirm(
                        '确定要删除设备 "' + row.device_id + '" 的授权吗？此操作不可恢复！',
                        '删除确认',
                        { 
                            confirmButtonText: '确定删除', 
                            cancelButtonText: '取消', 
                            type: 'error',
                            confirmButtonClass: 'el-button--danger'
                        }
                    ).then(async () => {
                        try {
                            await apiCall('/admin/delete', {
                                method: 'POST',
                                body: JSON.stringify({ device_id: row.device_id, type: 'license' })
                            });
                            ElementPlus.ElMessage.success('删除成功');
                            fetchList();
                        } catch (e) {
                            // 错误已在 apiCall 中处理
                        }
                    }).catch(() => {});
                };
                
                const handleDeleteLog = (row) => {
                    ElementPlus.ElMessageBox.confirm('确定要删除这条日志记录吗？', '提示', { type: 'warning' })
                    .then(async () => {
                        try {
                            await apiCall('/admin/delete', {
                                method: 'POST',
                                body: JSON.stringify({ key: row.key, type: 'log' })
                            });
                            ElementPlus.ElMessage.success('删除成功');
                            fetchLogs();
                        } catch (e) {
                            // 错误已在 apiCall 中处理
                        }
                    }).catch(() => {});
                };

                // ========== 工具函数 ==========
                const isExpired = (dateStr) => {
                    if (!dateStr) return true;
                    return new Date(dateStr) < new Date();
                };
                
                const formatDate = (dateStr) => {
                    if (!dateStr) return '-';
                    try {
                        return new Date(dateStr).toLocaleDateString('zh-CN');
                    } catch (e) {
                        return dateStr;
                    }
                };
                
                const formatDateTime = (dateStr) => {
                    if (!dateStr) return '-';
                    try {
                        return new Date(dateStr).toLocaleString('zh-CN');
                    } catch (e) {
                        return dateStr;
                    }
                };
                
                const copyToClipboard = (text) => {
                    if (navigator.clipboard) {
                        navigator.clipboard.writeText(text).then(() => {
                            ElementPlus.ElMessage.success('已复制: ' + text);
                        }).catch(() => {
                            fallbackCopy(text);
                        });
                    } else {
                        fallbackCopy(text);
                    }
                };
                
                const fallbackCopy = (text) => {
                    const textarea = document.createElement('textarea');
                    textarea.value = text;
                    document.body.appendChild(textarea);
                    textarea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textarea);
                    ElementPlus.ElMessage.success('已复制: ' + text);
                };
                
                const getFeatureLabel = (key) => {
                    return featureLabels[key] || key;
                };
                
                const disablePastDate = (date) => {
                    const today = new Date();
                    today.setHours(0, 0, 0, 0);
                    return date < today;
                };

                // ========== 初始化 ==========
                onMounted(() => {
                    if (token.value) {
                        fetchList();
                        fetchLogs();
                    }
                });

                return {
                    token, inputToken, login, logout, activeTab,
                    loading, loadingData, loadingLogs, submitting,
                    searchQuery, filteredLicenses, logs,
                    dialogVisible, isEdit, form, formRef, rules,
                    openAddDialog, openEditDialog, submitForm,
                    handleDeleteLicense, handleDeleteLog,
                    isExpired, formatDate, formatDateTime, copyToClipboard, 
                    generateUUID, getFeatureLabel, disablePastDate, fetchList, fetchLogs
                };
            }
        });

        // 注册 Element Plus 图标
        for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
            app.component(key, component);
        }
        
        app.use(ElementPlus);
        app.mount('#app');
    </script>
</body>
</html>
`;
