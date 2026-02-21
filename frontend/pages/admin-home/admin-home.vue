<template>
  <view class="container">
    <view class="header">
      <text class="title">管理员端</text>
      <text class="subtitle">报名审核与数据管理</text>
    </view>

    <view class="card">
      <view class="row">
        <text class="label">当前账号：</text>
        <text class="value">{{ adminName || '-' }}</text>
      </view>

      <button class="btn" @click="goApplications">报名审核</button>
      <button class="btn" @click="goImportMatchNo">参赛号导入</button>
      <button class="btn" @click="goImportAwards">获奖导入</button>
      <button class="btn" @click="goImportExcellentCoaches">优秀辅导员导入</button>
      <button class="btn" @click="goStats">可视化统计</button>
      <button class="btn" @click="goAdminMe">验证登录状态</button>

      <button class="btn-secondary" @click="logout">退出管理员登录</button>
    </view>
  </view>
</template>

<script>
import * as requestApi from '../../utils/request'

const request = requestApi && requestApi.default ? requestApi.default : requestApi

export default {
  data() {
    return {
      adminName: ''
    }
  },

  async onShow() {
    const token = String(uni.getStorageSync('admin_token') || '').trim()
    if (!token) {
      uni.reLaunch({ url: '/pages/auth/auth?mode=admin' })
      return
    }

    try {
      const res = await request.get('/api/admin/me')
      if (res && res.success && res.data) {
        this.adminName = res.data.username || ''
      }
    } catch (e) {}
  },

  methods: {
    goApplications() {
      uni.navigateTo({ url: '/pages/admin-application-list/admin-application-list' })
    },

    goImportMatchNo() {
      uni.navigateTo({ url: '/pages/admin-import-match-no/admin-import-match-no' })
    },

    goImportAwards() {
      uni.navigateTo({ url: '/pages/admin-import-awards/admin-import-awards' })
    },

    goImportExcellentCoaches() {
      uni.navigateTo({ url: '/pages/admin-import-excellent-coaches/admin-import-excellent-coaches' })
    },

    goStats() {
      uni.navigateTo({ url: '/pages/admin-stats/admin-stats' })
    },

    async goAdminMe() {
      try {
        uni.showLoading({ title: '请求中...' })
        const res = await request.get('/api/admin/me')
        uni.hideLoading()
        uni.showModal({
          title: 'admin/me',
          content: JSON.stringify(res || {}, null, 2),
          showCancel: false
        })
      } catch (e) {
        uni.hideLoading()
        uni.showToast({ title: '网络错误', icon: 'error' })
      }
    },

    logout() {
      try { uni.removeStorageSync('admin_token') } catch (e) {}
      uni.reLaunch({ url: '/pages/auth/auth?mode=admin' })
    }
  }
}
</script>

<style scoped>
.container {
  min-height: 100vh;
  background-color: var(--bg);
  padding: 20px;
  box-sizing: border-box;
}

.header {
  background: linear-gradient(135deg, rgba(31, 75, 153, 1) 0%, rgba(14, 165, 164, 1) 100%);
  border-radius: 12px;
  padding: 20px;
  color: #fff;
  margin-bottom: 15px;
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.18);
}

.title {
  display: block;
  font-size: 20px;
  font-weight: bold;
}

.subtitle {
  display: block;
  font-size: 12px;
  margin-top: 6px;
  opacity: 0.9;
}

.card {
  background-color: var(--card);
  border-radius: 14px;
  padding: 16px;
  box-shadow: var(--shadow);
}

.row {
  display: flex;
  margin-bottom: 12px;
}

.label {
  width: 90px;
  color: var(--muted);
  font-size: 14px;
}

.value {
  flex: 1;
  color: var(--text);
  font-size: 14px;
}

.btn {
  margin-top: 10px;
  background-color: var(--brand);
  color: #fff;
  border-radius: 12px;
}

.btn-secondary {
  margin-top: 10px;
  background-color: transparent;
  color: var(--brand);
  border: 1px solid rgba(31, 75, 153, 0.55);
  border-radius: 12px;
}
</style>
