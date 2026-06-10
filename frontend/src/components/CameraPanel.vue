<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'

const emit = defineEmits(['capture'])
const videoRef = ref(null)
const canvasRef = ref(null)
let stream = null
const captured = ref(null)

async function startCamera() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 1280, height: 720, facingMode: 'user' }
    })
    if (videoRef.value) {
      videoRef.value.srcObject = stream
    }
  } catch {
    ElMessage.error('无法访问摄像头')
  }
}

function capture() {
  if (!videoRef.value || !canvasRef.value) return
  const canvas = canvasRef.value
  canvas.width = videoRef.value.videoWidth
  canvas.height = videoRef.value.videoHeight
  const ctx = canvas.getContext('2d')
  ctx.drawImage(videoRef.value, 0, 0)
  const base64 = canvas.toDataURL('image/jpeg', 0.85)
  captured.value = base64
  emit('capture', { crop_base64: base64, zone: 'full', has_person: true })
}

function stopCamera() {
  if (stream) {
    stream.getTracks().forEach(t => t.stop())
    stream = null
  }
  emit('close')
}

onMounted(startCamera)
onUnmounted(stopCamera)
</script>

<template>
  <div style="margin-bottom: 16px">
    <div style="position: relative; display: inline-block; border-radius: 8px; overflow: hidden">
      <video ref="videoRef" autoplay playsinline style="width: 400px; background: #000" />
      <canvas ref="canvasRef" style="display: none" />
    </div>
    <div style="margin-top: 10px">
      <el-button type="primary" @click="capture">拍照采集</el-button>
      <el-button @click="stopCamera">关闭摄像头</el-button>
    </div>
    <el-image v-if="captured" :src="captured" style="width: 200px; margin-top: 10px; border-radius: 8px" fit="cover" />
  </div>
</template>
