import axios from 'axios'

const api = axios.create({
  baseURL: '',
  timeout: 120000,
})

// 边端分析服务（本地 localhost:9001，不走 Vite 代理）
const edgeAxios = axios.create({
  baseURL: 'http://localhost:9001',
  timeout: 60000,
})

export default {
  // 边端上传
  quickUpload: (data) => api.post('/api/edge/upload/quick', data),
  updateClothingAttributes: (id, data) => api.put(`/api/edge/upload/${id}`, data),

  // 边端分析服务
  analyzeImage: (imageBase64, zone = 'single_garment') =>
    edgeAxios.post('/analyze', { image_base64: imageBase64, zone }),

  // 衣橱
  getWardrobe: () => api.get('/api/wardrobe'),
  deleteClothing: (id) => api.delete(`/api/wardrobe/${id}`),

  // 搭配推荐
  recommend: (data) => api.post('/api/recommend', data),

  // 穿搭评价
  review: (data) => api.post('/api/review', data),

  // 创意生成
  generatePortrait: (data) => api.post('/api/portrait/generate', data, { timeout: 120000 }),
  savePortrait: (data) => api.post('/api/portrait/save', data),

  // 个人系统
  getProfile: () => api.get('/api/profile'),
  updateProfile: (data) => api.put('/api/profile', data),
  uploadAvatar: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/api/profile/avatar', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  getGallery: () => api.get('/api/profile/gallery'),
  uploadGallery: (file, tag = 'portrait') => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post(`/api/profile/gallery/upload?tag=${tag}`, fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  deleteGallery: (id) => api.delete(`/api/profile/gallery/${id}`),
}
