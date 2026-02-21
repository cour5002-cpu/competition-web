<template>
  <view class="container">
    <view class="card">
      <view class="row">
        <text class="label">状态</text>
        <picker :range="statusLabels" :value="statusIndex" @change="onStatusChange" class="picker">
          <view class="picker-text">{{ (statusIndex >= 0 && statusLabels && statusLabels[statusIndex]) ? statusLabels[statusIndex] : '全部' }}</view>
        </picker>
      </view>

      <view class="row">
        <text class="label">学段</text>
        <picker :range="educationOptions" :value="educationIndex" @change="onEducationChange" class="picker">
          <view class="picker-text">{{ educationIndex >= 0 ? educationOptions[educationIndex] : '全部' }}</view>
        </picker>
      </view>

      <view class="row">
        <text class="label">学校</text>
        <input v-model="schoolName" class="input" placeholder="支持模糊搜索" />
      </view>

      <view class="row">
        <text class="label">首字母</text>
        <input v-model="schoolInitial" class="input" placeholder="输入A-Z" maxlength="1" @input="onSchoolInitialInput" />
      </view>

      <view class="btn-row">
        <button class="btn" @click="doSearch(true)">查询</button>
        <button class="btn-secondary" @click="resetFilters">重置</button>
      </view>

      <view class="btn-row btn-row-gap">
        <button class="btn" @click="exportExcel">导出当前筛选Excel</button>
      </view>
    </view>

    <view v-if="items.length > 0" class="list">
      <view v-for="a in items" :key="a.id" class="item" @click="openDetail(a)">
        <view class="item-head">
          <text class="title">{{ a.school_name || '-' }}</text>
          <view :class="['badge', badgeClass(a.status)]">{{ statusText(a.status) }}</view>
        </view>
        <view class="meta">
          <text class="meta-line">{{ a.category }} - {{ a.task }}</text>
          <text class="meta-line">学段：{{ a.education_level || '-' }}｜人数：{{ a.participant_count || '-' }}</text>
          <text class="meta-line" v-if="a.match_no">参赛号：{{ a.match_no }}</text>
        </view>
      </view>

      <view class="pager">
        <button class="btn-secondary" :disabled="page <= 1 || loading" @click="prevPage">上一页</button>
        <text class="page-info">{{ page }}/{{ pages || 1 }}（共{{ total }}条）</text>
        <button class="btn-secondary" :disabled="page >= pages || loading" @click="nextPage">下一页</button>
      </view>
    </view>

    <view v-else class="empty">
      <image class="empty-icon" :src="emptyIcon" mode="aspectFit"></image>
      <text class="empty-text">暂无数据</text>
    </view>
  </view>
</template>

<script>
import * as requestApi from '../../utils/request'

const request = requestApi && requestApi.default ? requestApi.default : requestApi
const BASE_URL = requestApi && requestApi.BASE_URL ? requestApi.BASE_URL : ''

export default {
  data() {
    const emptySvg = `<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 24 24" fill="none" stroke="rgba(15, 23, 42, 0.55)" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8h12"/><path d="M7 8l1 12h8l1-12"/><path d="M9 8V6a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/><path d="M9.5 13.2h.01"/><path d="M14.5 13.2h.01"/><path d="M9.5 16.5c1.5 1.2 3.5 1.2 5 0"/></svg>`
    return {
      statusLabels: ['全部', '待审核', '已通过', '已退回'],
      statusValues: ['', 'pending', 'approved', 'rejected'],
      statusIndex: 0,
      educationOptions: ['全部', '小学', '初中', '高中/职高（含中专）'],
      educationIndex: 0,
      schoolName: '',
      schoolInitial: '',

      page: 1,
      perPage: 20,
      total: 0,
      pages: 1,
      items: [],
      loading: false,
      emptyIcon: `data:image/svg+xml;charset=utf-8,${encodeURIComponent(emptySvg)}`
    }
  },

  async onShow() {
    const token = String(uni.getStorageSync('admin_token') || '').trim()
    if (!token) {
      uni.reLaunch({ url: '/pages/auth/auth?mode=admin' })
      return
    }
    this.doSearch(true)
  },

  methods: {
    onStatusChange(e) {
      const idx = Number(e.detail.value || 0)
      this.statusIndex = (idx >= 0 && idx < this.statusLabels.length) ? idx : 0
    },

    onEducationChange(e) {
      const idx = Number(e.detail.value || 0)
      this.educationIndex = idx
    },

    resetFilters() {
      this.statusIndex = 0
      this.educationIndex = 0
      this.schoolName = ''
      this.schoolInitial = ''
      this.page = 1
      this.doSearch(true)
    },

    onSchoolInitialInput(e) {
      const val = (e && e.detail && typeof e.detail.value !== 'undefined') ? String(e.detail.value) : String(this.schoolInitial || '')
      const s = val.trim().toUpperCase()
      this.schoolInitial = /^[A-Z]$/.test(s) ? s : ''
    },

    statusText(s) {
      const m = { pending: '待审核', approved: '已通过', rejected: '已退回' }
      return m[s] || '未知'
    },

    badgeClass(s) {
      const m = { pending: 'b-pending', approved: 'b-approved', rejected: 'b-rejected' }
      return m[s] || 'b-default'
    },

    buildQuery() {
      const status = String((this.statusValues && this.statusValues[this.statusIndex]) || '')
      const education = this.educationIndex > 0 ? this.educationOptions[this.educationIndex] : ''
      const school = String(this.schoolName || '').trim()
      const initial = String(this.schoolInitial || '').trim().toUpperCase()
      return { status, education_level: education, school_name: school, school_initial: initial }
    },

    async doSearch(resetPage) {
      if (this.loading) return
      const token = String(uni.getStorageSync('admin_token') || '').trim()
      if (!token) {
        uni.reLaunch({ url: '/pages/auth/auth?mode=admin' })
        return
      }

      if (resetPage) this.page = 1

      const q = this.buildQuery()
      this.loading = true
      try {
        uni.showLoading({ title: '加载中...' })
        const res = await request.get('/api/admin/applications', {
          page: this.page,
          per_page: this.perPage,
          ...q
        })
        uni.hideLoading()

        if (res && res.success && res.data) {
          this.items = res.data.applications || []
          this.total = Number(res.data.total || 0)
          this.pages = Number(res.data.pages || 1)
          this.page = Number(res.data.current_page || this.page)
          return
        }

        uni.showModal({
          title: '加载失败',
          content: (res && res.message) ? res.message : '加载失败',
          showCancel: false
        })
      } catch (e) {
        uni.hideLoading()
        uni.showToast({ title: '网络错误', icon: 'error' })
      } finally {
        this.loading = false
      }
    },

    prevPage() {
      if (this.page <= 1) return
      this.page -= 1
      this.doSearch(false)
    },

    nextPage() {
      if (this.page >= this.pages) return
      this.page += 1
      this.doSearch(false)
    },

    openDetail(a) {
      if (!a || !a.id) return
      uni.navigateTo({ url: `/pages/admin-application-detail/admin-application-detail?id=${a.id}` })
    },

    exportExcel() {
      const token = String(uni.getStorageSync('admin_token') || '').trim()
      if (!token) {
        uni.reLaunch({ url: '/pages/auth/auth?mode=admin' })
        return
      }

      const q = this.buildQuery()
      const params = []
      Object.keys(q).forEach(k => {
        const v = q[k]
        if (v) params.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
      })
      const url = `${BASE_URL}/api/admin/applications/export${params.length ? ('?' + params.join('&')) : ''}`

      uni.showLoading({ title: '导出中...' })
      uni.downloadFile({
        url,
        header: { Authorization: `Bearer ${token}` },
        success: (res) => {
          uni.hideLoading()
          if (!res || res.statusCode !== 200 || !res.tempFilePath) {
            uni.showToast({ title: '导出失败', icon: 'none' })
            return
          }
          uni.openDocument({
            filePath: res.tempFilePath,
            showMenu: true,
            fail: () => {
              uni.showToast({ title: '打开失败', icon: 'none' })
            }
          })
        },
        fail: () => {
          uni.hideLoading()
          uni.showToast({ title: '导出失败', icon: 'none' })
        }
      })
    }
  }
}
</script>

<style scoped>
.container {
  min-height: 100vh;
  background-color: var(--bg);
  padding: 16px;
  box-sizing: border-box;
}

.card {
  background-color: var(--card);
  border-radius: 14px;
  padding: 14px;
  margin-bottom: 12px;
  box-shadow: var(--shadow);
}

.row {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.label {
  width: 60px;
  font-size: 13px;
  color: rgba(15, 23, 42, 0.72);
}

.picker {
  flex: 1;
  border: 1px solid var(--border);
  border-radius: 12px;
  height: 40px;
  display: flex;
  align-items: center;
  padding: 0 10px;
  background: #fff;
}

.picker-text {
  width: 100%;
  font-size: 14px;
  color: var(--text);
}

.input {
  flex: 1;
  border: 1px solid var(--border);
  border-radius: 12px;
  height: 40px;
  padding: 0 10px;
  box-sizing: border-box;
  font-size: 14px;
  background: #fff;
  color: var(--text);
}

.btn-row {
  display: flex;
  gap: 10px;
}

.btn-row-gap {
  margin-top: 8px;
}

.btn {
  flex: 1;
  background-color: var(--brand);
  color: #fff;
  border-radius: 12px;
  height: 40px;
  line-height: 40px;
  font-size: 14px;
  font-weight: 600;
}

.btn-secondary {
  flex: 1;
  background-color: transparent;
  color: var(--brand);
  border: 1px solid rgba(31, 75, 153, 0.55);
  border-radius: 12px;
  height: 40px;
  line-height: 40px;
  font-size: 14px;
  font-weight: 600;
}

.list .item {
  background-color: var(--card);
  border-radius: 14px;
  padding: 14px;
  margin-bottom: 10px;
  box-shadow: var(--shadow);
}

.item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
}

.badge {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  color: #fff;
}

.b-pending { background-color: #f59e0b; }
.b-approved { background-color: #0ea5a4; }
.b-rejected { background-color: #ef4444; }
.b-default { background-color: rgba(15, 23, 42, 0.45); }

.meta {
  margin-top: 8px;
}

.meta-line {
  display: block;
  font-size: 12px;
  color: var(--muted);
  margin-top: 4px;
}

.pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 4px;
}

.page-info {
  font-size: 12px;
  color: var(--muted);
}

.empty {
  margin-top: 50px;
  text-align: center;
  color: var(--muted);
  padding: 12px 0;
}

.empty-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 12px;
}

.empty-text {
  display: block;
  font-size: 13px;
}
</style>
