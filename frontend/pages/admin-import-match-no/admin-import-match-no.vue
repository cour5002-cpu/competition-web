<template>
  <view class="container">
    <view class="header">
      <text class="title">参赛号导入</text>
      <text class="subtitle">上传 Excel 批量写入参赛号</text>
    </view>

    <view class="card">
      <view class="file-row">
        <text class="label">文件</text>
        <view class="file-name">{{ fileName || '未选择' }}</view>
      </view>

      <view class="btn-row">
        <button class="btn-secondary" @click="pickFile">选择Excel</button>
        <button class="btn" :disabled="!filePath || uploading" @click="upload">上传导入</button>
      </view>

      <view class="result" v-if="result">
        <text class="result-title">导入结果</text>
        <text class="result-line">总计：{{ result.total_count }}</text>
        <text class="result-line">成功：{{ result.success_count }}</text>
        <text class="result-line">失败：{{ result.failed_count }}</text>

        <button
          v-if="result.error_log_available && result.import_log_id"
          class="btn"
          style="margin-top: 10px;"
          @click="downloadErrorLog"
        >
          下载错误日志
        </button>
      </view>
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
      filePath: '',
      fileName: '',
      uploading: false,
      result: null
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

    pickFile() {
      // 微信小程序优先用 chooseMessageFile
      const pick = uni.chooseMessageFile || uni.chooseFile
      if (!pick) {
        uni.showToast({ title: '当前环境不支持选择文件', icon: 'none' })
        return
      }

      pick({
        count: 1,
        type: 'file',
        extension: ['xlsx', 'xls'],
        success: (res) => {
          const f = (res && res.tempFiles && res.tempFiles[0]) ? res.tempFiles[0] : null
          if (!f) {
            uni.showToast({ title: '未选择文件', icon: 'none' })
            return
          }
          this.filePath = f.path || f.tempFilePath || ''
          this.fileName = f.name || ''
          this.result = null
        },
        fail: () => {}
      })
    },

    upload() {
      if (!this.filePath) return
      const token = String(uni.getStorageSync('admin_token') || '').trim()
      if (!token) {
        uni.reLaunch({ url: '/pages/auth/auth?mode=admin' })
        return
      }

      this.uploading = true
      uni.showLoading({ title: '上传中...' })

      uni.uploadFile({
        url: `${BASE_URL}/api/admin/import-match-no`,
        filePath: this.filePath,
        name: 'file',
        header: {
          Authorization: `Bearer ${token}`
        },
        success: (res) => {
          uni.hideLoading()
          this.uploading = false

          let payload = null
          try {
            payload = JSON.parse(res.data)
          } catch (e) {
            payload = null
          }

          if (!payload || !payload.success) {
            uni.showModal({
              title: '导入失败',
              content: (payload && payload.message) ? payload.message : '导入失败，请检查文件格式',
              showCancel: false
            })
            return
          }

          this.result = payload.data || null
          uni.showToast({ title: '导入完成', icon: 'success' })
        },
        fail: () => {
          uni.hideLoading()
          this.uploading = false
          uni.showToast({ title: '上传失败', icon: 'none' })
        }
      })
    },

    downloadErrorLog() {
      if (!this.result || !this.result.import_log_id) return
      const token = String(uni.getStorageSync('admin_token') || '').trim()
      if (!token) {
        uni.reLaunch({ url: '/pages/auth/auth?mode=admin' })
        return
      }

      const id = this.result.import_log_id
      uni.showLoading({ title: '下载中...' })
      uni.downloadFile({
        url: `${BASE_URL}/api/admin/download-error-log/${id}`,
        header: {
          Authorization: `Bearer ${token}`
        },
        success: (res) => {
          uni.hideLoading()
          if (!res || res.statusCode !== 200 || !res.tempFilePath) {
            uni.showToast({ title: '下载失败', icon: 'none' })
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
          uni.showToast({ title: '下载失败', icon: 'none' })
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

.file-row {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.label {
  width: 60px;
  color: var(--muted);
  font-size: 13px;
}

.file-name {
  flex: 1;
  font-size: 14px;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-row {
  display: flex;
  gap: 10px;
}

.btn {
  flex: 1;
  background-color: var(--brand);
  color: #fff;
  border-radius: 12px;
  font-weight: 600;
}

.btn-secondary {
  flex: 1;
  background-color: transparent;
  color: var(--brand);
  border: 1px solid rgba(31, 75, 153, 0.55);
  border-radius: 12px;
  font-weight: 600;
}

.result {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid rgba(15, 23, 42, 0.1);
}

.result-title {
  display: block;
  font-size: 14px;
  font-weight: bold;
  margin-bottom: 8px;
  color: var(--text);
}

.result-line {
  display: block;
  font-size: 14px;
  color: rgba(15, 23, 42, 0.78);
  margin-bottom: 4px;
}

.footer {
  margin-top: 10px;
}
</style>
