<template>
  <view class="container">
    <view class="header">
      <image class="logo" src="/static/logo.png" mode="aspectFit"></image>
      <text class="title">青少年无人机大赛</text>
      <text class="subtitle">报名、查询、证书一站式完成</text>
    </view>
    
    <view class="quick-actions">
      <view class="action-item" @click="goToRegister">
        <image class="action-icon" :src="iconSvg('edit')" mode="aspectFit"></image>
        <text class="action-title">立即报名</text>
        <text class="action-desc">填写报名信息</text>
      </view>

      <view class="action-item" @click="goToApplicationQuery">
        <image class="action-icon" :src="iconSvg('search')" mode="aspectFit"></image>
        <text class="action-title">报名查询</text>
        <text class="action-desc">按手机号查询</text>
      </view>
      
      <view class="action-item" @click="goToMyApplications">
        <image class="action-icon" :src="iconSvg('trophy')" mode="aspectFit"></image>
        <text class="action-title">获奖查询</text>
        <text class="action-desc">按参赛号查询</text>
      </view>

      <view class="action-item" @click="goToCoachAward">
        <image class="action-icon" :src="iconSvg('badge')" mode="aspectFit"></image>
        <text class="action-title">优秀辅导员</text>
        <text class="action-desc">证书查询</text>
      </view>
    </view>
    
    <view class="info-section">
      <view class="info-title">
        <text class="info-title-text">竞赛项目</text>
      </view>
      <view class="project-list">
        <view 
          v-for="(projects, category) in competitionRules" 
          :key="category"
          class="project-category"
        >
          <text class="category-name">{{ category }}</text>
          <view class="task-list">
            <view 
              v-for="(rule, task) in projects" 
              :key="task"
              class="task-item"
            >
              <text class="task-name">{{ task }}</text>
              <text class="task-info">{{ rule.participant_count }}人 | {{ rule.allowed_levels.join('、') }}</text>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import * as requestApi from '../../utils/request'
import auth from '../../utils/auth'

const request = requestApi && requestApi.default ? requestApi.default : requestApi

export default {
  data() {
    return {
      competitionRules: {}
    }
  },
  
  onLoad() {
    this.loadCompetitionRules()
  },

  async onShow() {
    await auth.requireUserLoginOrRedirect('/pages/index/index')
  },
  
  methods: {
    iconSvg(name) {
      const stroke = '#1f4b99'
      const stroke2 = '#0ea5a4'
      const map = {
        edit: `<svg xmlns="http://www.w3.org/2000/svg" width="72" height="72" viewBox="0 0 24 24" fill="none" stroke="${stroke}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>`,
        search: `<svg xmlns="http://www.w3.org/2000/svg" width="72" height="72" viewBox="0 0 24 24" fill="none" stroke="${stroke}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.2-3.2"/></svg>`,
        trophy: `<svg xmlns="http://www.w3.org/2000/svg" width="72" height="72" viewBox="0 0 24 24" fill="none" stroke="${stroke}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M8 21h8"/><path d="M12 17v4"/><path d="M7 4h10v5a5 5 0 0 1-10 0Z"/><path d="M5 5H3v2a4 4 0 0 0 4 4"/><path d="M19 5h2v2a4 4 0 0 1-4 4"/></svg>`,
        badge: `<svg xmlns="http://www.w3.org/2000/svg" width="72" height="72" viewBox="0 0 24 24" fill="none" stroke="${stroke2}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l2.4 4.8 5.3.8-3.9 3.8.9 5.3L12 14.8 7.3 16.7l.9-5.3L4.3 7.6l5.3-.8Z"/><path d="M8.2 15.2 7 22l5-2 5 2-1.2-6.8"/></svg>`
      }
      const svg = map[name] || map.search
      return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
    },
    async loadCompetitionRules() {
      try {
        const data = await request.get('/api/competition-rules')
        if (data.success) {
          this.competitionRules = data.data
        }
      } catch (error) {
        console.error('加载竞赛规则失败:', error)
      }
    },
    
    goToRegister() {
      uni.switchTab({
        url: '/pages/register/register'
      })
    },
    
    goToMyApplications() {
      uni.switchTab({
        url: '/pages/my-applications/my-applications'
      })
    },

    goToApplicationQuery() {
      uni.navigateTo({
        url: '/pages/application-query/application-query'
      })
    },

    goToCoachAward() {
      uni.navigateTo({
        url: '/pages/coach-award/coach-award'
      })
    }
  }
}
</script>

<style scoped>
.container {
  padding: 20px;
  background-color: var(--bg);
  min-height: 100vh;
}

.header {
  text-align: center;
  padding: 40px 0;
  background: linear-gradient(135deg, rgba(31, 75, 153, 1) 0%, rgba(14, 165, 164, 1) 100%);
  border-radius: 16px;
  margin-bottom: 30px;
  color: white;
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.18);
}

.logo {
  width: 80px;
  height: 80px;
  margin-bottom: 20px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.2);
}

.title {
  display: block;
  font-size: 28px;
  margin-bottom: 10px;
  font-weight: 700;
  letter-spacing: 1px;
}

.subtitle {
  display: block;
  font-size: 13px;
  opacity: 0.9;
}

.quick-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 20px;
}

.action-item {
  background-color: var(--card);
  padding: 18px 12px;
  border-radius: 12px;
  text-align: center;
  box-shadow: var(--shadow);
}

.action-icon {
  width: 40px;
  height: 40px;
  margin: 0 auto 10px;
}

.action-title {
  display: block;
  font-size: 18px;
  font-weight: bold;
  color: var(--text);
  margin-bottom: 5px;
}

.action-desc {
  display: block;
  font-size: 14px;
  color: var(--muted);
}

.info-section {
  background-color: var(--card);
  border-radius: 12px;
  padding: 20px;
  box-shadow: var(--shadow);
}

.info-title {
  border-bottom: 1px solid rgba(15, 23, 42, 0.1);
  padding-bottom: 10px;
  margin-bottom: 20px;
}

.info-title-text {
  font-size: 20px;
  font-weight: bold;
  color: var(--text);
}

.project-category {
  margin-bottom: 25px;
}

.category-name {
  display: block;
  font-size: 18px;
  font-weight: bold;
  color: var(--brand);
  margin-bottom: 15px;
}

.task-list {
  padding-left: 15px;
}

.task-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 15px;
  background-color: rgba(15, 23, 42, 0.04);
  border-radius: 8px;
  margin-bottom: 10px;
}

.task-name {
  font-size: 16px;
  color: var(--text);
  font-weight: 500;
}

.task-info {
  font-size: 14px;
  color: var(--muted);
}
</style>
