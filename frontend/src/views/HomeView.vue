<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '../stores/app'

const router = useRouter()
const store = useAppStore()
const hoveredCard = ref('')

const cards = [
  { id: 'recommend', path: '/recommend', icon: 'MagicStick', title: 'AI 搭配推荐',
    desc: '结合天气、场合、体型，智能推荐最佳穿搭方案',
    gradient: 'linear-gradient(135deg, #a78bfa 0%, #8b5cf6 50%, #c084fc 100%)',
    shadow: 'rgba(167,139,250,0.4)' },
  { id: 'review', path: '/review', icon: 'Star', title: 'AI 穿搭评价',
    desc: '穿上后拍照上传，AI 打分并给出专业改进建议',
    gradient: 'linear-gradient(135deg, #f472b6 0%, #ec4899 50%, #fda4af 100%)',
    shadow: 'rgba(244,114,182,0.4)' },
  { id: 'portrait', path: '/portrait', icon: 'BrushFilled', title: 'AI 创意写真',
    desc: '拍一张照片，AI 为你生成各种风格的时尚大片',
    gradient: 'linear-gradient(135deg, #38bdf8 0%, #0ea5e9 50%, #7dd3fc 100%)',
    shadow: 'rgba(56,189,248,0.4)' },
  { id: 'wardrobe', path: '/wardrobe', icon: 'Box', title: '数字衣橱',
    desc: '拍照或上传，管理所有衣物，构建专属数字衣橱',
    gradient: 'linear-gradient(135deg, #34d399 0%, #10b981 50%, #6ee7b7 100%)',
    shadow: 'rgba(52,211,153,0.4)' },
]

const bottomCards = [
  { path: '/profile', icon: 'UserFilled', label: '个人资料', color: '#f472b6' },
  { path: '/gallery', icon: 'PictureFilled', label: '个人相册', color: '#38bdf8' },
]
</script>

<template>
  <div class="home">
    <!-- 欢迎区 -->
    <section class="hero">
      <div class="hero-badge">
        <span class="dot"></span> 边云协同 · AI 驱动
      </div>
      <h1 class="hero-title">
        Style<span>Mate</span>
      </h1>
      <p class="hero-sub">
        {{ store.profile.nickname ? `${store.profile.nickname}，` : '' }}你的 AI 智能穿搭顾问。
        基于 YOLO 边缘检测 + 云端大模型推理，为你打造专属穿搭体验。
      </p>
    </section>

    <!-- 主功能卡片 -->
    <section class="cards-grid">
      <div v-for="card in cards" :key="card.id"
        class="feature-card"
        :class="{ 'is-hovered': hoveredCard === card.id }"
        @mouseenter="hoveredCard = card.id"
        @mouseleave="hoveredCard = ''"
        @click="router.push(card.path)"
        :style="{ '--card-gradient': card.gradient, '--card-shadow': card.shadow }">
        <div class="card-glow" :style="{ background: card.gradient }"></div>
        <div class="card-icon-wrap" :style="{ background: card.gradient }">
          <el-icon size="22" color="#fff"><component :is="card.icon" /></el-icon>
        </div>
        <h3>{{ card.title }}</h3>
        <p>{{ card.desc }}</p>
        <span class="card-arrow">→</span>
      </div>
    </section>

    <!-- 底部功能 -->
    <section class="bottom-row">
      <div v-for="c in bottomCards" :key="c.path" class="bottom-card" @click="router.push(c.path)"
        :style="{ '--bc': c.color }">
        <el-icon size="20"><component :is="c.icon" /></el-icon>
        <span>{{ c.label }}</span>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home { padding-top: 10px; }

/* === Hero === */
.hero { text-align: center; margin-bottom: 52px; }
.hero-badge {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 6px 18px; border-radius: 40px;
  background: rgba(167,139,250,0.1); border: 1px solid rgba(167,139,250,0.2);
  color: #c4b5fd; font-size: 13px; font-weight: 500; margin-bottom: 24px;
}
.dot { width: 6px; height: 6px; border-radius: 50%; background: #a78bfa; box-shadow: 0 0 8px #a78bfa; }
.hero-title {
  font-size: 56px; font-weight: 900; margin: 0 0 16px;
  background: linear-gradient(135deg, #c4b5fd 0%, #e9d5ff 30%, #fbcfe8 60%, #a78bfa 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  letter-spacing: -1px;
}
.hero-sub {
  max-width: 520px; margin: 0 auto;
  color: rgba(255,255,255,0.35); font-size: 15px; line-height: 1.7;
}

/* === Feature Cards === */
.cards-grid {
  display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;
  max-width: 900px; margin: 0 auto;
}
.feature-card {
  position: relative; padding: 32px 28px;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 24px; cursor: pointer;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}
.card-glow {
  position: absolute; top: -50%; right: -30%;
  width: 200px; height: 200px; border-radius: 50%;
  filter: blur(60px); opacity: 0;
  transition: opacity 0.5s;
}
.feature-card.is-hovered {
  border-color: rgba(255,255,255,0.1);
  transform: translateY(-4px);
  box-shadow: 0 16px 48px -12px var(--card-shadow);
}
.feature-card.is-hovered .card-glow { opacity: 0.3; }
.feature-card.is-hovered .card-arrow { opacity: 1; transform: translateX(0); }

.card-icon-wrap {
  width: 46px; height: 46px; border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 16px; position: relative; z-index: 1;
  transition: transform 0.3s;
}
.feature-card.is-hovered .card-icon-wrap { transform: scale(1.08); }
.feature-card h3 {
  color: rgba(255,255,255,0.9); font-size: 17px; font-weight: 700;
  margin: 0 0 6px; position: relative; z-index: 1;
}
.feature-card p {
  color: rgba(255,255,255,0.35); font-size: 14px; margin: 0; line-height: 1.5;
  position: relative; z-index: 1;
}
.card-arrow {
  position: absolute; right: 24px; bottom: 24px;
  font-size: 18px; color: rgba(255,255,255,0.3);
  opacity: 0; transform: translateX(-8px);
  transition: all 0.3s;
}

/* === Bottom Row === */
.bottom-row {
  display: flex; gap: 14px; justify-content: center; margin-top: 28px;
}
.bottom-card {
  display: flex; align-items: center; gap: 8px;
  padding: 12px 22px; border-radius: 40px;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.05);
  color: rgba(255,255,255,0.4); font-size: 14px; cursor: pointer;
  transition: all 0.3s;
}
.bottom-card:hover {
  background: rgba(255,255,255,0.05);
  border-color: var(--bc);
  color: var(--bc);
  box-shadow: 0 0 20px color-mix(in srgb, var(--bc) 15%, transparent);
}
</style>
