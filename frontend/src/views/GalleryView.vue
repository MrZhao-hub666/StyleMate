<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '../stores/app'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const store = useAppStore()
const uploading = ref(false)
const hoveredId = ref(null)
let _uploadingCount = 0

onMounted(() => store.loadGallery())
onUnmounted(() => clearInterval(_pollTimer))

async function upload(file) {
  _uploadingCount++
  uploading.value = true
  try {
    await api.uploadGallery(file.raw, 'portrait')
  } catch { ElMessage.error(`上传失败: ${file.name}`) }
  finally {
    _uploadingCount--
    if (_uploadingCount <= 0) {
      _uploadingCount = 0
      uploading.value = false
      ElMessage.success('上传完成，后台分析中…')
      await store.loadGallery()
      // 等待后台分析完成，最多轮询 15 次 × 2s = 30s
      pollAnalysis()
    }
  }
}

let _pollTimer = null
async function pollAnalysis() {
  clearInterval(_pollTimer)
  let tries = 0
  _pollTimer = setInterval(async () => {
    tries++
    await store.loadGallery()
    const allDone = store.gallery.every(img => img.analyzed !== false)
    if (allDone || tries >= 15) {
      clearInterval(_pollTimer)
    }
  }, 2000)
}

async function remove(id) {
  try {
    await ElMessageBox.confirm('确认删除？', '提示', { confirmButtonText: '删除', cancelButtonText: '取消' })
    await api.deleteGallery(id)
    await store.loadGallery()
    ElMessage.success('已删除')
  } catch {}
}
</script>

<template>
  <div style="max-width: 1200px; margin: 0 auto">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px">
      <h2 style="color: rgba(255,255,255,0.9); margin: 0; font-size: 22px">个人相册</h2>
      <el-upload :auto-upload="false" :show-file-list="false" accept="image/*"
        multiple :on-change="upload" :disabled="uploading">
        <el-button type="primary" :loading="uploading">
          {{ uploading ? '上传中...' : '+ 上传照片' }}
        </el-button>
      </el-upload>
    </div>

    <el-empty v-if="!store.gallery.length" description="暂无照片，上传你的照片吧" />

    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px">
      <div v-for="img in store.gallery" :key="img.id"
        style="position: relative; border-radius: 14px; overflow: hidden; aspect-ratio: 3/4;
               background: rgba(255,255,255,0.03); cursor: pointer; group"
        @mouseenter="hoveredId = img.id"
        @mouseleave="hoveredId = null">
        <img :src="img.filepath" style="width: 100%; height: 100%; object-fit: cover" />
        <!-- 分析中遮罩 -->
        <div v-if="!img.analyzed" style="position: absolute; bottom: 8px; left: 8px; background: rgba(167,139,250,0.85);
                    color: #fff; font-size: 12px; padding: 3px 10px; border-radius: 6px; backdrop-filter: blur(4px)">
          分析中…
        </div>
        <div v-show="hoveredId === img.id" style="position: absolute; inset: 0; background: rgba(0,0,0,0.5);
                    display: flex; align-items: center; justify-content: center;
                    transition: opacity 0.2s; gap: 8px">
          <el-button size="small" circle @click="remove(img.id)"><el-icon><Delete /></el-icon></el-button>
        </div>
      </div>
    </div>
  </div>
</template>
