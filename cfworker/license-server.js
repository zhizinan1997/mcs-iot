/**
 * MCS-IoT License Server
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

        // Admin API: Add License
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
                { valid: false, error: "未找到授权信息", tampered: false },
                { headers: corsHeaders() }
            );
        }

        if (new Date(licenseData.expires_at) < new Date()) {
            return Response.json(
                { valid: false, error: "授权已过期", tampered: false },
                { headers: corsHeaders() }
            );
        }

        if (licenseData.status !== "active") {
            return Response.json(
                { valid: false, error: "授权已被禁用", tampered: false },
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
                
                console.log(`TAMPERING DETECTED: ${device_id}`);
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
        const { device_id, customer, expires_at, features, expected_hash } = await request.json();

        const licenseData = {
            device_id,
            status: "active",
            customer,
            expires_at,
            features: features || ["mqtt_external", "ai", "r2_archive", "notifications"],
            expected_hash: expected_hash || "",
            created_at: new Date().toISOString()
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

        // Fetch details (limit 10 for demo, or fetch all parallel)
        for (const key of keys) {
            const data = await env.LICENSES.get(key.name, "json");
            licenses.push(data);
        }

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
        const tamperLogs = [];

        for (const key of keys) {
            const data = await env.LICENSES.get(key.name, "json");
            if (data) {
                data.key = key.name; // Include the key for deletion
                tamperLogs.push(data);
            }
        }

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
    };
}

// =============================================================================
// Web UI Template
// =============================================================================

const ADMIN_HTML = `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCS-IoT License Admin</title>
    <link rel="stylesheet" href="https://unpkg.com/element-plus/dist/index.css" />
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
    <script src="https://unpkg.com/element-plus"></script>
    <script src="https://unpkg.com/@element-plus/icons-vue"></script>
    <style>
        body { margin: 0; padding: 0; background: #f5f7fa; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
        .login-container { display: flex; justify-content: center; align-items: center; height: 100vh; }
        .login-card { width: 400px; }
        .main-container { padding: 20px; max-width: 1200px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; background: white; padding: 15px 20px; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }
        .feature-tag { margin-right: 5px; margin-bottom: 5px; }
        .hash-text { font-family: monospace; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div id="app">
        <!-- Loading -->
        <div v-if="loading" style="text-align:center; padding-top: 50px;">
             Loading...
        </div>

        <!-- Login -->
        <div v-else-if="!token" class="login-container">
            <el-card class="login-card">
                <template #header><h3>MCS-IoT 授权管理后台</h3></template>
                <el-form>
                    <el-form-item label="Token">
                        <el-input v-model="inputToken" placeholder="输入 Admin Token" type="password" show-password></el-input>
                    </el-form-item>
                    <el-button type="primary" @click="login" style="width: 100%">登录</el-button>
                </el-form>
            </el-card>
        </div>

        <!-- Dashboard -->
        <div v-else class="main-container">
            <div class="header">
                <h2>授权管理</h2>
                <div>
                    <el-button type="info" @click="logout">退出</el-button>
                </div>
            </div>

            <el-tabs type="border-card">
                <el-tab-pane label="授权列表">
                    <div style="margin-bottom: 15px;">
                        <el-button type="primary" @click="showAddDialog = true">添加授权</el-button>
                        <el-button @click="fetchList">刷新</el-button>
                    </div>
                    <el-table :data="licenses" stripe style="width: 100%" v-loading="loadingData">
                        <el-table-column prop="customer" label="客户名称" width="180"></el-table-column>
                        <el-table-column prop="device_id" label="设备 ID" width="220">
                             <template #default="scope">
                                <el-tag type="info">{{ scope.row.device_id }}</el-tag>
                            </template>
                        </el-table-column>
                        <el-table-column prop="expires_at" label="过期时间" width="120"></el-table-column>
                        <el-table-column prop="status" label="状态" width="100">
                            <template #default="scope">
                                <el-tag :type="getStatusType(scope.row)">{{ scope.row.status }}</el-tag>
                            </template>
                        </el-table-column>
                        <el-table-column label="完整性校验" width="150">
                            <template #default="scope">
                                <el-tooltip :content="scope.row.expected_hash" placement="top" v-if="scope.row.expected_hash">
                                    <span class="hash-text">{{ scope.row.expected_hash.substring(0, 8) }}...</span>
                                </el-tooltip>
                                <span v-else class="hash-text" style="color: #ccc">未设置</span>
                            </template>
                        </el-table-column>
                        <el-table-column label="功能权限">
                            <template #default="scope">
                                <el-tag v-for="f in scope.row.features" :key="f" size="small" class="feature-tag">{{ f }}</el-tag>
                            </template>
                        </el-table-column>
                        <el-table-column label="操作" width="150" align="right">
                             <template #default="scope">
                                <el-button type="primary" link @click="edit(scope.row)">编辑</el-button>
                                <el-button type="danger" link @click="confirmDelete(scope.row.device_id, 'license')">删除</el-button>
                             </template>
                        </el-table-column>
                    </el-table>
                </el-tab-pane>
                
                <el-tab-pane label="破解记录(Tamper Logs)">
                    <div style="margin-bottom: 15px;">
                        <el-button @click="fetchTamperLogs">刷新</el-button>
                    </div>
                    <el-table :data="tamperLogs" stripe style="width: 100%" v-loading="loadingLogs">
                        <el-table-column prop="timestamp" label="时间" width="180">
                            <template #default="scope">
                                {{ new Date(scope.row.timestamp).toLocaleString() }}
                            </template>
                        </el-table-column>
                         <el-table-column prop="device_id" label="设备 ID" width="220">
                             <template #default="scope">
                                <el-tag type="danger">{{ scope.row.device_id }}</el-tag>
                            </template>
                        </el-table-column>
                        <el-table-column prop="customer" label="可能客户" width="150"></el-table-column>
                        <el-table-column label="哈希对比">
                            <template #default="scope">
                                <div>期望: <span class="hash-text">{{ scope.row.expected_hash }}</span></div>
                                <div>实际: <span class="hash-text" style="color: red">{{ scope.row.actual_hash }}</span></div>
                            </template>
                        </el-table-column>
                        <el-table-column label="操作" width="100" align="right">
                             <template #default="scope">
                                <el-button type="danger" link @click="confirmDelete(scope.row.key, 'log')">删除</el-button>
                             </template>
                        </el-table-column>
                    </el-table>
                </el-tab-pane>
            </el-tabs>

            <!-- Add Dialog -->
            <el-dialog v-model="showAddDialog" title="添加/编辑授权" width="600px">
                <el-form :model="form" label-width="120px">
                    <el-form-item label="设备 ID">
                        <el-input v-model="form.device_id" placeholder="MCS-XXXX-XXXX-XXXX"></el-input>
                    </el-form-item>
                    <el-form-item label="客户名称">
                        <el-input v-model="form.customer" placeholder="客户公司名称"></el-input>
                    </el-form-item>
                    <el-form-item label="过期时间">
                         <el-date-picker v-model="form.expires_at" type="date" placeholder="选择日期" format="YYYY-MM-DD" value-format="YYYY-MM-DD" style="width: 100%"></el-date-picker>
                    </el-form-item>
                    <el-form-item label="Expected Hash">
                        <el-input v-model="form.expected_hash" placeholder="代码完整性哈希 (例如: 43b8117fff32ab77)"></el-input>
                        <div style="font-size: 12px; color: #999;">生产环境代码的 SHA-256 哈希值 (前16位)</div>
                    </el-form-item>
                    <el-form-item label="功能权限">
                        <el-checkbox-group v-model="form.features">
                            <el-checkbox label="mqtt_external">MQTT 外网</el-checkbox>
                            <el-checkbox label="ai">AI 分析</el-checkbox>
                            <el-checkbox label="r2_archive">R2 归档</el-checkbox>
                            <el-checkbox label="notifications">报警通知</el-checkbox>
                        </el-checkbox-group>
                    </el-form-item>
                </el-form>
                <template #footer>
                    <el-button @click="showAddDialog = false">取消</el-button>
                    <el-button type="primary" @click="submit" :loading="submitting">保存</el-button>
                </template>
            </el-dialog>
        </div>
    </div>

    <script>
        const { createApp, ref, reactive, onMounted } = Vue;

        const app = createApp({
            setup() {
                const loading = ref(true);
                const token = ref(localStorage.getItem('admin_token') || '');
                const inputToken = ref('');
                const licenses = ref([]);
                const tamperLogs = ref([]);
                const loadingData = ref(false);
                const loadingLogs = ref(false);
                const showAddDialog = ref(false);
                const submitting = ref(false);
                
                const form = reactive({
                    device_id: '',
                    customer: '',
                    expires_at: '',
                    expected_hash: '',
                    features: ['mqtt_external', 'ai', 'r2_archive', 'notifications']
                });

                const login = () => {
                    if(inputToken.value) {
                        token.value = inputToken.value;
                        localStorage.setItem('admin_token', inputToken.value);
                        fetchList();
                        fetchTamperLogs();
                    }
                };
                
                const logout = () => {
                    token.value = '';
                    localStorage.removeItem('admin_token');
                };

                const fetchList = async () => {
                    loadingData.value = true;
                    try {
                        const res = await fetch('/admin/list', {
                            headers: { 'Authorization': 'Bearer ' + token.value }
                        });
                        if(res.status === 401) { logout(); return; }
                        const data = await res.json();
                        licenses.value = data.licenses || [];
                    } catch(e) {
                         ElementPlus.ElMessage.error('加载失败: ' + e.message);
                    } finally {
                        loadingData.value = false;
                    }
                };

                const fetchTamperLogs = async () => {
                    loadingLogs.value = true;
                    try {
                        const res = await fetch('/admin/tamper-logs', {
                            headers: { 'Authorization': 'Bearer ' + token.value }
                        });
                        if(res.status === 401) return;
                        const data = await res.json();
                        tamperLogs.value = data.tamper_logs || [];
                    } catch(e) {
                         ElementPlus.ElMessage.error('加载日志失败: ' + e.message);
                    } finally {
                        loadingLogs.value = false;
                    }
                };

                const edit = (row) => {
                    form.device_id = row.device_id;
                    form.customer = row.customer;
                    form.expires_at = row.expires_at;
                    form.features = row.features || [];
                    form.expected_hash = row.expected_hash || '';
                    showAddDialog.value = true;
                };

                const submit = async () => {
                    if(!form.device_id) return ElementPlus.ElMessage.warning('请输入设备 ID');
                    submitting.value = true;
                    try {
                        const res = await fetch('/admin/add', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'Authorization': 'Bearer ' + token.value
                            },
                            body: JSON.stringify(form)
                        });
                        const data = await res.json();
                        if(data.success) {
                            ElementPlus.ElMessage.success('保存成功');
                            showAddDialog.value = false;
                            fetchList();
                        } else {
                            ElementPlus.ElMessage.error(data.error || '保存失败');
                        }
                    } catch(e) {
                        ElementPlus.ElMessage.error('保存出错: ' + e.message);
                    } finally {
                        submitting.value = false;
                    }
                }
                
                const confirmDelete = (id, type) => {
                    ElementPlus.ElMessageBox.confirm(
                        type === 'license' ? '确定要删除设备 ' + id + ' 的授权吗？' : '确定要删除这条破解记录吗？',
                        '警告',
                        { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
                    ).then(async () => {
                        try {
                            const res = await fetch('/admin/delete', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'Authorization': 'Bearer ' + token.value
                                },
                                body: JSON.stringify({ device_id: id, type: type, key: type === 'log' ? id : undefined })
                            });
                            const data = await res.json();
                            if(data.success) {
                                ElementPlus.ElMessage.success('删除成功');
                                if(type === 'license') fetchList();
                                else fetchTamperLogs();
                            } else {
                                ElementPlus.ElMessage.error(data.error || '删除失败');
                            }
                        } catch(e) {
                            ElementPlus.ElMessage.error('删除出错: ' + e.message);
                        }
                    }).catch(() => {});
                };

                const getStatusType = (row) => {
                    if(row.status !== 'active') return 'danger';
                    if(new Date(row.expires_at) < new Date()) return 'warning';
                    return 'success';
                };

                onMounted(() => {
                    loading.value = false;
                    if(token.value) {
                        fetchList();
                        fetchTamperLogs();
                    }
                });

                return {
                    loading, token, inputToken, login, logout,
                    licenses, tamperLogs, loadingData, loadingLogs,
                    showAddDialog, submitting, form, submit, edit,
                    getStatusType, fetchList, fetchTamperLogs, confirmDelete
                };
            }
        });
        
        app.use(ElementPlus);
        app.mount('#app');
    </script>
</body>
</html>
`;
