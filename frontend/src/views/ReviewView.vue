<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'
import CameraPanel from '../components/CameraPanel.vue'

const occasion = ref('日常休闲')
const result = ref(null)
const loading = ref(false)
const showCamera = ref(false)
const outfitData = ref([])
const photoData = ref(null)

function handleCapture(data) {
  outfitData.value = [data]
  photoData.value = data.crop_base64
  showCamera.value = false
  ElMessage.success('已采集')
}

function handleFileUpload(file) {
  const r = new FileReader()
  r.onload = e => {
    outfitData.value = [{ crop_base64: e.target.result, zone: 'full', has_person: true }]
    photoData.value = e.target.result
  }
  r.readAsDataURL(file.raw)
  ElMessage.success('已加载图片')
}

async function review() {
  if (!outfitData.value.length) { ElMessage.warning('请先拍照或上传穿搭'); return }
  loading.value = true
  try {
    const r = await api.review({ outfit_items: outfitData.value, occasion: occasion.value })
    result.value = r.data
  } catch { ElMessage.error('评价失败') }
  finally { loading.value = false }
}
</script>

<template>
  <div style="max-width: 800px; margin: 0 auto">
    <h2 style="color: rgba(255,255,255,0.9); font-size: 22px; margin: 0 0 20px">AI 穿搭评价</h2>

    <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 20px; padding: 28px; margin-bottom: 24px">
      <div style="margin-bottom: 16px">
        <label style="color: rgba(255,255,255,0.5); font-size: 13px; display: block; margin-bottom: 6px">场合</label>
        <el-select v-model="occasion" style="width: 200px">
          <el-option v-for="o in ['日常休闲','面试','约会','商务','运动']" :key="o" :label="o" :value="o" />
        </el-select>
      </div>
      <div style="display: flex; gap: 10px; margin-bottom: 16px">
        <el-button @click="showCamera = !showCamera">{{ showCamera ? '关闭摄像头' : '📷 拍照采集' }}</el-button>
        <el-upload :auto-upload="false" :show-file-list="false" accept="image/*" :on-change="handleFileUpload">
          <el-button>📁 上传图片</el-button>
        </el-upload>
        <el-button type="primary" @click="review" :loading="loading">
          {{ loading ? 'AI 评价中...' : '✨ 开始评价' }}
        </el-button>
      </div>

      <div v-if="showCamera" style="margin-bottom: 16px; padding: 20px; background: rgba(0,0,0,0.2); border-radius: 16px">
        <CameraPanel @capture="handleCapture" @close="showCamera = false" />
      </div>
      <img v-if="photoData" :src="photoData" style="max-width: 200px; border-radius: 10px; margin-bottom: 16px" />
      <el-tag v-if="outfitData.length">已采集穿搭数据</el-tag>
    </div>

    <div v-if="result"
      style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 20px; padding: 32px; text-align: center">
      <div style="font-size: 72px; font-weight: 800; background: linear-gradient(135deg, #a78bfa, #f472b6);
                  -webkit-background-clip: text; -webkit-text-fill-color: transparent; line-height: 1">
        {{ result.score }}
      </div>
      <div style="color: rgba(255,255,255,0.4); font-size: 14px; margin-bottom: 16px">/ 10 分</div>
      <p style="color: rgba(255,255,255,0.65); font-size: 15px; line-height: 1.6; margin-bottom: 24px; max-height: 200px; overflow-y: auto">{{ result.summary }}</p>

      <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; text-align: left">
        <div style="max-height: 300px; overflow-y: auto">
          <h4 style="color: #34d399; font-size: 14px; margin: 0 0 10px">✦ 亮点</h4>
          <ul style="margin: 0; padding-left: 16px; color: rgba(255,255,255,0.6); font-size: 13px; line-height: 2; word-break: break-word">
            <li v-for="(h, i) in result.highlights" :key="i">{{ h }}</li>
          </ul>
        </div>
        <div style="max-height: 300px; overflow-y: auto">
          <h4 style="color: #fbbf24; font-size: 14px; margin: 0 0 10px">▲ 不足</h4>
          <ul style="margin: 0; padding-left: 16px; color: rgba(255,255,255,0.6); font-size: 13px; line-height: 2; word-break: break-word">
            <li v-for="(w, i) in result.weaknesses" :key="i">{{ w }}</li>
          </ul>
        </div>
        <div style="max-height: 300px; overflow-y: auto">
          <h4 style="color: #38bdf8; font-size: 14px; margin: 0 0 10px">➔ 建议</h4>
          <ul style="margin: 0; padding-left: 16px; color: rgba(255,255,255,0.6); font-size: 13px; line-height: 2; word-break: break-word">
            <li v-for="(s, i) in result.suggestions" :key="i">{{ s }}</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>
