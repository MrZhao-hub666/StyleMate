<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'
import CameraPanel from '../components/CameraPanel.vue'

const items = ref([])
const showCamera = ref(false)
const uploadingFile = ref(false)
const analyzingIds = ref(new Set())

// zone 中文映射
const ZONE_LABELS = { upper: '上装', lower: '下装', full: '全身', shoes: '鞋履', single_garment: '单品' }
function zoneLabel(zone) { return ZONE_LABELS[zone] || zone }

// 边端分析队列（串行执行，避免并发压垮本地 YOLO）
let _analysisQueue = Promise.resolve()
function enqueueAnalysis(base64, itemId) {
  _analysisQueue = _analysisQueue
    .then(() => _doAnalyze(base64, itemId))
    .catch(() => {})  // 单次失败不阻塞后续
}

async function _doAnalyze(base64, itemId) {
  analyzingIds.value.add(itemId)
  try {
    const result = await api.analyzeImage(base64)
    if (result.data.primary_color_name === '未知') {
      console.warn(`[分析] 边端返回默认值，图片可能解码失败: id=${String(itemId).slice(0,8)}...`)
    } else {
      await api.updateClothingAttributes(itemId, result.data)
    }
  } catch (e) {
    console.error(`[分析] 失败: id=${String(itemId).slice(0,8)}...`, e.message)
  } finally {
    analyzingIds.value.delete(itemId)
    await loadWardrobe()
  }
}

onMounted(loadWardrobe)

async function loadWardrobe() {
  try { const r = await api.getWardrobe(); items.value = r.data } catch {}
}

async function handleCapture(data) {
  uploadingFile.value = true
  try {
    const res = await api.quickUpload({ crop_base64: data.crop_base64, zone: 'single_garment' })
    ElMessage.success('已入库，正在分析…')
    await loadWardrobe()
    showCamera.value = false
    enqueueAnalysis(data.crop_base64, res.data.id)
  } catch { ElMessage.error('上传失败') }
  finally { uploadingFile.value = false }
}

async function handleFileUpload(file) {
  uploadingFile.value = true
  const reader = new FileReader()
  reader.onload = async e => {
    const base64 = e.target.result
    try {
      const res = await api.quickUpload({ crop_base64: base64, zone: 'single_garment' })
      await loadWardrobe()
      enqueueAnalysis(base64, res.data.id)
    } catch { ElMessage.error(`上传失败: ${file.name}`) }
    finally {
      uploadingFile.value = false
    }
  }
  reader.readAsDataURL(file.raw)
}

function isAnalyzing(id) {
  return analyzingIds.value.has(id)
}

async function handleDelete(id) {
  try { await api.deleteClothing(id); ElMessage.success('已删除'); await loadWardrobe() } catch { ElMessage.error('删除失败') }
}
</script>

<template>
  <div style="max-width: 1200px; margin: 0 auto">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px">
      <h2 style="color: rgba(255,255,255,0.9); margin: 0; font-size: 22px">个人衣橱</h2>
      <div style="display: flex; gap: 10px">
        <el-upload :auto-upload="false" :show-file-list="false" accept="image/*"
          multiple :on-change="handleFileUpload" :disabled="uploadingFile">
          <el-button :loading="uploadingFile">📁 上传图片</el-button>
        </el-upload>
        <el-button type="primary" @click="showCamera = !showCamera">
          {{ showCamera ? '关闭摄像头' : '📷 拍照入库' }}
        </el-button>
      </div>
    </div>

    <div v-if="showCamera" style="margin-bottom: 20px; padding: 20px; background: rgba(255,255,255,0.02); border-radius: 16px; border: 1px solid rgba(255,255,255,0.06)">
      <CameraPanel @capture="handleCapture" @close="showCamera = false" />
    </div>

    <el-empty v-if="!items.length && !showCamera" description="衣橱空空，拍照或上传你的第一件衣物" />

    <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px">
      <div v-for="item in items" :key="item.id"
        style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
               border-radius: 14px; overflow: hidden; transition: transform 0.2s; cursor: pointer"
        @mouseenter="e => e.currentTarget.style.transform = 'translateY(-2px)'"
        @mouseleave="e => e.currentTarget.style.transform = ''">
        <div style="height: 160px; overflow: hidden; display: flex; align-items: center; justify-content: center; background: rgba(255,255,255,0.05)">
          <img v-if="item.crop_base64" :src="item.crop_base64" style="width: 100%; height: 100%; object-fit: cover" />
          <div v-else :style="{ background: item.primary_color_hex || '#808080', width: '100%', height: '100%' }" />
        </div>
        <div style="padding: 10px">
          <div style="display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 4px; align-items: center">
            <el-tag v-if="isAnalyzing(item.id)" size="small" type="warning">🔍 分析中…</el-tag>
            <el-tag v-else-if="item.subcategory && item.subcategory !== 'pending_cloud'" size="small" type="success">{{ item.subcategory }}</el-tag>
            <el-tag v-else size="small">{{ item.category }}</el-tag>
            <el-tag size="small" type="info">{{ zoneLabel(item.zone) }}</el-tag>
          </div>
          <div style="color: rgba(255,255,255,0.5); font-size: 12px; line-height: 1.5">
            {{ item.primary_color_name }} · {{ item.pattern }} · {{ item.fabric || '' }} · {{ item.length_category || '' }}
          </div>
          <div v-if="item.neckline && item.neckline !== 'pending_cloud'" style="color: rgba(167,139,250,0.7); font-size: 11px; margin-top: 2px">
            {{ [item.neckline, item.sleeve, item.fit].filter(Boolean).join(' · ') }}
          </div>
          <el-button type="danger" size="small" link @click.stop="handleDelete(item.id)" style="margin-top: 4px">删除</el-button>
        </div>
      </div>
    </div>
  </div>
</template>
