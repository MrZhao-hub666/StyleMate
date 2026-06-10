<script setup>
import { ref, onMounted } from 'vue'
import { useAppStore } from '../stores/app'
import { ElMessage } from 'element-plus'
import api from '../api'

const store = useAppStore()
const form = ref({ nickname: '', gender: '未设置', birthdate: '', height: null, weight: null, city: '北京' })
const saving = ref(false)
const avatarInput = ref(null)

onMounted(async () => {
  await store.loadProfile()
  const p = store.profile
  form.value = {
    nickname: p.nickname || '',
    gender: p.gender || '未设置',
    birthdate: p.birthdate || '',
    height: p.height || null,
    weight: p.weight || null,
    city: p.city || '北京',
  }
})

async function save() {
  saving.value = true
  try {
    await api.updateProfile({
      nickname: form.value.nickname,
      gender: form.value.gender,
      birthdate: form.value.birthdate || undefined,
      height: form.value.height || undefined,
      weight: form.value.weight || undefined,
      city: form.value.city,
    })
    ElMessage.success('保存成功')
    await store.loadProfile()
  } catch { ElMessage.error('保存失败') }
  finally { saving.value = false }
}

async function handleAvatar(event) {
  const file = event.target.files?.[0]
  if (!file) return
  try {
    await api.uploadAvatar(file)
    ElMessage.success('头像已更新')
    await store.loadProfile()
  } catch { ElMessage.error('上传失败') }
}

const FIELD_STYLE = { display: 'flex', flexDirection: 'column', gap: '6px' }
</script>

<template>
  <div style="max-width: 720px; margin: 0 auto">
    <!-- 头像区 -->
    <div style="text-align: center; margin-bottom: 36px">
      <div style="width: 88px; height: 88px; border-radius: 50%;
                  background: linear-gradient(135deg, #a78bfa, #f472b6); margin: 0 auto 16px;
                  display: flex; align-items: center; justify-content: center;
                  overflow: hidden; cursor: pointer" @click="avatarInput.click()">
        <img v-if="store.profile.avatar_path"
          :src="store.profile.avatar_path"
          style="width: 100%; height: 100%; object-fit: cover" />
        <span v-else style="color: #fff; font-size: 32px; font-weight: 700">
          {{ store.profile.nickname?.[0] || 'U' }}
        </span>
      </div>
      <h2 style="color: rgba(255,255,255,0.9); margin: 0 0 4px">{{ store.profile.nickname || '未设置昵称' }}</h2>
      <div style="display: flex; gap: 12px; justify-content: center; color: rgba(255,255,255,0.4); font-size: 13px">
        <span v-if="store.profile.age">{{ store.profile.age }}岁</span>
        <span v-if="store.profile.zodiac">{{ store.profile.zodiac }}</span>
        <span v-if="store.profile.height">{{ store.profile.height }}cm</span>
        <span v-if="store.profile.weight">{{ store.profile.weight }}kg</span>
      </div>
      <input ref="avatarInput" type="file" accept="image/*" hidden @change="handleAvatar" />
    </div>

    <!-- 编辑表单 -->
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px">
      <div :style="FIELD_STYLE">
        <label style="color: rgba(255,255,255,0.5); font-size: 13px">昵称</label>
        <el-input v-model="form.nickname" placeholder="你的昵称" />
      </div>
      <div :style="FIELD_STYLE">
        <label style="color: rgba(255,255,255,0.5); font-size: 13px">性别</label>
        <el-select v-model="form.gender" style="width: 100%">
          <el-option label="男" value="男" />
          <el-option label="女" value="女" />
          <el-option label="未设置" value="未设置" />
        </el-select>
      </div>
      <div :style="FIELD_STYLE">
        <label style="color: rgba(255,255,255,0.5); font-size: 13px">出生日期</label>
        <el-date-picker v-model="form.birthdate" type="date" placeholder="选择日期"
          style="width: 100%" value-format="YYYY-MM-DD" />
      </div>
      <div :style="FIELD_STYLE">
        <label style="color: rgba(255,255,255,0.5); font-size: 13px">常居城市</label>
        <el-input v-model="form.city" placeholder="用于天气查询" />
      </div>
      <div :style="FIELD_STYLE">
        <label style="color: rgba(255,255,255,0.5); font-size: 13px">身高 (cm)</label>
        <el-input v-model.number="form.height" type="number" placeholder="170" />
      </div>
      <div :style="FIELD_STYLE">
        <label style="color: rgba(255,255,255,0.5); font-size: 13px">体重 (kg)</label>
        <el-input v-model.number="form.weight" type="number" placeholder="60" />
      </div>
    </div>

    <div style="margin-top: 28px; text-align: center">
      <el-button type="primary" size="large" @click="save" :loading="saving" style="padding: 12px 48px">
        保存资料
      </el-button>
    </div>
  </div>
</template>
