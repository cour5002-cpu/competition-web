<template>
  <view class="container">
    <view class="header">
      <text class="title">盖章图片上传</text>
      <text class="subtitle">选择证书类型与章序号，上传 PNG 替换对应盖章</text>
    </view>

    <view class="card">
      <view class="row">
        <text class="label">证书类型</text>
        <picker :range="kindLabels" :value="kindIndex" @change="onKindChange" class="picker">
          <view class="picker-text">{{ kindLabels[kindIndex] }}</view>
        </picker>
      </view>

      <view class="row">
        <text class="label">章序号</text>
        <picker :range="slotLabels" :value="slotIndex" @change="onSlotChange" class="picker">
          <view class="picker-text">{{ slotLabels[slotIndex] }}</view>
        </picker>
      </view>

      <view class="preview" v-if="previewUrl">
        <image class="preview-img" :src="previewUrl" mode="aspectFit"></image>
      </view>

      <view class="btn-row">
        <button class="btn-secondary" @click="refreshPreview" :disabled="loading">查看当前盖章</button>
        <button class="btn" @click="pickAndUpload" :disabled="loading">选择图片并上传</button>
      </view>

      <view class="tip">建议上传 PNG（透明底），图片会覆盖指定序号的盖章文件。</view>
    </view>

    <view class="footer">
      <button class="btn-secondary" @click="goBack">返回</button>
    </view>
  </view>
</template>

<script>
import * as requestApi from '../../utils/request'

const BASE_URL = requestApi && requestApi.BASE_URL ? requestApi.BASE_URL : ''

export default {
  data() {
    return {
      loading: false,
      kindLabels: ['学生证书（player）', '辅导员证书（coach）'],
      kindValues: ['player', 'coach'],
      kindIndex: 0,
      slotLabels: ['1', '2', '3', '4', '5', '6'],
      slotIndex: 0,
      previewUrl: ''
    }
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
      const idx = Number((e && e.detail && e.detail.value) || 0)
      this.kindIndex = (idx >= 0 && idx < this.kindValues.length) ? idx : 0
      this.previewUrl = ''
    },

    onSlotChange(e) {
      const idx = Number((e && e.detail && e.detail.value) || 0)
      this.slotIndex = (idx >= 0 && idx < this.slotLabels.length) ? idx : 0
      this.previewUrl = ''
    },

    buildStampUrl() {
      const kind = this.kindValues[this.kindIndex]
      const slot = Number(this.slotLabels[this.slotIndex])
      return `${BASE_URL}/api/admin/stamps/${kind}/${slot}`
    },

    refreshPreview() {
      const token = String(uni.getStorageSync('admin_token') || '').trim()
      if (!token) {
        uni.reLaunch({ url: '/pages/auth/auth?mode=admin' })
        return
      }

      if (this.loading) return
      this.loading = true
      uni.showLoading({ title: '加载中...' })

      const ts = Date.now()
      const url = `${this.buildStampUrl()}?t=${ts}`
      uni.downloadFile({
        url,
        header: {
          Authorization: `Bearer ${token}`
        },
        success: (res) => {
          uni.hideLoading()
          const ok = res && (res.statusCode >= 200 && res.statusCode < 300)
          if (!ok) {
            uni.showModal({
              title: '加载失败',
              content: `HTTP ${res && res.statusCode ? res.statusCode : ''}`,
              showCancel: false
            })
            return
          }
          this.previewUrl = res.tempFilePath
        },
        fail: (e) => {
          uni.hideLoading()
          uni.showModal({
            title: '加载失败',
            content: (e && e.errMsg) ? e.errMsg : '加载失败',
            showCancel: false
          })
        },
        complete: () => {
          this.loading = false
        }
      })
    },

    pickAndUpload() {
      const token = String(uni.getStorageSync('admin_token') || '').trim()
      if (!token) {
        uni.reLaunch({ url: '/pages/auth/auth?mode=admin' })
        return
      }

      if (this.loading) return

      uni.chooseImage({
        count: 1,
        sizeType: ['original', 'compressed'],
        sourceType: ['album', 'camera'],
        success: (res) => {
          const filePath = res && res.tempFilePaths && res.tempFilePaths[0]
          if (!filePath) {
            uni.showToast({ title: '未选择文件', icon: 'none' })
            return
          }
          this.doUpload(filePath, token)
        },
        fail: () => {
          uni.showToast({ title: '选择失败', icon: 'none' })
        }
      })
    },

    doUpload(filePath, token) {
      const url = this.buildStampUrl()
      this.loading = true
      uni.showLoading({ title: '上传中...' })
      uni.uploadFile({
        url,
        filePath,
        name: 'file',
        header: {
          Authorization: `Bearer ${token}`
        },
        success: (res) => {
          uni.hideLoading()
          const ok = res && (res.statusCode >= 200 && res.statusCode < 300)
          if (!ok) {
            uni.showModal({
              title: '上传失败',
              content: (res && res.data) ? String(res.data) : '上传失败',
              showCancel: false
            })
            return
          }
          uni.showToast({ title: '上传成功', icon: 'success' })
          this.refreshPreview()
        },
        fail: (e) => {
          uni.hideLoading()
          uni.showModal({
            title: '上传失败',
            content: (e && e.errMsg) ? e.errMsg : '上传失败',
            showCancel: false
          })
        },
        complete: () => {
          this.loading = false
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
  align-items: center;
  margin-bottom: 12px;
}

.label {
  width: 90px;
  color: var(--muted);
  font-size: 14px;
}

.picker {
  flex: 1;
}

.picker-text {
  padding: 10px 12px;
  border: 1px solid rgba(100, 116, 139, 0.35);
  border-radius: 10px;
  color: var(--text);
}

.preview {
  margin-top: 12px;
  border: 1px dashed rgba(100, 116, 139, 0.45);
  border-radius: 12px;
  padding: 10px;
}

.preview-img {
  width: 100%;
  height: 160px;
}

.btn-row {
  margin-top: 14px;
  display: flex;
  gap: 10px;
}

.btn {
  flex: 1;
  background-color: var(--brand);
  color: #fff;
  border-radius: 12px;
}

.btn-secondary {
  flex: 1;
  background-color: transparent;
  color: var(--brand);
  border: 1px solid rgba(31, 75, 153, 0.55);
  border-radius: 12px;
}

.tip {
  margin-top: 10px;
  color: var(--muted);
  font-size: 12px;
}

.footer {
  margin-top: 16px;
}
</style>
