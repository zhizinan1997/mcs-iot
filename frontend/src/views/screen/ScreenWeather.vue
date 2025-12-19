<template>
  <div class="screen-weather-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>天气接口设置</span>
          <el-tag :type="weatherConfig.enabled ? 'success' : 'info'">
            {{ weatherConfig.enabled ? "已启用" : "未启用" }}
          </el-tag>
        </div>
      </template>
      <el-form :model="weatherConfig" label-width="120px">
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
          />
        </el-form-item>
        <el-form-item label="城市拼音">
          <el-input v-model="weatherConfig.city_pinyin" disabled placeholder="自动生成" />
        </el-form-item>
        <el-form-item label="API 私钥">
          <el-input v-model="weatherConfig.api_key" placeholder="请输入 Seniverse API Key" type="password" show-password />
          <div class="form-tip">
            请前往 <a href="https://www.seniverse.com/" target="_blank" style="color: #409EFF">心知天气 (Seniverse)</a> 申请免费 API Key
          </div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveWeatherConfig" :loading="saving">保存配置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
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
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.form-tip {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}
</style>
