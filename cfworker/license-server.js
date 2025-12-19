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

        // Admin API: List Licenses
        if (request.method === "GET" && url.pathname === "/admin/list") {
            return handleListLicenses(request, env);
        }

        return new Response("Not found", { status: 404 });
    },
};

// =============================================================================
// API Handlers
// =============================================================================

async function handleVerify(request, env) {
    try {
        const { device_id } = await request.json();

        if (!device_id) {
            return Response.json(
                { valid: false, error: "Missing device_id" },
                { status: 400, headers: corsHeaders() }
            );
        }

        const licenseData = await env.LICENSES.get(`license:${device_id}`, "json");

        if (!licenseData) {
            return Response.json(
                { valid: false, error: "未找到授权信息" },
                { headers: corsHeaders() }
            );
        }

        if (new Date(licenseData.expires_at) < new Date()) {
            return Response.json(
                { valid: false, error: "授权已过期" },
                { headers: corsHeaders() }
            );
        }

        if (licenseData.status !== "active") {
            return Response.json(
                { valid: false, error: "授权已被禁用" },
                { headers: corsHeaders() }
            );
        }

        return Response.json(
            {
                valid: true,
                customer: licenseData.customer,
                expires_at: licenseData.expires_at,
                features: licenseData.features || ["mqtt_external", "ai", "r2_archive", "notifications"],
            },
            { headers: corsHeaders() }
        );
    } catch (e) {
        return Response.json(
            { valid: false, error: "Internal Server Error" },
            { status: 500, headers: corsHeaders() }
        );
    }
}

async function handleAddLicense(request, env) {
    if (!checkAuth(request, env)) return new Response("Unauthorized", { status: 401, headers: corsHeaders() });

    try {
        const { device_id, customer, expires_at, features } = await request.json();

        const licenseData = {
            device_id,
            status: "active",
            customer,
            expires_at,
            features: features || ["mqtt_external", "ai", "r2_archive", "notifications"],
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
                    <el-button type="primary" @click="showAddDialog = true">添加授权</el-button>
                    <el-button type="info" @click="logout">退出</el-button>
                </div>
            </div>

            <el-card>
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
                    <el-table-column label="功能权限">
                        <template #default="scope">
                            <el-tag v-for="f in scope.row.features" :key="f" size="small" class="feature-tag">{{ f }}</el-tag>
                        </template>
                    </el-table-column>
                    <el-table-column label="操作" width="150" align="right">
                         <template #default="scope">
                            <el-button type="primary" link @click="edit(scope.row)">编辑</el-button>
                         </template>
                    </el-table-column>
                </el-table>
            </el-card>

            <!-- Add Dialog -->
            <el-dialog v-model="showAddDialog" title="添加/编辑授权" width="500px">
                <el-form :model="form" label-width="100px">
                    <el-form-item label="设备 ID">
                        <el-input v-model="form.device_id" placeholder="MCS-XXXX-XXXX-XXXX"></el-input>
                    </el-form-item>
                    <el-form-item label="客户名称">
                        <el-input v-model="form.customer" placeholder="客户公司名称"></el-input>
                    </el-form-item>
                    <el-form-item label="过期时间">
                         <el-date-picker v-model="form.expires_at" type="date" placeholder="选择日期" format="YYYY-MM-DD" value-format="YYYY-MM-DD" style="width: 100%"></el-date-picker>
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
                const loadingData = ref(false);
                const showAddDialog = ref(false);
                const submitting = ref(false);
                
                const form = reactive({
                    device_id: '',
                    customer: '',
                    expires_at: '',
                    features: ['mqtt_external', 'ai', 'r2_archive', 'notifications']
                });

                const login = () => {
                    if(inputToken.value) {
                        token.value = inputToken.value;
                        localStorage.setItem('admin_token', inputToken.value);
                        fetchList();
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
                        if(res.status === 401) {
                            logout();
                            ElementPlus.ElMessage.error('Token 无效或过期');
                            return;
                        }
                        const data = await res.json();
                        licenses.value = data.licenses || [];
                    } catch(e) {
                         ElementPlus.ElMessage.error('加载失败: ' + e.message);
                    } finally {
                        loadingData.value = false;
                    }
                };

                const edit = (row) => {
                    form.device_id = row.device_id;
                    form.customer = row.customer;
                    form.expires_at = row.expires_at;
                    form.features = row.features || [];
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
                
                const getStatusType = (row) => {
                    if(row.status !== 'active') return 'danger';
                    if(new Date(row.expires_at) < new Date()) return 'warning';
                    return 'success';
                };

                onMounted(() => {
                    loading.value = false;
                    if(token.value) fetchList();
                });

                return {
                    loading, token, inputToken, login, logout,
                    licenses, loadingData,
                    showAddDialog, submitting, form, submit, edit,
                    getStatusType
                };
            }
        });
        
        app.use(ElementPlus);
        app.mount('#app');
    </script>
</body>
</html>
`;
