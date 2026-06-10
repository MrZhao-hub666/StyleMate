<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'
import { useAppStore } from '../stores/app'

const store = useAppStore()
const form = ref({ occasion: '', preference: '', city: '北京' })
const loading = ref(false)
const result = ref(null)
const photoData = ref(null)

const occasions = ['面试', '约会', '商务日常', '休闲日常', '运动健身', '晚宴']

onMounted(async () => {
  await store.loadProfile()
  if (store.profile.city) form.value.city = store.profile.city
})

function handlePhoto(file) {
  if (!file?.raw) return
  const r = new FileReader()
  r.onload = e => { photoData.value = e.target.result }
  r.readAsDataURL(file.raw)
}

function downloadImage(url, name) {
  const a = document.createElement('a')
  a.href = url
  a.download = name || 'preview.jpg'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

async function recommend(forceTextOnly = false) {
  if (!form.value.occasion) { ElMessage.warning('请选择场合'); return }
  loading.value = true; result.value = null
  try {
    const r = await api.recommend({
      ...form.value,
      photo_data: photoData.value || null,
      force_text_only: forceTextOnly,
    })
    const data = r.data
    if (data.need_confirm) {
      try {
        await ElMessageBox.confirm(
          data.preview_warning || '缺少人物照片或衣橱物品，无法生成预览图。\n\n是否继续获取纯文字搭配建议？',
          '暂时无法生成预览图',
          { confirmButtonText: '继续', cancelButtonText: '取消', type: 'warning' }
        )
        await recommend(true)
        return
      } catch { /* cancelled */ }
    } else {
      result.value = data
    }
  } catch { ElMessage.error('推荐失败，请检查服务') }
  finally { loading.value = false }
}
</script>

<template>
  <div style="max-width: 960px; margin: 0 auto">
    <h2 style="color: rgba(255,255,255,0.9); font-size: 22px; margin: 0 0 20px">AI 搭配推荐</h2>

    <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 20px; padding: 28px; margin-bottom: 24px">
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px">
        <div>
          <label style="color: rgba(255,255,255,0.5); font-size: 13px; display: block; margin-bottom: 6px">场合</label>
          <el-select v-model="form.occasion" placeholder="选择场合" style="width: 100%">
            <el-option v-for="o in occasions" :key="o" :label="o" :value="o" />
          </el-select>
        </div>
        <div>
          <label style="color: rgba(255,255,255,0.5); font-size: 13px; display: block; margin-bottom: 6px">城市</label>
          <el-input v-model="form.city" placeholder="用于天气查询" />
        </div>
      </div>
      <div style="margin-bottom: 20px">
        <label style="color: rgba(255,255,255,0.5); font-size: 13px; display: block; margin-bottom: 6px">偏好描述</label>
        <el-input v-model="form.preference" type="textarea" :rows="2" placeholder="如：沉稳大气、青春活力、简约风..." />
      </div>
      <div style="margin-bottom: 20px">
        <label style="color: rgba(255,255,255,0.5); font-size: 13px; display: block; margin-bottom: 6px">上传你的照片（生成穿搭预览图需要）</label>
        <div style="display: flex; align-items: center; gap: 12px">
          <el-upload :auto-upload="false" :show-file-list="false" accept="image/*" :on-change="handlePhoto">
            <el-button>📁 选择照片</el-button>
          </el-upload>
        </div>
        <img v-if="photoData" :src="photoData" style="width: 120px; margin-top: 10px; border-radius: 10px" />
      </div>
      <div v-if="store.profile.height || store.profile.weight">
        <span style="color: rgba(255,255,255,0.4); font-size: 13px">
          📏 {{ store.profile.height }}cm · {{ store.profile.weight }}kg<template v-if="store.profile.gender && store.profile.gender !== '未设置'"> · {{ store.profile.gender }}</template>
        </span>
      </div>
      <el-button type="primary" size="large" @click="recommend()" :loading="loading" style="width: 100%; margin-top: 12px; height: 48px">
        {{ loading ? 'AI 正在为你搭配（含预览图约60秒）...' : '✨ 开始推荐' }}
      </el-button>
    </div>

    <div v-if="result">
      <!-- 天气 -->
      <div v-if="result.weather?.temp"
        style="background: rgba(244,114,182,0.1); border: 1px solid rgba(244,114,182,0.2); border-radius: 12px;
               padding: 14px 20px; margin-bottom: 20px; display: flex; align-items: center; gap: 10px">
        <span style="font-size: 24px; color: #f472b6; font-weight: 700">{{ result.weather.temp }}°C</span>
        <span style="color: rgba(255,255,255,0.6); font-size: 14px">{{ result.weather.city }} · {{ result.weather.condition }}</span>
      </div>

      <!-- 推荐卡片 -->
      <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px">
        <div v-for="(rec, idx) in result.recommendations" :key="idx"
          style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 16px; overflow: hidden">
          <!-- 预览图（悬停显示下载） -->
          <div v-if="rec.preview_url" style="position: relative; overflow: hidden; cursor: pointer"
            @mouseenter="rec._hover = true" @mouseleave="rec._hover = false">
            <img :src="rec.preview_url"
              style="width: 100%; max-height: 280px; object-fit: cover; display: block" />
            <div v-show="rec._hover"
              style="position: absolute; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; transition: opacity 0.2s"
              @click="downloadImage(rec.preview_url, '搭配推荐_' + (idx+1) + '.jpg')">
              <el-icon style="font-size: 36px; color: #fff"><Download /></el-icon>
            </div>
          </div>
          <div style="padding: 20px">
            <div style="font-size: 16px; font-weight: 600; color: #a78bfa; margin-bottom: 10px">{{ rec.name }}</div>
            <div style="margin-bottom: 10px">
              <template v-if="rec.items">
                <el-tag v-for="(item, i) in rec.items" :key="i" size="small" style="margin: 2px" type="info">
                  {{ item }}
                </el-tag>
              </template>
            </div>
            <div style="color: rgba(255,255,255,0.45); font-size: 13px; line-height: 1.6">{{ rec.reason }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
