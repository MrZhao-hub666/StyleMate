import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Home', component: () => import('../views/HomeView.vue') },
  { path: '/profile', name: 'Profile', component: () => import('../views/ProfileView.vue') },
  { path: '/gallery', name: 'Gallery', component: () => import('../views/GalleryView.vue') },
  { path: '/wardrobe', name: 'Wardrobe', component: () => import('../views/WardrobeView.vue') },
  { path: '/recommend', name: 'Recommend', component: () => import('../views/RecommendView.vue') },
  { path: '/review', name: 'Review', component: () => import('../views/ReviewView.vue') },
  { path: '/portrait', name: 'Portrait', component: () => import('../views/PortraitView.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

export default createRouter({ history: createWebHistory(), routes })
