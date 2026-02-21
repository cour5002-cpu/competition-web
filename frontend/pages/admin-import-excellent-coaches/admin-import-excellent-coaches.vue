<template>
  <view class="container">
    <view class="card">
      <text class="title">优秀辅导员导入</text>
      <text class="desc">上传Excel：指导老师姓名 + 指导老师电话</text>

      <view class="row">
        <button class="btn" @click="chooseFile">选择Excel文件</button>
      </view>

      <view v-if="fileName" class="file-info">
        <text>已选择：{{ fileName }}</text>
      </view>

      <view class="row">
        <button class="btn" :disabled="!filePath || uploading" @click="upload">开始导入</button>
      </view>

      <view v-if="result" class="result">
        <text>总数：{{ result.total_count }}</text>
        <text>成功：{{ result.success_count }}</text>
        <text>失败：{{ result.failed_count }}</text>

        <button
          v-if="result.error_log_available"
          class="btn-secondary"
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

    chooseFile() {
      try {
        const chooser = (uni && typeof uni.chooseMessageFile === 'function')
          ? uni.chooseMessageFile
          : ((uni && typeof uni.chooseFile === 'function') ? uni.chooseFile : null)

        if (!chooser) {
          uni.showModal({
            title: '不支持',
            content: '当前环境不支持选择文件，请使用微信开发者工具/真机重试',
            showCancel: false
          })
          return
        }

        chooser({
          count: 1,
          type: 'file',
          extension: ['xls', 'xlsx'],
          success: (res) => {
            const f = res && res.tempFiles && res.tempFiles.length ? res.tempFiles[0] : null
            if (!f || !f.path) {
              uni.showToast({ title: '选择失败', icon: 'none' })
              return
            }
            this.filePath = f.path
            this.fileName = f.name || 'excel'
            this.result = null
          },
          fail: () => {
            uni.showToast({ title: '已取消', icon: 'none' })
          }
        })
      } catch (e) {
        uni.showModal({
          title: '选择失败',
          content: (e && e.message) ? String(e.message) : '选择文件失败，请重试',
          showCancel: false
        })
      }
    },

    upload() {
      const token = String(uni.getStorageSync('admin_token') || '').trim()
      if (!token) {
        uni.reLaunch({ url: '/pages/auth/auth?mode=admin' })
        return
      }

      if (!this.filePath) {
        uni.showToast({ title: '请先选择文件', icon: 'none' })
        return
      }

      this.uploading = true
      uni.showLoading({ title: '上传中...' })

      uni.uploadFile({
        url: `${BASE_URL}/api/admin/import-excellent-coaches`,
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

      uni.showLoading({ title: '下载中...' })
      uni.downloadFile({
        url: `${BASE_URL}/api/admin/download-error-log/${this.result.import_log_id}`,
        header: { Authorization: `Bearer ${token}` },
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
  padding: 16px;
  box-sizing: border-box;
}

.card {
  background-color: var(--card);
  border-radius: 14px;
  padding: 14px;
  box-shadow: var(--shadow);
}

.title {
  display: block;
  font-size: 18px;
  font-weight: bold;
  color: var(--text);
  margin-bottom: 6px;
}

.desc {
  display: block;
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 12px;
}

.row {
  margin-top: 10px;
}

.btn {
  width: 100%;
  background-color: var(--brand);
  color: #fff;
  border-radius: 12px;
  font-weight: 600;
}

.btn-secondary {
  width: 100%;
  background-color: transparent;
  color: var(--brand);
  border: 1px solid rgba(31, 75, 153, 0.55);
  border-radius: 12px;
  margin-top: 10px;
  font-weight: 600;
}

.file-info {
  margin-top: 10px;
  color: rgba(15, 23, 42, 0.78);
  font-size: 12px;
}

.result {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: rgba(15, 23, 42, 0.78);
}

.footer {
  margin-top: 12px;
}
</style>
