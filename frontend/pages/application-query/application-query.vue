<template>
  <view class="container">
    <view class="search-bar">
      <input
        v-model="phone"
        type="number"
        placeholder="请输入报名手机号查询"
        class="search-input"
        maxlength="11"
      />
      <button class="search-btn" @click="search">查询</button>
    </view>

    <text class="search-hint">请输入报名时填写的参赛人手机号查询报名状态</text>

    <view class="application-list" v-if="applications.length > 0">
      <view
        v-for="application in applications"
        :key="application.id"
        class="application-item"
      >
        <view class="app-header">
          <text class="project-name">{{ application.category }} - {{ application.task }}</text>
          <view :class="['status-badge', getStatusClass(application.status)]">
            {{ getStatusText(application.status) }}
          </view>
        </view>

        <view class="app-content">
          <view class="info-row">
            <text class="info-label">学校：</text>
            <text class="info-value">{{ displayText(application.school_name) }}</text>
          </view>

          <view class="info-row" v-if="application.education_level">
            <text class="info-label">学段：</text>
            <text class="info-value">{{ displayText(application.education_level) }}</text>
          </view>

          <view class="info-row" v-if="application.participant_count">
            <text class="info-label">人数：</text>
            <text class="info-value">{{ application.participant_count }}人</text>
          </view>

          <view class="info-row" v-if="application.contact_name">
            <text class="info-label">联系人：</text>
            <text class="info-value">{{ displayText(application.contact_name) }}</text>
          </view>

          <view class="info-row" v-if="application.contact_phone">
            <text class="info-label">手机：</text>
            <text class="info-value">{{ displayText(application.contact_phone) }}</text>
          </view>

          <view class="info-row" v-if="application.match_no">
            <text class="info-label">参赛号：</text>
            <text class="info-value">{{ displayText(application.match_no) }}</text>
          </view>

          <view class="participants-section" v-if="application.participants && application.participants.length > 0">
            <text class="participants-title">选手名单：</text>
            <view class="participants-list">
              <text
                v-for="participant in application.participants"
                :key="participant.id"
                class="participant-name"
              >
                {{ participant.seq_no }}. {{ participant.participant_name }}
              </text>
            </view>
          </view>
        </view>

        <view class="app-footer">
          <text class="submit-time">提交时间：{{ formatDate(application.created_at) }}</text>
        </view>

        <view class="app-footer" v-if="application.status === 'rejected'">
          <view class="info-row" v-if="application.rejected_reason">
            <text class="info-label">退回原因：</text>
            <text class="info-value">{{ displayText(application.rejected_reason) }}</text>
          </view>
          <button class="go-register-btn" @click="goToResubmit(application)">修改并再次提交</button>
        </view>
      </view>
    </view>

    <view class="empty-state" v-else-if="hasSearched">
      <image class="empty-icon" :src="emptyIcon" mode="aspectFit"></image>
      <text class="empty-text">暂无报名信息</text>
      <button class="go-register-btn" @click="goToRegister">立即报名</button>
    </view>

    <view class="initial-state" v-else>
      <image class="initial-icon" :src="searchIcon" mode="aspectFit"></image>
      <text class="initial-text">请输入手机号查询报名记录</text>
    </view>
  </view>
</template>

<script>
import request from '../../utils/request'
import auth from '../../utils/auth'

export default {
  data() {
    const emptySvg = `<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 24 24" fill="none" stroke="rgba(15, 23, 42, 0.55)" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16"/><path d="M6 7l1 14h10l1-14"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/><path d="M9.5 12.5h.01"/><path d="M14.5 12.5h.01"/><path d="M9.5 16c1.5 1.3 3.5 1.3 5 0"/></svg>`
    const searchSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 24 24" fill="none" stroke="#1f4b99" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.2-3.2"/></svg>`
    return {
      phone: '',
      applications: [],
      hasSearched: false,
      emptyIcon: `data:image/svg+xml;charset=utf-8,${encodeURIComponent(emptySvg)}`,
      searchIcon: `data:image/svg+xml;charset=utf-8,${encodeURIComponent(searchSvg)}`
    }
  },

  async onShow() {
    await auth.requireUserLoginOrRedirect('/pages/application-query/application-query')
  },

  onHide() {
    this.resetPage()
  },

  onUnload() {
    this.resetPage()
  },

  methods: {
    resetPage() {
      this.phone = ''
      this.applications = []
      this.hasSearched = false
    },

    goToRegister() {
      uni.switchTab({
        url: '/pages/register/register'
      })
    },

    goToResubmit(application) {
      if (!application || !application.id) return
      try {
        uni.setStorageSync('resubmit_application_id', String(application.id))
      } catch (e) {}
      uni.switchTab({
        url: '/pages/register/register'
      })
    },
    async search() {
      const ok = await auth.requireUserLoginOrRedirect('/pages/application-query/application-query')
      if (!ok) return

      const phone = String(this.phone || '').trim()
      if (!phone || phone.length !== 11) {
        uni.showToast({
          title: '请输入正确的手机号',
          icon: 'error'
        })
        return
      }

      try {
        uni.showLoading({ title: '查询中...' })
        const res = await request.get('/api/applications/by-phone', { phone })
        uni.hideLoading()

        this.hasSearched = true
        if (res && res.success) {
          this.applications = res.data || []
          return
        }

        this.applications = []
        uni.showModal({
          title: '查询失败',
          content: (res && res.message) || '查询失败，请重试',
          showCancel: false
        })
      } catch (e) {
        uni.hideLoading()
        this.hasSearched = true
        this.applications = []
        uni.showToast({
          title: '网络错误',
          icon: 'error'
        })
      }
    },

    getStatusClass(status) {
      const statusMap = {
        pending: 'status-pending',
        approved: 'status-approved',
        rejected: 'status-rejected'
      }
      return statusMap[status] || 'status-default'
    },

    getStatusText(status) {
      const statusMap = {
        pending: '待审核',
        approved: '已通过',
        rejected: '已拒绝'
      }
      return statusMap[status] || '未知'
    },

    isBlankText(v) {
      const s = String(v == null ? '' : v).trim()
      if (!s) return true
      const low = s.toLowerCase()
      return low === 'nan' || low === 'none' || low === 'null' || low === 'undefined'
    },

    displayText(v) {
      return this.isBlankText(v) ? '无' : String(v).trim()
    },

    formatDate(dateString) {
      if (!dateString) return ''
      const date = new Date(dateString)
      return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
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

.search-bar {
  display: flex;
  margin-bottom: 20px;
  background-color: var(--card);
  padding: 15px;
  border-radius: 14px;
  box-shadow: var(--shadow);
}

.search-hint {
  display: block;
  margin-top: -10px;
  margin-bottom: 20px;
  font-size: 12px;
  color: var(--muted);
  padding: 0 5px;
}

.search-input {
  flex: 1;
  border: 1px solid var(--border);
  border-radius: 12px;
  height: 42px;
  line-height: 42px;
  padding: 0 12px;
  font-size: 16px;
  margin-right: 10px;
  box-sizing: border-box;
  background: #fff;
  color: var(--text);
}

.search-btn {
  background-color: var(--brand);
  color: white;
  border-radius: 12px;
  padding: 0 20px;
  font-size: 16px;
  height: 42px;
  line-height: 42px;
}

.application-item {
  background-color: var(--card);
  border-radius: 14px;
  padding: 15px;
  margin-bottom: 15px;
  box-shadow: var(--shadow);
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.project-name {
  font-size: 16px;
  font-weight: bold;
  color: var(--text);
  flex: 1;
}

.status-badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  color: white;
}

.status-pending {
  background-color: #f39c12;
}

.participants-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(15, 23, 42, 0.1);
}

.participants-title {
  display: block;
  font-size: 14px;
  color: var(--muted);
  margin-bottom: 8px;
}

.participants-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.participant-name {
  background-color: rgba(15, 23, 42, 0.04);
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  color: var(--text);
}

.status-approved {
  background-color: #27ae60;
}

.status-rejected {
  background-color: #e74c3c;
}

.info-row {
  display: flex;
  margin-bottom: 6px;
}

.info-label {
  width: 60px;
  color: var(--muted);
  font-size: 14px;
}

.info-value {
  flex: 1;
  color: var(--text);
  font-size: 14px;
}

.award-text {
  color: #e67e22;
  font-weight: bold;
}

.app-footer {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(15, 23, 42, 0.1);
}

.submit-time {
  font-size: 12px;
  color: #999;
}

.empty-state,
.initial-state {
  margin-top: 40px;
  text-align: center;
}

.empty-icon,
.initial-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 12px;
}

.empty-text,
.initial-text {
  color: var(--muted);
}

.go-register-btn {
  margin-top: 15px;
  background-color: var(--brand);
  color: white;
  border-radius: 20px;
  padding: 8px 20px;
  font-size: 14px;
}
</style>
