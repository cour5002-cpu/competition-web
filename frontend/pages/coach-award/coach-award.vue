<template>
  <view class="container">
    <view class="search-bar">
      <input
        v-model="teacherName"
        type="text"
        placeholder="请输入指导老师姓名"
        class="search-input"
      />
      <input
        v-model="teacherPhone"
        type="number"
        placeholder="请输入指导老师电话"
        class="search-input"
        maxlength="11"
      />
      <button class="search-btn" @click="search">查询</button>
    </view>

    <text class="search-hint">请输入指导老师姓名与电话，查询优秀辅导员证书</text>

    <view v-if="hasSearched && !result" class="empty-state">
      <image class="empty-icon" :src="emptyIcon" mode="aspectFit"></image>
      <text class="empty-text">未找到记录</text>
    </view>

    <view v-if="result" class="card">
      <view class="row">
        <text class="label">老师：</text>
        <text class="value">{{ result.teacher_name }}</text>
      </view>
      <view class="row">
        <text class="label">学校：</text>
        <text class="value">{{ result.school_name }}</text>
      </view>
      <view class="row" v-if="result.category">
        <text class="label">项目：</text>
        <text class="value">{{ result.category }} - {{ result.task }}</text>
      </view>
      <view class="row" v-if="result.match_no">
        <text class="label">参赛号：</text>
        <text class="value">{{ result.match_no }}</text>
      </view>
      <view class="row" v-if="result.award_level">
        <text class="label">获奖：</text>
        <text class="value award">{{ result.award_level }}</text>
      </view>

      <view class="row" v-if="participantsText">
        <text class="label">选手：</text>
        <text class="value">{{ participantsText }}</text>
      </view>

      <button class="download-btn" :disabled="!canDownload" @click="openCoachCertificate">
        打开优秀辅导员证书
      </button>

      <text v-if="!canDownload" class="warn">该参赛号暂无获奖信息，无法生成证书</text>
    </view>
  </view>
</template>

<script>
import * as requestApi from '../../utils/request'
import auth from '../../utils/auth'

const request = requestApi && requestApi.default ? requestApi.default : requestApi
const BASE_URL = requestApi && requestApi.BASE_URL ? requestApi.BASE_URL : ''

export default {
  data() {
    return {
      teacherName: '',
      teacherPhone: '',
      result: null,
      coachId: '',
      hasSearched: false,
      emptyIcon: `data:image/svg+xml;charset=utf-8,${encodeURIComponent('<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"96\" height=\"96\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"rgba(15, 23, 42, 0.55)\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M4 7h16\"/><path d=\"M6 7l1 14h10l1-14\"/><path d=\"M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2\"/><path d=\"M9.5 12.5h.01\"/><path d=\"M14.5 12.5h.01\"/><path d=\"M9.5 16c1.5 1.3 3.5 1.3 5 0\"/></svg>')}`
    }
  },

  async onShow() {
    await auth.requireUserLoginOrRedirect('/pages/coach-award/coach-award')
  },

  onHide() {
    this.resetPage()
  },

  onUnload() {
    this.resetPage()
  },

  computed: {
    participantsText() {
      const app = this.result
      if (!app || !Array.isArray(app.participants) || app.participants.length === 0) return ''
      const sorted = app.participants.slice().sort((a, b) => (a.seq_no || 0) - (b.seq_no || 0))
      return sorted.map(p => p.participant_name).join('、')
    },

    canDownload() {
      return !!(this.result && this.result.award_level && this.coachId)
    }
  },

  methods: {
    resetPage() {
      this.teacherName = ''
      this.teacherPhone = ''
      this.result = null
      this.coachId = ''
      this.hasSearched = false
    },
    async search() {
      const ok = await auth.requireUserLoginOrRedirect('/pages/coach-award/coach-award')
      if (!ok) return

      const teacherName = String(this.teacherName || '').trim()
      const teacherPhone = String(this.teacherPhone || '').trim()
      if (!teacherName || !teacherPhone) {
        uni.showToast({
          title: '请输入姓名与电话',
          icon: 'error'
        })
        return
      }

      try {
        uni.showLoading({ title: '查询中...' })
        const res = await request.get('/api/excellent-coaches/query', { teacher_name: teacherName, teacher_phone: teacherPhone })
        uni.hideLoading()

        this.hasSearched = true
        if (res && res.success && res.data) {
          const coach = (res.data && res.data.coach) ? res.data.coach : null
          const app = (res.data && res.data.application) ? res.data.application : null
          this.coachId = coach && coach.coach_id ? String(coach.coach_id) : ''
          this.result = app ? {
            ...app,
            teacher_name: coach && coach.teacher_name ? coach.teacher_name : teacherName
          } : null
        } else {
          this.result = null
          this.coachId = ''
          uni.showModal({
            title: '查询失败',
            content: (res && res.message) || '查询失败，请重试',
            showCancel: false
          })
        }
      } catch (e) {
        uni.hideLoading()
        this.hasSearched = true
        this.result = null
        this.coachId = ''
        uni.showToast({
          title: '网络错误',
          icon: 'error'
        })
      }
    },

    openCoachCertificate() {
      if (!this.canDownload) return

      const coachId = String(this.coachId || '').trim()
      const url = `${BASE_URL}/api/certificate/generate-excellent-coach/${coachId}`
      const token = String(uni.getStorageSync('user_token') || '').trim()
      uni.showLoading({ title: '打开中...' })

      uni.downloadFile({
        url,
        header: token ? { Authorization: `Bearer ${token}` } : {},
        success: (res) => {
          uni.hideLoading()
          if (res.statusCode === 200) {
            uni.openDocument({
              filePath: res.tempFilePath,
              showMenu: true
            })
            return
          }
          uni.showModal({
            title: '打开失败',
            content: '证书下载失败，请稍后重试',
            showCancel: false
          })
        },
        fail: () => {
          uni.hideLoading()
          uni.showModal({
            title: '打开失败',
            content: '证书下载失败，请稍后重试',
            showCancel: false
          })
        }
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

.search-bar {
  display: flex;
  flex-direction: column;
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
  border: 1px solid var(--border);
  border-radius: 12px;
  height: 42px;
  line-height: 42px;
  padding: 0 12px;
  font-size: 16px;
  margin-bottom: 10px;
  box-sizing: border-box;
  background: #fff;
  color: var(--text);
}

.search-btn {
  background-color: var(--brand);
  color: white;
  border-radius: 12px;
  width: 100%;
  padding: 0 20px;
  font-size: 16px;
  height: 42px;
  line-height: 42px;
}

.empty-state {
  margin-top: 40px;
  text-align: center;
}

.empty-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 12px;
}

.empty-text {
  color: var(--muted);
}

.card {
  background-color: var(--card);
  border-radius: 14px;
  padding: 16px;
  box-shadow: var(--shadow);
}

.row {
  display: flex;
  margin-bottom: 10px;
}

.label {
  width: 70px;
  color: var(--muted);
}

.value {
  flex: 1;
  color: var(--text);
}

.award {
  color: #e67e22;
  font-weight: bold;
}

.download-btn {
  margin-top: 15px;
  background-color: var(--brand-2);
  color: #fff;
  border-radius: 12px;
}

.warn {
  display: block;
  margin-top: 10px;
  font-size: 12px;
  color: rgba(15, 23, 42, 0.5);
}
</style>
