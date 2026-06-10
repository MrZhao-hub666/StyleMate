<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAppStore } from './stores/app'

const router = useRouter()
const route = useRoute()
const store = useAppStore()
const hoveredNav = ref('')

onMounted(async () => {
  await store.loadProfile()
  await store.loadGallery()
})

const navItems = [
  { path: '/', label: '首页', icon: 'HomeFilled', color: '#a78bfa' },
  { path: '/profile', label: '个人资料', icon: 'UserFilled', color: '#f472b6' },
  { path: '/gallery', label: '个人相册', icon: 'PictureFilled', color: '#38bdf8' },
  { path: '/wardrobe', label: '个人衣橱', icon: 'Box', color: '#34d399' },
  { path: '/recommend', label: '搭配推荐', icon: 'MagicStick', color: '#a78bfa' },
  { path: '/review', label: '穿搭评价', icon: 'Star', color: '#f472b6' },
  { path: '/portrait', label: '创意生成', icon: 'BrushFilled', color: '#38bdf8' },
]
</script>

<template>
  <div class="app-shell">
    <!-- 背景凝虹炫彩 -->
    <div class="bg-glow bg-glow-1"></div>
    <div class="bg-glow bg-glow-2"></div>
    <div class="bg-glow bg-glow-3"></div>
    <div class="bg-glow bg-glow-4"></div>
    <div class="bg-glow bg-glow-5"></div>

    <!-- 顶栏 -->
    <header class="topbar">
      <div class="topbar-inner">
        <span class="brand" @click="router.push('/')">StyleMate</span>
        <nav class="nav-links">
          <router-link v-for="item in navItems" :key="item.path" :to="item.path"
            class="nav-item"
            :class="{ active: route.path === item.path }"
            @mouseenter="hoveredNav = item.path"
            @mouseleave="hoveredNav = ''"
            :style="{
              '--nav-color': item.color,
              color: (route.path === item.path || hoveredNav === item.path) ? item.color : undefined,
              background: (route.path === item.path || hoveredNav === item.path)
                ? `rgba(${parseInt(item.color.slice(1,3),16)},${parseInt(item.color.slice(3,5),16)},${parseInt(item.color.slice(5,7),16)},0.12)` : undefined,
              borderColor: hoveredNav === item.path ? item.color : undefined,
            }">
            <el-icon><component :is="item.icon" /></el-icon>
            <span>{{ item.label }}</span>
          </router-link>
        </nav>
        <router-link to="/profile" class="user-badge">
          <div class="avatar-circle">
            {{ store.profile.nickname?.[0] || 'U' }}
          </div>
          <span>{{ store.profile.nickname || '用户' }}</span>
        </router-link>
      </div>
    </header>

    <!-- 主体 -->
    <main class="main-area">
      <router-view />
    </main>
  </div>
</template>

<style>
/* === 全局重置 === */
html, body, #app { margin: 0; padding: 0; min-height: 100vh; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
* { box-sizing: border-box; }

/* === 背景凝虹炫彩 === */
.app-shell {
  position: relative;
  min-height: 100vh;
  background: #08080f;
  overflow: hidden;
}
.bg-glow {
  position: fixed;
  border-radius: 50%;
  filter: blur(140px);
  pointer-events: none;
  z-index: 0;
  animation: float 18s ease-in-out infinite;
}
.bg-glow-1 {
  width: 650px; height: 650px;
  background: radial-gradient(circle at 40% 40%, rgba(139,92,246,0.35), rgba(236,72,153,0.25), transparent 70%);
  top: -10%; left: -8%; animation-delay: 0s;
}
.bg-glow-2 {
  width: 550px; height: 550px;
  background: radial-gradient(circle at 60% 50%, rgba(59,130,246,0.3), rgba(6,182,212,0.2), transparent 70%);
  top: 40%; right: -5%; animation-delay: -6s;
}
.bg-glow-3 {
  width: 500px; height: 500px;
  background: radial-gradient(circle at 50% 60%, rgba(244,114,182,0.3), rgba(168,85,247,0.2), transparent 70%);
  bottom: -12%; left: 25%; animation-delay: -12s;
}
.bg-glow-4 {
  width: 400px; height: 400px;
  background: radial-gradient(circle at 30% 30%, rgba(52,211,153,0.2), rgba(16,185,129,0.15), transparent 70%);
  top: 30%; left: 15%; animation-delay: -9s;
}
.bg-glow-5 {
  width: 350px; height: 350px;
  background: radial-gradient(circle at 70% 70%, rgba(250,204,21,0.15), rgba(251,146,60,0.12), transparent 70%);
  bottom: 20%; right: 20%; animation-delay: -3s;
}
/* 凝虹雾化底层 */
.app-shell::before {
  content: '';
  position: fixed; inset: 0;
  background:
    radial-gradient(ellipse 120% 80% at 20% 30%, rgba(139,92,246,0.06) 0%, transparent 50%),
    radial-gradient(ellipse 100% 90% at 80% 60%, rgba(236,72,153,0.05) 0%, transparent 50%),
    radial-gradient(ellipse 90% 70% at 50% 80%, rgba(59,130,246,0.05) 0%, transparent 50%),
    linear-gradient(180deg, rgba(139,92,246,0.03) 0%, rgba(236,72,153,0.02) 50%, rgba(59,130,246,0.03) 100%);
  pointer-events: none; z-index: 0;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1) rotate(0deg); }
  25% { transform: translate(50px, -40px) scale(1.12) rotate(3deg); }
  50% { transform: translate(-30px, 30px) scale(0.92) rotate(-2deg); }
  75% { transform: translate(20px, -15px) scale(1.05) rotate(1deg); }
}

/* === 顶栏 === */
.topbar {
  position: sticky; top: 0; z-index: 100;
  background: rgba(7,7,15,0.7);
  backdrop-filter: blur(24px) saturate(180%);
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.topbar-inner {
  max-width: 1400px; margin: 0 auto; height: 64px;
  display: flex; align-items: center; padding: 0 32px;
}
.brand {
  font-size: 24px; font-weight: 800; cursor: pointer;
  background: linear-gradient(135deg, #c4b5fd, #f9a8d4);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  margin-right: 48px; transition: filter 0.3s;
}
.brand:hover { filter: brightness(1.3); }

.nav-links { display: flex; gap: 2px; flex: 1; }
.nav-item {
  display: flex; align-items: center; gap: 5px;
  padding: 8px 14px; border-radius: 12px; font-size: 13.5px; font-weight: 500;
  text-decoration: none; color: rgba(255,255,255,0.45);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid transparent; position: relative;
}
.nav-item:hover {
  color: var(--nav-color);
  background: color-mix(in srgb, var(--nav-color) 12%, transparent);
  border-color: color-mix(in srgb, var(--nav-color) 25%, transparent);
  box-shadow: 0 0 20px color-mix(in srgb, var(--nav-color) 15%, transparent);
  transform: translateY(-1px);
}
.nav-item.active {
  color: var(--nav-color);
  background: color-mix(in srgb, var(--nav-color) 15%, transparent);
  box-shadow: 0 0 16px color-mix(in srgb, var(--nav-color) 10%, transparent);
}
.nav-item .el-icon { font-size: 16px; }

.user-badge {
  display: flex; align-items: center; gap: 10px; text-decoration: none;
  padding: 4px 12px 4px 4px; border-radius: 28px;
  transition: background 0.2s;
}
.user-badge:hover { background: rgba(255,255,255,0.06); }
.avatar-circle {
  width: 34px; height: 34px; border-radius: 50%;
  background: linear-gradient(135deg, #a78bfa, #f472b6);
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-weight: 700; font-size: 13px;
}
.user-badge span { color: rgba(255,255,255,0.65); font-size: 14px; }

.main-area {
  position: relative; z-index: 1;
  padding: 32px; max-width: 1280px; margin: 0 auto;
}

/* === 滚动条 === */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.15); }

/* === Element Plus 暗色全面覆写 === */
.el-card {
  background: rgba(255,255,255,0.025) !important;
  border: 1px solid rgba(255,255,255,0.06) !important;
  border-radius: 18px !important;
  backdrop-filter: blur(10px);
  transition: all 0.3s;
}
.el-card:hover { border-color: rgba(167,139,250,0.25) !important; box-shadow: 0 8px 32px rgba(167,139,250,0.08); }

/* --- 输入框 --- */
.el-input__wrapper {
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
  border-radius: 12px !important; box-shadow: none !important; transition: all 0.2s;
}
.el-input__wrapper:hover { border-color: rgba(167,139,250,0.3) !important; }
.el-input__wrapper.is-focus { border-color: #a78bfa !important; box-shadow: 0 0 0 2px rgba(167,139,250,0.15) !important; }
.el-input__inner { color: rgba(255,255,255,0.85) !important; }
.el-input__inner::placeholder { color: rgba(255,255,255,0.25) !important; }

/* --- 数字输入框上下箭头 --- */
.el-input-number__decrease, .el-input-number__increase {
  background: rgba(255,255,255,0.04) !important;
  border-color: rgba(255,255,255,0.06) !important; border-radius: 0 !important;
}
.el-input-number__decrease:hover, .el-input-number__increase:hover {
  color: #a78bfa !important; background: rgba(167,139,250,0.1) !important;
}
.el-input-number__decrease .el-icon, .el-input-number__increase .el-icon {
  color: rgba(255,255,255,0.4) !important;
}

/* --- 下拉选择框（Element Plus 2.x 使用 el-select__wrapper） --- */
.el-select {
  --el-select-border-color-hover: rgba(167,139,250,0.3);
  --el-select-input-focus-border-color: #a78bfa;
}
.el-select__wrapper {
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
  border-radius: 12px !important;
  box-shadow: none !important;
  transition: all 0.2s;
}
.el-select__wrapper:hover { border-color: rgba(167,139,250,0.3) !important; }
.el-select__wrapper.is-focus {
  border-color: #a78bfa !important;
  box-shadow: 0 0 0 2px rgba(167,139,250,0.15) !important;
}
.el-select__placeholder { color: rgba(255,255,255,0.25) !important; }
.el-select__placeholder.is-transitied { color: rgba(255,255,255,0.25) !important; }
.el-select__selected-item { color: rgba(255,255,255,0.85) !important; }
.el-select__input { color: rgba(255,255,255,0.85) !important; }
.el-select__caret { color: rgba(255,255,255,0.35) !important; }
/* 选中值的关闭按钮 */
.el-select__tags .el-tag .el-tag__close { color: rgba(255,255,255,0.5) !important; }
.el-select__tags .el-tag .el-tag__close:hover { color: #a78bfa !important; background: rgba(167,139,250,0.15) !important; }
/* 多选标签 */
.el-select__tags .el-tag {
  background: rgba(167,139,250,0.12) !important;
  border-color: rgba(167,139,250,0.25) !important;
  color: #a78bfa !important;
  border-radius: 6px !important;
}

/* 下拉面板 */
.el-select-dropdown {
  background: #1c1c30 !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
  border-radius: 12px !important;
  box-shadow: 0 12px 40px rgba(0,0,0,0.5) !important;
}
.el-select-dropdown__wrap {
  background: #1c1c30 !important;
  max-height: 274px;
}
.el-select-dropdown__list { padding: 4px !important; }
.el-select-dropdown__item {
  height: auto !important; line-height: 1.4 !important;
  padding: 9px 12px !important; margin: 1px 6px !important;
  color: rgba(255,255,255,0.65) !important;
  border-radius: 8px; font-size: 14px;
  transition: all 0.15s;
}
.el-select-dropdown__item.is-selected {
  color: #a78bfa !important; font-weight: 600 !important;
  background: rgba(167,139,250,0.1) !important;
}
.el-select-dropdown__item.is-hovering,
.el-select-dropdown__item.hover,
.el-select-dropdown__item:hover {
  background: rgba(167,139,250,0.12) !important;
  color: rgba(255,255,255,0.9) !important;
}
.el-select__popper .el-popper__arrow::before {
  background: #1c1c30 !important;
  border-color: rgba(255,255,255,0.08) !important;
}
.el-select-dropdown__empty { color: rgba(255,255,255,0.3) !important; padding: 12px !important; }

/* --- 日期选择器 --- */
.el-picker-panel {
  background: #1c1c30 !important; border: 1px solid rgba(255,255,255,0.08) !important;
  border-radius: 14px !important; box-shadow: 0 12px 40px rgba(0,0,0,0.5) !important;
}
.el-date-picker__header-label { color: rgba(255,255,255,0.7) !important; }
.el-date-picker__header-label:hover { color: #a78bfa !important; }
.el-date-table td { color: rgba(255,255,255,0.5) !important; }
.el-date-table td.available:hover { color: #a78bfa !important; }
.el-date-table td.current:not(.disabled) .el-date-table-cell__text {
  background: #a78bfa !important; color: #fff !important; border-radius: 8px !important;
}
.el-date-table td.today .el-date-table-cell__text { color: #a78bfa !important; font-weight: 700 !important; }
.el-month-table td .cell, .el-year-table td .cell { color: rgba(255,255,255,0.5) !important; }
.el-month-table td .cell:hover, .el-year-table td .cell:hover { color: #a78bfa !important; }
.el-picker-panel__icon-btn { color: rgba(255,255,255,0.4) !important; }
.el-picker-panel__icon-btn:hover { color: #a78bfa !important; }

/* --- 按钮 --- */
.el-button--primary {
  background: linear-gradient(135deg, #a78bfa, #8b5cf6) !important;
  border: none !important; border-radius: 12px !important; font-weight: 600 !important;
  transition: all 0.3s !important;
}
.el-button--primary:hover { transform: translateY(-1px); box-shadow: 0 6px 24px rgba(139,92,246,0.35) !important; }
.el-button--primary:active { transform: translateY(0); }
.el-button:not(.el-button--primary) {
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
  border-radius: 12px !important; color: rgba(255,255,255,0.7) !important; transition: all 0.2s;
}
.el-button:not(.el-button--primary):hover {
  border-color: rgba(167,139,250,0.4) !important;
  color: #a78bfa !important; background: rgba(167,139,250,0.06) !important;
}

/* --- 其他 --- */
.el-tag { border-radius: 8px !important; border: none !important; font-weight: 500 !important; }
.el-radio-button__inner {
  background: rgba(255,255,255,0.03) !important;
  border-color: rgba(255,255,255,0.1) !important; color: rgba(255,255,255,0.5) !important; transition: all 0.2s;
}
.el-radio-button__original-radio:checked + .el-radio-button__inner {
  background: rgba(167,139,250,0.15) !important;
  border-color: #a78bfa !important; color: #a78bfa !important; box-shadow: none !important;
}
.el-alert {
  background: rgba(167,139,250,0.1) !important;
  border: 1px solid rgba(167,139,250,0.15) !important; border-radius: 12px !important;
}
.el-empty__description { color: rgba(255,255,255,0.3) !important; }
.el-popper.is-light { background: #1c1c30 !important; border-color: rgba(255,255,255,0.1) !important; }

/* --- 文本域 --- */
.el-textarea__inner {
  background: rgba(255,255,255,0.04) !important;
  border-color: rgba(255,255,255,0.08) !important;
  border-radius: 12px !important; color: rgba(255,255,255,0.85) !important;
  box-shadow: none !important; transition: all 0.2s;
}
.el-textarea__inner:hover { border-color: rgba(167,139,250,0.3) !important; }
.el-textarea__inner:focus { border-color: #a78bfa !important; box-shadow: 0 0 0 2px rgba(167,139,250,0.15) !important; }
.el-textarea__inner::placeholder { color: rgba(255,255,255,0.25) !important; }

/* --- 上传组件 --- */
.el-upload-dragger {
  background: rgba(255,255,255,0.03) !important;
  border: 1px dashed rgba(255,255,255,0.1) !important;
  border-radius: 12px !important;
}
.el-upload-dragger:hover { border-color: rgba(167,139,250,0.4) !important; }

/* --- 消息提示 --- */
.el-message {
  background: #1c1c30 !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
  border-radius: 12px !important; box-shadow: 0 8px 24px rgba(0,0,0,0.4) !important;
}
.el-message .el-message__content { color: rgba(255,255,255,0.85) !important; }

/* --- 消息弹窗 --- */
.el-message-box {
  background: #1c1c30 !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
  border-radius: 16px !important;
}
.el-message-box__title { color: rgba(255,255,255,0.85) !important; }
.el-message-box__message { color: rgba(255,255,255,0.6) !important; }

/* --- 加载遮罩 --- */
.el-loading-mask {
  background: rgba(8,8,15,0.8) !important;
  backdrop-filter: blur(4px);
}

/* --- 表单标签 --- */
.el-form-item__label { color: rgba(255,255,255,0.6) !important; }

/* --- 分割线 --- */
.el-divider__text { background: transparent !important; color: rgba(255,255,255,0.35) !important; }

/* --- 空状态 --- */
.el-empty__image svg { filter: brightness(0.5); }
</style>
