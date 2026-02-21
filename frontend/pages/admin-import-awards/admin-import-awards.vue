<template>
  <view class="container">
    <view class="header">
      <text class="title">获奖导入</text>
      <text class="subtitle">上传 Excel 批量写入获奖等级</text>
    </view>

    <view class="card">
      <view class="file-row">
        <text class="label">文件</text>
        <view class="file-name">{{ fileName || '未选择' }}</view>
      </view>

      <view class="row">
        <text class="label">生成证书</text>
        <view class="seg">
          <view class="seg-item" :class="autoGenerate ? 'active' : ''" @click="setAutoGenerate(true)">是</view>
          <view class="seg-item" :class="!autoGenerate ? 'active' : ''" @click="setAutoGenerate(false)">否</view>
        </view>
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

        <view class="tip" v-if="autoGenerate">
          若勾选生成证书：后端会返回 zip 文件，请在下载完成后手动打开。
        </view>

        <view class="tip" v-if="lastZip && lastZip.path">
          <text>最近下载zip：约 {{ lastZip.size_kb }}KB</text>
          <view style="margin-top: 8px; display: flex; gap: 10px;">
            <button class="btn-secondary" @click="copyLastZipPath">复制路径</button>
            <button class="btn" @click="shareLastZip">转发到微信</button>
          </view>
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

const BASE_URL = requestApi && requestApi.BASE_URL ? requestApi.BASE_URL : ''

export default {
  data() {
    return {
      filePath: '',
      fileName: '',
      autoGenerate: false,
      uploading: false,
      result: null,
      lastZip: null
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

    setAutoGenerate(v) {
      this.autoGenerate = !!v
    },

    pickFile() {
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

      const url = this.autoGenerate
        ? `${BASE_URL}/api/admin/import-awards?auto_generate=1`
        : `${BASE_URL}/api/admin/import-awards`

      uni.uploadFile({
        url,
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

          if (this.autoGenerate && this.result && this.result.zip_download_url) {
            const downloadUrl = `${BASE_URL}${this.result.zip_download_url}`
            uni.showLoading({ title: '下载证书中...' })
            uni.downloadFile({
              url: downloadUrl,
              header: {
                Authorization: `Bearer ${token}`
              },
              success: (dres) => {
                uni.hideLoading()
                if (!dres || dres.statusCode !== 200 || !dres.tempFilePath) {
                  uni.showToast({ title: '下载失败', icon: 'none' })
                  return
                }

                const tempPath = dres.tempFilePath

                // 校验下载文件大小，避免 0KB（通常是后端返回空内容/网络地址不对）
                uni.getFileInfo({
                  filePath: tempPath,
                  success: (fres) => {
                    const size = Number((fres && fres.size) || 0)
                    if (size <= 0) {
                      uni.showModal({
                        title: '下载到 0KB',
                        content: `证书zip下载到了 0KB。\n\n状态码：${dres.statusCode}\n地址：${downloadUrl}\n\n请检查：\n1) BASE_URL 是否可被当前运行端访问（小程序真机不能用 127.0.0.1）\n2) 后端是否实际生成了zip文件`,
                        showCancel: false
                      })
                      return
                    }

                    // 小程序端通常无法直接 openDocument 打开 zip，改为保存文件并提示用户自行解压
                    uni.saveFile({
                      tempFilePath: tempPath,
                      success: (sres) => {
                        const saved = (sres && sres.savedFilePath) ? sres.savedFilePath : tempPath
                        this.lastZip = {
                          path: saved,
                          size_bytes: size,
                          size_kb: Math.max(1, Math.round(size / 1024)),
                          downloadUrl
                        }
                        uni.showModal({
                          title: '证书压缩包已下载',
                          content: `已保存（约 ${Math.round(size / 1024)}KB）。请通过微信文件/文件管理器找到该zip，或转发到电脑解压查看。`,
                          showCancel: false
                        })
                        try {
                          uni.setClipboardData({ data: saved })
                        } catch (e) {}
                      },
                      fail: () => {
                        this.lastZip = {
                          path: tempPath,
                          size_bytes: size,
                          size_kb: Math.max(1, Math.round(size / 1024)),
                          downloadUrl
                        }
                        uni.showModal({
                          title: '证书压缩包已下载',
                          content: `zip 已下载到临时文件（约 ${Math.round(size / 1024)}KB）。请在微信下载列表中保存/转发到电脑后解压查看。`,
                          showCancel: false
                        })
                      }
                    })
                  },
                  fail: () => {
                    // 获取不到大小也尝试保存
                    uni.saveFile({
                      tempFilePath: tempPath,
                      success: () => {
                        this.lastZip = {
                          path: tempPath,
                          size_bytes: 0,
                          size_kb: 0,
                          downloadUrl
                        }
                        uni.showModal({
                          title: '证书压缩包已下载',
                          content: '已保存到本地文件。请通过微信文件/文件管理器找到该zip，或转发到电脑解压查看。',
                          showCancel: false
                        })
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
                uni.showToast({ title: '下载失败', icon: 'none' })
              }
            })
          }
        },
        fail: () => {
          uni.hideLoading()
          this.uploading = false
          uni.showToast({ title: '上传失败', icon: 'none' })
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

      // 微信小程序专用：把沙盒文件“转发到聊天”，用户可在聊天里保存/发到电脑解压
      // eslint-disable-next-line no-undef
      if (typeof wx !== 'undefined' && wx && typeof wx.shareFileMessage === 'function') {
        // eslint-disable-next-line no-undef
        wx.shareFileMessage({
          filePath: this.lastZip.path,
          fileName: `获奖证书_${Date.now()}.zip`,
          success: () => {
            uni.showToast({ title: '已唤起转发', icon: 'success' })
          },
          fail: () => {
            uni.showModal({
              title: '转发失败',
              content: '微信可能不支持转发该文件或文件已被系统清理。你可以尝试重新下载后再转发。',
              showCancel: false
            })
          }
        })
        return
      }

      uni.showModal({
        title: '当前环境不支持',
        content: '只有微信小程序环境支持直接转发文件。你可以在开发者工具/真机中重试，或把下载地址发到电脑浏览器下载。',
        showCancel: false
      })
    },

    downloadErrorLog() {
      if (!this.result || !this.result.import_log_id) return
      const token = String(uni.getStorageSync('admin_token') || '').trim()
      if (!token) {
        uni.redirectTo({ url: '/pages/admin-login/admin-login' })
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

.file-row {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

.row {
  display: flex;
  align-items: center;
  margin-bottom: 24px;
}

.label {
  width: 80px;
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

.seg {
  flex: 1;
  display: flex;
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
  background: rgba(15, 23, 42, 0.04);
  padding: 4px;
}

.seg-item {
  flex: 1;
  text-align: center;
  height: 40px;
  line-height: 40px;
  font-size: 14px;
  color: rgba(15, 23, 42, 0.72);
  background-color: transparent;
  border-radius: 10px;
}

.seg-item.active {
  background-color: #fff;
  color: #fff;
  color: var(--text);
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
}

.btn-row {
  display: flex;
  gap: 12px;
}

.btn {
  flex: 1;
  background-color: var(--brand);
  color: #fff;
  border-radius: 12px;
  height: 48px;
  line-height: 48px;
  font-size: 15px;
  font-weight: 600;
}

.btn-secondary {
  flex: 1;
  background-color: transparent;
  color: var(--brand);
  border: 1px solid rgba(31, 75, 153, 0.55);
  border-radius: 12px;
  height: 48px;
  line-height: 48px;
  font-size: 15px;
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

.tip {
  margin-top: 10px;
  font-size: 12px;
  color: var(--muted);
}

.footer {
  margin-top: 24px;
}
</style>
