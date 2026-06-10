<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'
import CameraPanel from '../components/CameraPanel.vue'

const description = ref('')
const style = ref('')
const loading = ref(false)
const result = ref(null)
const photoData = ref(null)
const showCamera = ref(false)
const savingIndex = ref(-1)
const hoveredIdx = ref(null)

function handleCapture(data) {
  photoData.value = data.crop_base64
  showCamera.value = false
  ElMessage.success('已采集照片')
}

function handleFileUpload(file) {
  const r = new FileReader()
  r.onload = e => { photoData.value = e.target.result }
  r.readAsDataURL(file.raw)
}

function clearPhoto() {
  photoData.value = null
}

async function savePortrait(imageUrl, index) {
  savingIndex.value = index
  try {
    await api.savePortrait({ image_url: imageUrl })
    ElMessage.success('已保存到创意写真相册')
  } catch {
    ElMessage.error('保存失败')
  }
  finally { savingIndex.value = -1 }
}

function downloadImage(url, name) {
  const a = document.createElement('a')
  a.href = url
  a.download = name || 'portrait.jpg'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

async function generate() {
  if (!description.value) { ElMessage.warning('请输入描述'); return }
  loading.value = true
  result.value = null
  try {
    const r = await api.generatePortrait({
      description: description.value,
      style: style.value,
      face_image: photoData.value || null,
    })
    result.value = r.data
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '生成失败，请检查后端 DashScope 配置')
  }
  finally { loading.value = false }
}

const templates = [
  '赛博朋克·霓虹夜景', '日系校园·樱花树下', '港风复古·胶片质感',
  '古风汉服·水墨画境', '极简职场·纯色背景', '街头潮流·城市街景',
]
</script>

<template>
  <div style="max-width: 960px; margin: 0 auto">
    <h2 style="color: rgba(255,255,255,0.9); font-size: 22px; margin: 0 0 20px">AI 创意写真</h2>

    <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 20px; padding: 28px; margin-bottom: 24px">
      <!-- 照片来源 -->
      <div style="margin-bottom: 16px">
        <label style="color: rgba(255,255,255,0.5); font-size: 13px; display: block; margin-bottom: 8px">
          {{ photoData ? '已选择照片' : '选择照片（可选，不选则默认从个人相册选取）' }}
        </label>
        <div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center">
          <el-upload :auto-upload="false" :show-file-list="false" accept="image/*" :on-change="handleFileUpload">
            <el-button>📁 上传照片</el-button>
          </el-upload>
          <el-button @click="showCamera = !showCamera">📷 现场拍摄</el-button>
          <el-button v-if="photoData" size="small" @click="clearPhoto">清除照片</el-button>
        </div>
        <div v-if="showCamera" style="margin-top: 12px; padding: 16px; background: rgba(0,0,0,0.2); border-radius: 12px">
          <CameraPanel @capture="handleCapture" @close="showCamera = false" />
        </div>
        <img v-if="photoData" :src="photoData" style="width: 100px; margin-top: 12px; border-radius: 8px" />
      </div>

      <!-- 描述 -->
      <div style="margin-bottom: 16px">
        <label style="color: rgba(255,255,255,0.5); font-size: 13px; display: block; margin-bottom: 6px">风格描述</label>
        <el-input v-model="description" type="textarea" :rows="2" placeholder="描述你想要的风格和场景..." />
      </div>
      <div style="margin-bottom: 16px">
        <label style="color: rgba(255,255,255,0.5); font-size: 13px; display: block; margin-bottom: 6px">风格提示（可选）</label>
        <el-input v-model="style" placeholder="如：日系、古风、科幻" />
      </div>

      <el-button type="primary" size="large" @click="generate" :loading="loading" style="width: 100%; height: 48px; margin-top: 8px">
        {{ loading ? 'AI 正在生成中（约 10-30 秒）...' : '✨ 生成创意写真' }}
      </el-button>
    </div>

    <!-- 模板 -->
    <div style="margin-bottom: 20px; display: flex; gap: 8px; flex-wrap: wrap">
      <span v-for="t in templates" :key="t" style="cursor: pointer; padding: 6px 14px; border-radius: 20px;
            background: rgba(167,139,250,0.1); color: #a78bfa; font-size: 13px; transition: all 0.2s"
        @click="description = t; style = t.split('\u00b7')[0]?.trim()"
        @mouseenter="e => e.target.style.background = 'rgba(167,139,250,0.2)'"
        @mouseleave="e => e.target.style.background = 'rgba(167,139,250,0.1)'">
        {{ t }}
      </span>
    </div>

    <!-- 结果 -->
    <div v-if="result" style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 20px; padding: 28px">
      <div style="color: rgba(255,255,255,0.9); font-weight: 600; margin-bottom: 16px">✨ 生成结果</div>

      <!-- 图片网格 -->
      <div v-if="result.images && result.images.length" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 20px">
        <div v-for="(img, i) in result.images" :key="i"
          style="border-radius: 12px; overflow: hidden; background: rgba(255,255,255,0.05); position: relative"
          @mouseenter="hoveredIdx = i" @mouseleave="hoveredIdx = null">
          <img :src="img" style="width: 100%; height: auto; display: block" />
          <div v-show="hoveredIdx === i"
            style="position: absolute; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; gap: 12px">
            <el-button size="small" @click.stop="downloadImage(img, '创意写真_' + (i+1) + '.jpg')">
              <el-icon style="margin-right: 4px"><Download /></el-icon>下载
            </el-button>
            <el-button
              :loading="savingIndex === i"
              size="small"
              type="success"
              @click.stop="savePortrait(img, i)"
            >
              💾 保存到相册
            </el-button>
          </div>
        </div>
      </div>
      <div v-else-if="result.error" style="color: #f56c6c; font-size: 14px; margin-bottom: 16px">
        ❌ 生图失败：{{ result.error }}
      </div>

      <!-- 模型信息 -->
      <div style="color: rgba(255,255,255,0.35); font-size: 12px; margin-bottom: 12px">
        模型：{{ result.generation_model || 'N/A' }}
      </div>

      <!-- Prompt -->
      <div style="color: rgba(255,255,255,0.5); font-size: 13px; margin-bottom: 4px">优化后的 Prompt</div>
      <div style="color: rgba(255,255,255,0.7); font-size: 14px; line-height: 1.6; background: rgba(255,255,255,0.03); border-radius: 10px; padding: 14px">
        {{ result.optimized_prompt }}
      </div>
    </div>
  </div>
</template>
