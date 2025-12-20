<template>
  <div class="screen-weather-page">
    <div class="glass-panel main-container">
      <div class="header">
        <div class="icon-box">
          <el-icon :size="24" color="#0071e3"><PartlyCloudy /></el-icon>
        </div>
        <div class="title-info">
          <h3>天气设置</h3>
          <p class="subtitle">配置大屏显示的天气数据源</p>
        </div>
        <el-tag :type="weatherConfig.enabled ? 'success' : 'info'" effect="dark" round>
          {{ weatherConfig.enabled ? "已启用" : "未启用" }}
        </el-tag>
      </div>

      <el-divider class="glass-divider" />

      <div class="form-content">
        <el-form 
          :model="weatherConfig" 
          label-width="120px" 
          label-position="left"
          class="mac-form"
        >
          <el-form-item label="启用天气">
            <el-switch v-model="weatherConfig.enabled" />
          </el-form-item>

          <el-form-item label="所在地区">
            <el-cascader
              v-model="selectedRegion"
              :options="provinceAndCityData"
              :props="{ value: 'label' }"
              placeholder="请选择省/市"
              @change="handleRegionChange"
              style="width: 100%"
              class="mac-cascader"
            />
          </el-form-item>

          <el-form-item label="城市拼音">
            <el-input v-model="weatherConfig.city_pinyin" disabled placeholder="自动生成" />
            <p class="form-tip">根据所选城市自动生成，用于天气 API 查询</p>
          </el-form-item>

          <el-form-item label="API 私钥">
            <el-input 
              v-model="weatherConfig.api_key" 
              placeholder="请输入 Seniverse API Key" 
              type="password" 
              show-password 
            />
            <div class="form-tip">
              请前往 <a href="https://www.seniverse.com/" target="_blank" style="color: #0071e3">心知天气 (Seniverse)</a> 申请免费 API Key
            </div>
          </el-form-item>

          <div class="form-actions">
            <el-button @click="loadWeatherConfig" round>重置</el-button>
            <el-button type="primary" @click="saveWeatherConfig" :loading="saving" round>保存配置</el-button>
          </div>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { PartlyCloudy } from "@element-plus/icons-vue";
import { configApi } from "../../api";
import { provinceAndCityData } from 'element-china-area-data';
import { pinyin } from 'pinyin-pro';

const saving = ref(false);

const weatherConfig = reactive({
  enabled: true,
  province: '',
  city: '',
  city_pinyin: '',
  api_key: ''
});

const selectedRegion = ref<string[]>([]);

async function loadWeatherConfig() {
  try {
    const res = await configApi.getWeather();
    Object.assign(weatherConfig, res.data);
    if (weatherConfig.province && weatherConfig.city) {
      selectedRegion.value = [weatherConfig.province, weatherConfig.city];
    }
  } catch (error) {
    console.error("Failed to load weather config:", error);
  }
}

async function saveWeatherConfig() {
  saving.value = true;
  try {
    await configApi.updateWeather(weatherConfig);
    ElMessage.success("天气配置已保存");
  } catch (error) {
    ElMessage.error("保存失败");
  } finally {
    saving.value = false;
  }
}

const handleRegionChange = (value: string[]) => {
  if (value && value.length === 2) {
    weatherConfig.province = value[0] || '';
    weatherConfig.city = value[1] || '';

    let cityName = value[1] || '';
    if (cityName.endsWith('市')) cityName = cityName.slice(0, -1);
    else if (cityName.endsWith('地区')) cityName = cityName.slice(0, -2);
    else if (cityName.endsWith('盟')) cityName = cityName.slice(0, -1);
    else if (cityName.endsWith('自治州')) cityName = cityName.slice(0, -3);

    // Special case: Direct-controlled municipalities
    const municipalities = ['北京市', '上海市', '天津市', '重庆市'];
    if (municipalities.includes(value[0] || '')) {
        cityName = value[0] || '';
        if (cityName.endsWith('市')) cityName = cityName.slice(0, -1);
    } else if (cityName === '市辖区' || cityName === '县') {
        cityName = value[0] || '';
        if (cityName.endsWith('市')) cityName = cityName.slice(0, -1);
    }

    if (cityName) {
      const py = pinyin(cityName, { toneType: 'none', type: 'array' }) as string[];
      weatherConfig.city_pinyin = py.join('');
    }
  }
};

onMounted(() => {
  loadWeatherConfig();
});
</script>

<style scoped>
.screen-weather-page {
  padding: 40px;
  height: 100%;
  box-sizing: border-box;
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

.glass-panel {
  width: 600px;
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.6);
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(20px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.header {
  padding: 32px 40px;
  display: flex;
  align-items: center;
  gap: 20px;
}

.icon-box {
  width: 56px;
  height: 56px;
  background: rgba(0, 113, 227, 0.1);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.title-info {
  flex: 1;
}

.title-info h3 {
  margin: 0 0 6px;
  font-size: 20px;
  color: #1d1d1f;
}
.title-info .subtitle {
  margin: 0;
  color: #86868b;
  font-size: 14px;
}

.glass-divider {
  margin: 0;
  border-color: rgba(0,0,0,0.05);
}

.form-content {
  padding: 40px;
}

.mac-form .el-form-item {
  margin-bottom: 24px;
}

.mac-cascader {
  width: 100%;
}
:deep(.mac-cascader .el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #dcdfe6 inset !important;
}

.form-tip {
  font-size: 12px;
  color: #86868b;
  margin-top: 6px;
  line-height: 1.4;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 16px;
  margin-top: 40px;
}
</style>
