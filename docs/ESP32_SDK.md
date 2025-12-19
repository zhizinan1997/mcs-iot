·# MCS-IoT ESP32 设备接入 SDK

本文档提供 ESP32 设备接入 MCS-IoT 平台的完整驱动库和示例代码。

---

## 目录

- [1. 协议说明](#1-协议说明)
- [2. 驱动库](#2-驱动库)
- [3. 使用示例](#3-使用示例)
- [4. 配置说明](#4-配置说明)

---

## 1. 协议说明

### MQTT Topic 规范

| 方向 | Topic | 说明 |
|------|-------|------|
| 上行 | `mcs/{设备SN}/up` | 设备上报数据 |
| 下行 | `mcs/{设备SN}/down` | 服务器下发指令 |

### 上行数据格式 (JSON)

```json
{
  "ts": 1702723200,    // Unix 时间戳 (秒)
  "seq": 123,          // 序列号 (0-65535 循环)
  "v_raw": 2045.5,     // 传感器原始值
  "temp": 25.3,        // 温度 (°C)
  "humi": 45.2,        // 湿度 (%)
  "bat": 85,           // 电池电量 (%)
  "rssi": -72,         // 信号强度 (dBm)
  "net": "4G",         // 网络类型 (WiFi/4G/NB-IoT)
  "err": 0             // 错误码 (0=正常)
}
```

### 下行指令格式

```json
{
  "cmd": "config",
  "params": {
    "interval": 10
  }
}
```

---

## 2. 驱动库

### 2.1 头文件 `mcs_iot.h`

```c
/**
 * MCS-IoT ESP32 驱动库
 * 版本: 1.0.0
 * 作者: MCS-IoT Team
 */

#ifndef MCS_IOT_H
#define MCS_IOT_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// ============================================================================
// 配置结构体
// ============================================================================

typedef struct {
    const char* broker_host;     // MQTT 服务器地址
    uint16_t broker_port;        // MQTT 端口 (1883 或 8883)
    const char* device_sn;       // 设备序列号
    const char* mqtt_user;       // MQTT 用户名
    const char* mqtt_pass;       // MQTT 密码
    bool use_tls;                // 是否使用 TLS
    const char* ca_cert;         // CA 证书 (TLS 时需要)
    uint16_t report_interval;    // 上报间隔 (秒)
} mcs_config_t;

typedef struct {
    float v_raw;                 // 传感器原始值
    float temp;                  // 温度
    float humi;                  // 湿度
    uint8_t bat;                 // 电池电量
    int8_t rssi;                 // 信号强度
    const char* net;             // 网络类型
    uint8_t err;                 // 错误码
} mcs_sensor_data_t;

// 指令回调函数类型
typedef void (*mcs_cmd_callback_t)(const char* cmd, const char* params);

// ============================================================================
// API 函数
// ============================================================================

/**
 * 初始化 MCS-IoT 客户端
 * @param config 配置参数
 * @return 0=成功, 其他=错误码
 */
int mcs_init(const mcs_config_t* config);

/**
 * 连接到 MQTT 服务器
 * @return 0=成功, 其他=错误码
 */
int mcs_connect(void);

/**
 * 断开连接
 */
void mcs_disconnect(void);

/**
 * 检查连接状态
 * @return true=已连接
 */
bool mcs_is_connected(void);

/**
 * 上报传感器数据
 * @param data 传感器数据
 * @return 0=成功, 其他=错误码
 */
int mcs_report_data(const mcs_sensor_data_t* data);

/**
 * 设置指令回调函数
 * @param callback 回调函数
 */
void mcs_set_cmd_callback(mcs_cmd_callback_t callback);

/**
 * 主循环处理 (需在主循环中调用)
 */
void mcs_loop(void);

/**
 * 获取上一次错误信息
 * @return 错误描述字符串
 */
const char* mcs_get_last_error(void);

#ifdef __cplusplus
}
#endif

#endif // MCS_IOT_H
```

### 2.2 实现文件 `mcs_iot.c`

```c
/**
 * MCS-IoT ESP32 驱动库实现
 */

#include "mcs_iot.h"
#include <stdio.h>
#include <string.h>
#include <time.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "mqtt_client.h"
#include "cJSON.h"

static const char* TAG = "MCS_IOT";

// ============================================================================
// 内部变量
// ============================================================================

static mcs_config_t g_config;
static esp_mqtt_client_handle_t g_mqtt_client = NULL;
static bool g_connected = false;
static uint16_t g_seq = 0;
static mcs_cmd_callback_t g_cmd_callback = NULL;
static char g_topic_up[64];
static char g_topic_down[64];
static char g_last_error[128] = "";

// ============================================================================
// 内部函数
// ============================================================================

static void set_error(const char* err) {
    strncpy(g_last_error, err, sizeof(g_last_error) - 1);
    ESP_LOGE(TAG, "%s", err);
}

static void mqtt_event_handler(void* handler_args, esp_event_base_t base, 
                                int32_t event_id, void* event_data) {
    esp_mqtt_event_handle_t event = (esp_mqtt_event_handle_t)event_data;
    
    switch (event->event_id) {
        case MQTT_EVENT_CONNECTED:
            ESP_LOGI(TAG, "MQTT 已连接");
            g_connected = true;
            // 订阅下行 Topic
            esp_mqtt_client_subscribe(g_mqtt_client, g_topic_down, 1);
            break;
            
        case MQTT_EVENT_DISCONNECTED:
            ESP_LOGW(TAG, "MQTT 断开连接");
            g_connected = false;
            break;
            
        case MQTT_EVENT_DATA:
            // 处理下行指令
            if (g_cmd_callback && event->data_len > 0) {
                char* data = malloc(event->data_len + 1);
                if (data) {
                    memcpy(data, event->data, event->data_len);
                    data[event->data_len] = '\0';
                    
                    cJSON* json = cJSON_Parse(data);
                    if (json) {
                        cJSON* cmd = cJSON_GetObjectItem(json, "cmd");
                        cJSON* params = cJSON_GetObjectItem(json, "params");
                        if (cmd && cmd->valuestring) {
                            char* params_str = params ? cJSON_PrintUnformatted(params) : NULL;
                            g_cmd_callback(cmd->valuestring, params_str);
                            free(params_str);
                        }
                        cJSON_Delete(json);
                    }
                    free(data);
                }
            }
            break;
            
        case MQTT_EVENT_ERROR:
            ESP_LOGE(TAG, "MQTT 错误");
            set_error("MQTT 连接错误");
            break;
            
        default:
            break;
    }
}

// ============================================================================
// API 实现
// ============================================================================

int mcs_init(const mcs_config_t* config) {
    if (!config || !config->broker_host || !config->device_sn) {
        set_error("配置参数无效");
        return -1;
    }
    
    memcpy(&g_config, config, sizeof(mcs_config_t));
    
    // 构建 Topic
    snprintf(g_topic_up, sizeof(g_topic_up), "mcs/%s/up", config->device_sn);
    snprintf(g_topic_down, sizeof(g_topic_down), "mcs/%s/down", config->device_sn);
    
    ESP_LOGI(TAG, "初始化完成, 设备SN: %s", config->device_sn);
    return 0;
}

int mcs_connect(void) {
    esp_mqtt_client_config_t mqtt_cfg = {
        .broker.address.hostname = g_config.broker_host,
        .broker.address.port = g_config.broker_port,
        .credentials.username = g_config.mqtt_user,
        .credentials.authentication.password = g_config.mqtt_pass,
        .credentials.client_id = g_config.device_sn,
    };
    
    if (g_config.use_tls) {
        mqtt_cfg.broker.address.transport = MQTT_TRANSPORT_OVER_SSL;
        if (g_config.ca_cert) {
            mqtt_cfg.broker.verification.certificate = g_config.ca_cert;
        }
    } else {
        mqtt_cfg.broker.address.transport = MQTT_TRANSPORT_OVER_TCP;
    }
    
    g_mqtt_client = esp_mqtt_client_init(&mqtt_cfg);
    if (!g_mqtt_client) {
        set_error("MQTT 客户端初始化失败");
        return -1;
    }
    
    esp_mqtt_client_register_event(g_mqtt_client, ESP_EVENT_ANY_ID, 
                                    mqtt_event_handler, NULL);
    
    esp_err_t err = esp_mqtt_client_start(g_mqtt_client);
    if (err != ESP_OK) {
        set_error("MQTT 启动失败");
        return -1;
    }
    
    ESP_LOGI(TAG, "正在连接 MQTT...");
    return 0;
}

void mcs_disconnect(void) {
    if (g_mqtt_client) {
        esp_mqtt_client_stop(g_mqtt_client);
        esp_mqtt_client_destroy(g_mqtt_client);
        g_mqtt_client = NULL;
    }
    g_connected = false;
}

bool mcs_is_connected(void) {
    return g_connected;
}

int mcs_report_data(const mcs_sensor_data_t* data) {
    if (!g_connected || !g_mqtt_client) {
        set_error("未连接到服务器");
        return -1;
    }
    
    if (!data) {
        set_error("数据参数无效");
        return -1;
    }
    
    // 构建 JSON
    cJSON* json = cJSON_CreateObject();
    cJSON_AddNumberToObject(json, "ts", (int)time(NULL));
    cJSON_AddNumberToObject(json, "seq", g_seq++);
    cJSON_AddNumberToObject(json, "v_raw", data->v_raw);
    cJSON_AddNumberToObject(json, "temp", data->temp);
    cJSON_AddNumberToObject(json, "humi", data->humi);
    cJSON_AddNumberToObject(json, "bat", data->bat);
    cJSON_AddNumberToObject(json, "rssi", data->rssi);
    cJSON_AddStringToObject(json, "net", data->net ? data->net : "WiFi");
    cJSON_AddNumberToObject(json, "err", data->err);
    
    char* payload = cJSON_PrintUnformatted(json);
    cJSON_Delete(json);
    
    if (!payload) {
        set_error("JSON 序列化失败");
        return -1;
    }
    
    int msg_id = esp_mqtt_client_publish(g_mqtt_client, g_topic_up, 
                                          payload, 0, 1, 0);
    free(payload);
    
    if (msg_id < 0) {
        set_error("消息发布失败");
        return -1;
    }
    
    ESP_LOGD(TAG, "数据已上报, seq=%d", g_seq - 1);
    return 0;
}

void mcs_set_cmd_callback(mcs_cmd_callback_t callback) {
    g_cmd_callback = callback;
}

void mcs_loop(void) {
    // ESP-IDF MQTT 客户端是事件驱动的，此函数可用于扩展
    vTaskDelay(pdMS_TO_TICKS(10));
}

const char* mcs_get_last_error(void) {
    return g_last_error;
}
```

---

## 3. 使用示例

### 3.1 基础示例 `main.c`

```c
/**
 * MCS-IoT ESP32 示例程序
 * 
 * 功能：
 * - 连接 WiFi
 * - 连接 MQTT 服务器
 * - 定时上报传感器数据
 * - 接收并处理服务器指令
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "esp_netif.h"

#include "mcs_iot.h"

// ============================================================================
// 配置 - 请修改为实际值
// ============================================================================

#define WIFI_SSID       "your-wifi-ssid"
#define WIFI_PASS       "your-wifi-password"

#define MQTT_BROKER     "mqtt.yourdomain.com"   // MQTT 服务器
#define MQTT_PORT       8883                     // TLS 端口
#define MQTT_USER       "device"                 // MQTT 用户名
#define MQTT_PASS       "your-password"          // MQTT 密码

#define DEVICE_SN       "H20101"                 // 设备序列号

// TLS 证书 (可选，用于服务器验证)
static const char* ca_cert = NULL;  // 如果需要，替换为实际证书

static const char* TAG = "MCS_DEMO";
static uint16_t g_report_interval = 10;  // 上报间隔 (秒)

// ============================================================================
// WiFi 连接
// ============================================================================

static void wifi_event_handler(void* arg, esp_event_base_t event_base,
                               int32_t event_id, void* event_data) {
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        ESP_LOGW(TAG, "WiFi 断开，正在重连...");
        esp_wifi_connect();
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t* event = (ip_event_got_ip_t*)event_data;
        ESP_LOGI(TAG, "获取到 IP: " IPSTR, IP2STR(&event->ip_info.ip));
    }
}

static void wifi_init(void) {
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();
    
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, 
                                                &wifi_event_handler, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, 
                                                &wifi_event_handler, NULL));
    
    wifi_config_t wifi_config = {
        .sta = {
            .ssid = WIFI_SSID,
            .password = WIFI_PASS,
        },
    };
    
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());
    
    ESP_LOGI(TAG, "WiFi 初始化完成");
}

// ============================================================================
// 传感器读取 (示例)
// ============================================================================

static void read_sensor(mcs_sensor_data_t* data) {
    // TODO: 替换为实际的传感器读取代码
    
    // 模拟数据
    static float v = 30.0;
    v += (rand() % 100 - 50) / 10.0;
    if (v < 0) v = 0;
    if (v > 100) v = 100;
    
    data->v_raw = v;
    data->temp = 25.0 + (rand() % 50 - 25) / 10.0;
    data->humi = 45.0 + (rand() % 100 - 50) / 10.0;
    data->bat = 85;
    data->rssi = -65 + (rand() % 20 - 10);
    data->net = "WiFi";
    data->err = 0;
}

// ============================================================================
// 指令处理
// ============================================================================

static void on_command(const char* cmd, const char* params) {
    ESP_LOGI(TAG, "收到指令: %s, 参数: %s", cmd, params ? params : "无");
    
    if (strcmp(cmd, "config") == 0 && params) {
        // 解析配置指令
        cJSON* json = cJSON_Parse(params);
        if (json) {
            cJSON* interval = cJSON_GetObjectItem(json, "interval");
            if (interval && interval->valueint > 0) {
                g_report_interval = interval->valueint;
                ESP_LOGI(TAG, "上报间隔已更新为: %d 秒", g_report_interval);
            }
            cJSON_Delete(json);
        }
    } else if (strcmp(cmd, "reboot") == 0) {
        ESP_LOGI(TAG, "收到重启指令，3秒后重启...");
        vTaskDelay(pdMS_TO_TICKS(3000));
        esp_restart();
    }
}

// ============================================================================
// 主任务
// ============================================================================

static void mcs_task(void* arg) {
    // 等待 WiFi 连接
    vTaskDelay(pdMS_TO_TICKS(5000));
    
    // 初始化 MCS-IoT
    mcs_config_t config = {
        .broker_host = MQTT_BROKER,
        .broker_port = MQTT_PORT,
        .device_sn = DEVICE_SN,
        .mqtt_user = MQTT_USER,
        .mqtt_pass = MQTT_PASS,
        .use_tls = (MQTT_PORT == 8883),
        .ca_cert = ca_cert,
        .report_interval = g_report_interval,
    };
    
    if (mcs_init(&config) != 0) {
        ESP_LOGE(TAG, "MCS 初始化失败: %s", mcs_get_last_error());
        vTaskDelete(NULL);
        return;
    }
    
    // 设置指令回调
    mcs_set_cmd_callback(on_command);
    
    // 连接 MQTT
    if (mcs_connect() != 0) {
        ESP_LOGE(TAG, "MQTT 连接失败: %s", mcs_get_last_error());
        vTaskDelete(NULL);
        return;
    }
    
    // 等待连接成功
    int retry = 0;
    while (!mcs_is_connected() && retry < 30) {
        vTaskDelay(pdMS_TO_TICKS(1000));
        retry++;
    }
    
    if (!mcs_is_connected()) {
        ESP_LOGE(TAG, "MQTT 连接超时");
        vTaskDelete(NULL);
        return;
    }
    
    ESP_LOGI(TAG, "=== MCS-IoT 已启动 ===");
    ESP_LOGI(TAG, "设备SN: %s", DEVICE_SN);
    ESP_LOGI(TAG, "上报间隔: %d 秒", g_report_interval);
    
    // 主循环
    mcs_sensor_data_t sensor_data;
    TickType_t last_report = 0;
    
    while (1) {
        mcs_loop();
        
        TickType_t now = xTaskGetTickCount();
        if ((now - last_report) >= pdMS_TO_TICKS(g_report_interval * 1000)) {
            if (mcs_is_connected()) {
                read_sensor(&sensor_data);
                
                if (mcs_report_data(&sensor_data) == 0) {
                    ESP_LOGI(TAG, "数据已上报: v_raw=%.2f, temp=%.1f, humi=%.1f",
                             sensor_data.v_raw, sensor_data.temp, sensor_data.humi);
                } else {
                    ESP_LOGW(TAG, "上报失败: %s", mcs_get_last_error());
                }
            } else {
                ESP_LOGW(TAG, "未连接，跳过上报");
            }
            last_report = now;
        }
        
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

// ============================================================================
// 入口
// ============================================================================

void app_main(void) {
    // 初始化 NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
    
    ESP_LOGI(TAG, "=== MCS-IoT ESP32 示例 ===");
    
    // 初始化 WiFi
    wifi_init();
    
    // 创建 MCS 任务
    xTaskCreate(mcs_task, "mcs_task", 8192, NULL, 5, NULL);
}
```

---

## 4. 配置说明

### 4.1 PlatformIO 配置 `platformio.ini`

```ini
[env:esp32dev]
platform = espressif32
board = esp32dev
framework = espidf
monitor_speed = 115200

lib_deps =
    # cJSON 库
    https://github.com/DaveGamble/cJSON.git

build_flags =
    -DCONFIG_ESP_TLS_USING_MBEDTLS=1
```

### 4.2 CMakeLists.txt

```cmake
idf_component_register(
    SRCS 
        "main.c"
        "mcs_iot.c"
    INCLUDE_DIRS "."
    REQUIRES 
        nvs_flash
        esp_wifi
        esp_event
        esp_netif
        mqtt
        json
)
```

---

## 5. 错误码说明

| 错误码 | 说明 |
|-------|------|
| 0 | 成功 |
| -1 | 参数错误 |
| -2 | 连接失败 |
| -3 | 发布失败 |
| -4 | 超时 |

---

## 6. 注意事项

1. **设备SN格式**: 推荐使用 `{类型}{仪表编号}{传感器编号}` 格式，如 `H20101`
2. **TLS证书**: 生产环境建议使用 TLS，需配置正确的 CA 证书
3. **断线重连**: 驱动库会自动处理 MQTT 断线重连
4. **时间同步**: 建议使用 SNTP 同步系统时间，确保 `ts` 字段准确

---

**技术支持**: <zinanzhi@gmail.com>
