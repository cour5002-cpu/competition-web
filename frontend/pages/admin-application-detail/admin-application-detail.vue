<template>
  <view class="container">
    <view class="card" v-if="item">
      <view class="head">
        <text class="title">报名详情</text>
        <view :class="['badge', badgeClass(item.status)]">{{ statusText(item.status) }}</view>
      </view>

      <view class="row"><text class="k">学校</text><text class="v">{{ item.school_name || '-' }}</text></view>
      <view class="row"><text class="k">项目</text><text class="v">{{ item.category }} - {{ item.task }}</text></view>
      <view class="row"><text class="k">学段</text><text class="v">{{ item.education_level || '-' }}</text></view>
      <view class="row"><text class="k">人数</text><text class="v">{{ item.participant_count || '-' }}</text></view>
      <view class="row"><text class="k">参赛号</text><text class="v">{{ item.match_no || '-' }}</text></view>

      <view class="row"><text class="k">指导老师</text><text class="v">{{ item.teacher_name || '-' }}</text></view>
      <view class="row"><text class="k">老师电话</text><text class="v">{{ item.teacher_phone || '-' }}</text></view>

      <view class="row"><text class="k">领队</text><text class="v">{{ item.leader_name || '-' }}</text></view>
      <view class="row"><text class="k">领队电话</text><text class="v">{{ item.leader_phone || '-' }}</text></view>

      <view class="row"><text class="k">参赛人手机</text><text class="v">{{ item.participant_phone || '-' }}</text></view>
      <view class="row"><text class="k">参赛人邮箱</text><text class="v">{{ item.participant_email || '-' }}</text></view>

      <view class="row" v-if="item.rejected_reason"><text class="k">退回原因</text><text class="v">{{ item.rejected_reason }}</text></view>

      <view class="section" v-if="item.participants && item.participants.length">
        <text class="section-title">选手名单</text>
        <view class="p" v-for="p in sortedParticipants" :key="p.id || p.seq_no">
          <text>{{ p.seq_no }}. {{ p.participant_name }}</text>
        </view>
      </view>
    </view>

    <view class="card" v-else>
      <text>加载中...</text>
    </view>

    <view class="card">
      <view class="btn-row">
        <button class="btn-approve" :disabled="loading || !canApprove" @click="approve">通过</button>
        <button class="btn-reject" :disabled="loading" @click="openReject">退回</button>
      </view>
      <view class="tip">退回需填写原因。通过/退回后状态会更新，并尝试发送通知。</view>
    </view>

    <view class="footer">
      <button class="btn-secondary" @click="goBack">返回</button>
    </view>

    <view v-if="rejectVisible" class="modal-mask">
      <view class="modal">
        <text class="modal-title">退回原因（必填）</text>
        <textarea v-model="rejectReason" class="textarea" placeholder="请输入退回原因"></textarea>
        <view class="btn-row">
          <button class="btn-secondary" @click="closeReject" :disabled="loading">取消</button>
          <button class="btn-reject" @click="reject" :disabled="loading">确认退回</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import * as requestApi from '../../utils/request'

const request = requestApi && requestApi.default ? requestApi.default : requestApi

export default {
  data() {
    return {
      id: '',
      item: null,
      loading: false,
      rejectVisible: false,
      rejectReason: ''
    }
  },

  computed: {
    sortedParticipants() {
      const arr = (this.item && Array.isArray(this.item.participants)) ? this.item.participants : []
      return arr.slice().sort((a, b) => Number(a.seq_no || 0) - Number(b.seq_no || 0))
    },

    canApprove() {
      if (!this.item) return false
      return this.item.status !== 'approved'
    }
  },

  onLoad(options) {
    this.id = String((options && options.id) || '').trim()
  },

  async onShow() {
    const token = String(uni.getStorageSync('admin_token') || '').trim()
    if (!token) {
      uni.reLaunch({ url: '/pages/auth/auth?mode=admin' })
      return
    }
    this.loadDetail()
  },

  methods: {
    goBack() {
      uni.navigateBack({ delta: 1 })
    },

    statusText(s) {
      const m = { pending: '待审核', approved: '已通过', rejected: '已退回' }
      return m[s] || '未知'
    },

    badgeClass(s) {
      const m = { pending: 'b-pending', approved: 'b-approved', rejected: 'b-rejected' }
      return m[s] || 'b-default'
    },

    async loadDetail() {
      if (!this.id) {
        uni.showToast({ title: '缺少ID', icon: 'none' })
        return
      }

      this.loading = true
      try {
        uni.showLoading({ title: '加载中...' })
        const res = await request.get(`/api/admin/applications/${this.id}`)
        uni.hideLoading()

        if (res && res.success && res.data) {
          this.item = res.data
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

    async approve() {
      if (!this.id) return
      if (this.loading) return

      const ok = await new Promise(resolve => {
        uni.showModal({
          title: '确认通过',
          content: '确认将该报名标记为“已通过”？',
          success: (res) => resolve(!!(res && res.confirm))
        })
      })
      if (!ok) return

      this.loading = true
      try {
        uni.showLoading({ title: '提交中...' })
        const res = await request.post(`/api/admin/applications/${this.id}/approve`, {})
        uni.hideLoading()

        if (res && res.success) {
          uni.showToast({ title: '已通过', icon: 'success' })
          this.item = res.data || this.item
          return
        }

        uni.showModal({
          title: '操作失败',
          content: (res && res.message) ? res.message : '操作失败',
          showCancel: false
        })
      } catch (e) {
        uni.hideLoading()
        uni.showToast({ title: '网络错误', icon: 'error' })
      } finally {
        this.loading = false
      }
    },

    openReject() {
      this.rejectReason = ''
      this.rejectVisible = true
    },

    closeReject() {
      if (this.loading) return
      this.rejectVisible = false
    },

    async reject() {
      if (!this.id) return
      if (this.loading) return

      const reason = String(this.rejectReason || '').trim()
      if (!reason) {
        uni.showToast({ title: '请输入退回原因', icon: 'none' })
        return
      }

      this.loading = true
      try {
        uni.showLoading({ title: '提交中...' })
        const res = await request.post(`/api/admin/applications/${this.id}/reject`, { reason })
        uni.hideLoading()

        if (res && res.success) {
          this.rejectVisible = false
          uni.showToast({ title: '已退回', icon: 'success' })
          this.item = (res.data && res.data.id) ? res.data : (res.data || this.item)
          // 后端 reject 接口会把 notify 信息塞到 data.notify，若你想展示可在这里加 modal
          return
        }

        uni.showModal({
          title: '操作失败',
          content: (res && res.message) ? res.message : '操作失败',
          showCancel: false
        })
      } catch (e) {
        uni.hideLoading()
        uni.showToast({ title: '网络错误', icon: 'error' })
      } finally {
        this.loading = false
      }
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

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.title {
  font-size: 16px;
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

.row {
  display: flex;
  padding: 8px 0;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}

.k {
  width: 90px;
  color: var(--muted);
  font-size: 13px;
}

.v {
  flex: 1;
  color: var(--text);
  font-size: 13px;
}

.section {
  margin-top: 12px;
}

.section-title {
  display: block;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--text);
}

.p {
  padding: 6px 0;
  color: rgba(15, 23, 42, 0.78);
  font-size: 13px;
}

.btn-row {
  display: flex;
  gap: 10px;
}

.btn-approve {
  flex: 1;
  background-color: var(--brand-2);
  color: #fff;
  border-radius: 12px;
  height: 40px;
  line-height: 40px;
  font-size: 14px;
  font-weight: 600;
}

.btn-reject {
  flex: 1;
  background-color: var(--danger);
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

.tip {
  margin-top: 10px;
  color: var(--muted);
  font-size: 12px;
}

.footer {
  margin-top: 8px;
}

.modal-mask {
  position: fixed;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  background-color: rgba(0,0,0,0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 18px;
  box-sizing: border-box;
}

.modal {
  width: 100%;
  background-color: var(--card);
  border-radius: 14px;
  padding: 14px;
  box-shadow: 0 18px 46px rgba(15, 23, 42, 0.28);
}

.modal-title {
  display: block;
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 10px;
  color: var(--text);
}

.textarea {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: 12px;
  min-height: 90px;
  padding: 10px;
  box-sizing: border-box;
  font-size: 14px;
  background: #fff;
  color: var(--text);
}
</style>
