import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'

export const useAppStore = defineStore('app', () => {
  const profile = ref({})
  const gallery = ref([])

  async function loadProfile() {
    try { const r = await api.getProfile(); profile.value = r.data } catch (e) { console.warn('加载用户资料失败:', e.message) }
  }
  async function loadGallery() {
    try { const r = await api.getGallery(); gallery.value = r.data } catch (e) { console.warn('加载相册失败:', e.message) }
  }

  return { profile, gallery, loadProfile, loadGallery }
})
