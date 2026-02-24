<template>
  <view class="container">
    <view class="header">
      <text class="title">证书ZIP下载</text>
      <text class="subtitle">下载当前已生成的证书（不会触发生成）</text>
    </view>

    <view class="card">
      <view class="row">
        <text class="label">Task ID</text>
        <input v-model="taskId" class="input" placeholder="可选：填写 task_id 只下载该任务涉及的证书" />
      </view>

      <view class="row">
        <text class="label">类型</text>
        <picker :range="kindLabels" :value="kindIndex" @change="onKindChange" class="picker">
          <view class="picker-text">{{ kindLabels[kindIndex] }}</view>
        </picker>
      </view>

      <view class="btn-row">
        <button class="btn-secondary" :disabled="loading || !taskId" @click="queryTask">查询任务进度</button>
        <button class="btn" :disabled="loading" @click="downloadZip">下载ZIP</button>
      </view>

      <view v-if="task" class="task">
        <text class="task-title">任务状态</text>
        <text class="task-line">状态：{{ task.status || '-' }}</text>
        <text class="task-line">进度：{{ (task.progress && task.progress.done_applications) || 0 }}/{{ (task.progress && task.progress.total_applications) || 0 }}</text>
        <text class="task-line">生成文件数：{{ (task.progress && task.progress.generated_files) || 0 }}</text>
        <text class="task-line">错误：{{ (task.progress && task.progress.errors) || 0 }}</text>
      </view>

      <view v-if="lastZip && lastZip.path" class="tip">
        <text>最近下载zip：约 {{ lastZip.size_kb }}KB</text>
        <view style="margin-top: 8px; display: flex; gap: 10px;">
          <button class="btn-secondary" @click="copyLastZipPath">复制路径</button>
          <button class="btn" @click="shareLastZip">转发到微信</button>
        </view>
      </view>
    </view>

    <view class="footer">
      <button class="btn-secondary" @click="goBack">返回</button>
    </view>
  </view>
</template>

<script>
import * as requestApi from '../../utils/request'

const request = requestApi && requestApi.default ? requestApi.default : requestApi
const BASE_URL = requestApi && requestApi.BASE_URL ? requestApi.BASE_URL : ''

export default {
  data() {
    return {
      taskId: '',
      kindIndex: 0,
      kindLabels: ['全部', '选手证书', '辅导员证书', '优秀辅导员证书'],
      kindValues: ['', 'player', 'coach', 'excellent_coach'],
      loading: false,
      task: null,
      lastZip: null
    }
  },

  onLoad(options) {
    const tid = options && options.task_id ? String(options.task_id) : ''
    this.taskId = tid.trim()
  },

  async onShow() {
    const token = String(uni.getStorageSync('admin_token') || '').trim()
    if (!token) {
      uni.reLaunch({ url: '/pages/auth/auth?mode=admin' })
      return
    }
  },

  methods: {
    goBack() {
      uni.navigateBack({ delta: 1 })
    },

    onKindChange(e) {
      const idx = Number(e.detail.value || 0)
      this.kindIndex = (idx >= 0 && idx < this.kindLabels.length) ? idx : 0
    },

    async queryTask() {
      const tid = String(this.taskId || '').trim()
      if (!tid) return
      if (this.loading) return

      this.loading = true
      try {
        uni.showLoading({ title: '查询中...' })
        const res = await request.get(`/api/admin/certificate-tasks/${encodeURIComponent(tid)}`)
        uni.hideLoading()
        if (res && res.success && res.data) {
          this.task = res.data
          return
        }
        this.task = null
        uni.showModal({ title: '查询失败', content: (res && res.message) ? res.message : '查询失败', showCancel: false })
      } catch (e) {
        uni.hideLoading()
        this.task = null
        uni.showToast({ title: '网络错误', icon: 'error' })
      } finally {
        this.loading = false
      }
    },

    downloadZip() {
      if (this.loading) return

      const token = String(uni.getStorageSync('admin_token') || '').trim()
      if (!token) {
        uni.reLaunch({ url: '/pages/auth/auth?mode=admin' })
        return
      }

      const kind = String((this.kindValues && this.kindValues[this.kindIndex]) || '')
      const tid = String(this.taskId || '').trim()

      const qs = []
      if (kind) qs.push(`kind=${encodeURIComponent(kind)}`)
      if (tid) qs.push(`task_id=${encodeURIComponent(tid)}`)

      const url = `${BASE_URL}/api/admin/certificates/download-zip${qs.length ? ('?' + qs.join('&')) : ''}`

      this.loading = true
      uni.showLoading({ title: '下载中...' })
      uni.downloadFile({
        url,
        header: { Authorization: `Bearer ${token}` },
        success: (res) => {
          uni.hideLoading()
          this.loading = false
          if (!res || res.statusCode !== 200 || !res.tempFilePath) {
            uni.showToast({ title: '下载失败', icon: 'none' })
            return
          }

          const tempPath = res.tempFilePath
          uni.getFileInfo({
            filePath: tempPath,
            success: (fres) => {
              const size = Number((fres && fres.size) || 0)
              uni.saveFile({
                tempFilePath: tempPath,
                success: (sres) => {
                  const saved = (sres && sres.savedFilePath) ? sres.savedFilePath : tempPath
                  this.lastZip = {
                    path: saved,
                    size_bytes: size,
                    size_kb: Math.max(1, Math.round(size / 1024)),
                    downloadUrl: url
                  }
                  uni.showModal({
                    title: '下载完成',
                    content: `已保存（约 ${Math.round(size / 1024)}KB）。请在文件管理器/微信文件中找到该zip，或转发到电脑解压查看。`,
                    showCancel: false
                  })
                  try { uni.setClipboardData({ data: saved }) } catch (e) {}
                },
                fail: () => {
                  this.lastZip = {
                    path: tempPath,
                    size_bytes: size,
                    size_kb: Math.max(1, Math.round(size / 1024)),
                    downloadUrl: url
                  }
                  uni.showModal({
                    title: '下载完成',
                    content: `zip 已下载到临时文件（约 ${Math.round(size / 1024)}KB）。请在下载列表中保存/转发到电脑后解压查看。`,
                    showCancel: false
                  })
                }
              })
            },
            fail: () => {
              uni.saveFile({
                tempFilePath: tempPath,
                success: () => {
                  this.lastZip = { path: tempPath, size_bytes: 0, size_kb: 0, downloadUrl: url }
                  uni.showModal({ title: '下载完成', content: '已保存到本地文件。请通过文件管理器找到该zip，或转发到电脑解压查看。', showCancel: false })
                },
                fail: () => {
                  uni.showToast({ title: '保存失败', icon: 'none' })
                }
              })
            }
          })
        },
        fail: () => {
          uni.hideLoading()
          this.loading = false
          uni.showToast({ title: '下载失败', icon: 'none' })
        }
      })
    },

    copyLastZipPath() {
      if (!this.lastZip || !this.lastZip.path) {
        uni.showToast({ title: '暂无zip路径', icon: 'none' })
        return
      }
      try {
        uni.setClipboardData({ data: String(this.lastZip.path) })
      } catch (e) {
        uni.showToast({ title: '复制失败', icon: 'none' })
      }
    },

    shareLastZip() {
      if (!this.lastZip || !this.lastZip.path) {
        uni.showToast({ title: '暂无zip文件', icon: 'none' })
        return
      }

      // eslint-disable-next-line no-undef
      if (typeof wx !== 'undefined' && wx && typeof wx.shareFileMessage === 'function') {
        // eslint-disable-next-line no-undef
        wx.shareFileMessage({
          filePath: this.lastZip.path,
          fileName: `证书_${Date.now()}.zip`,
          success: () => {
            uni.showToast({ title: '已唤起转发', icon: 'success' })
          },
          fail: () => {
            uni.showModal({ title: '转发失败', content: '微信可能不支持转发该文件或文件已被系统清理。你可以尝试重新下载后再转发。', showCancel: false })
          }
        })
        return
      }

      uni.showModal({ title: '当前环境不支持', content: '只有微信小程序环境支持直接转发文件。你可以在开发者工具/真机中重试，或把下载地址发到电脑浏览器下载。', showCancel: false })
    }
  }
}
</script>

<style scoped>
.container {
  min-height: 100vh;
  background-color: var(--bg);
  padding: 24px 16px;
}

.header {
  background: linear-gradient(135deg, rgba(31, 75, 153, 1) 0%, rgba(14, 165, 164, 1) 100%);
  border-radius: 12px;
  padding: 32px 24px;
  color: #fff;
  margin-bottom: 24px;
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.18);
}

.title {
  display: block;
  font-size: 24px;
  font-weight: bold;
}

.subtitle {
  display: block;
  font-size: 13px;
  margin-top: 8px;
  opacity: 0.9;
}

.card {
  background-color: var(--card);
  border-radius: 14px;
  padding: 24px;
  box-shadow: var(--shadow);
}

.row {
  display: flex;
  align-items: center;
  margin-bottom: 14px;
}

.label {
  width: 80px;
  color: var(--muted);
  font-size: 13px;
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

.btn-row {
  display: flex;
  gap: 12px;
  margin-top: 6px;
}

.btn {
  flex: 1;
  background-color: var(--brand);
  color: #fff;
  border-radius: 12px;
  height: 44px;
  line-height: 44px;
  font-size: 14px;
  font-weight: 600;
}

.btn-secondary {
  flex: 1;
  background-color: transparent;
  color: var(--brand);
  border: 1px solid rgba(31, 75, 153, 0.55);
  border-radius: 12px;
  height: 44px;
  line-height: 44px;
  font-size: 14px;
  font-weight: 600;
}

.task {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid rgba(15, 23, 42, 0.1);
}

.task-title {
  display: block;
  font-size: 14px;
  font-weight: bold;
  margin-bottom: 8px;
  color: var(--text);
}

.task-line {
  display: block;
  font-size: 13px;
  color: rgba(15, 23, 42, 0.78);
  margin-bottom: 4px;
}

.tip {
  margin-top: 14px;
  font-size: 12px;
  color: var(--muted);
}

.footer {
  margin-top: 24px;
}
</style>
