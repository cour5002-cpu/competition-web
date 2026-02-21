<template>
  <view class="auth-page">
    <view class="hero">
      <image class="hero-logo" src="/static/logo.png" mode="aspectFit"></image>
      <text class="hero-title">青少年无人机大赛</text>
      <text class="hero-subtitle">报名、查询、证书一站式完成</text>
    </view>

    <view class="panel">
      <view class="segmented">
        <view class="segmented-item" :class="{ active: mode === 'wechat' }" @click="mode = 'wechat'">微信登录</view>
        <view class="segmented-item" :class="{ active: mode === 'admin' }" @click="mode = 'admin'">账号密码登录</view>
      </view>

      <view v-if="mode === 'wechat'" class="panel-body">
        <text class="panel-title">微信授权登录</text>
        <text class="panel-desc">用于报名与证书查询。我们不会公开你的微信信息。</text>
        <button class="btn btn-wechat" :disabled="loading" @click="handleWeChatLogin">
          {{ loading ? '登录中...' : '微信一键登录' }}
        </button>
        <text v-if="errorMsg" class="form-error">{{ errorMsg }}</text>
      </view>

      <view v-else class="panel-body">
        <text class="panel-title">账号密码登录</text>
        <text class="panel-desc">使用账号密码登录后台管理。</text>

        <view class="form-item">
          <text class="form-label">账号</text>
          <input v-model="username" class="form-input" type="text" placeholder="请输入账号" />
        </view>

        <view class="form-item">
          <text class="form-label">密码</text>
          <input v-model="password" class="form-input" type="password" placeholder="请输入密码" />
        </view>

        <button class="btn btn-primary" :disabled="loading" @click="handleAdminLogin">
          {{ loading ? '登录中...' : '登录后台' }}
        </button>

        <text v-if="errorMsg" class="form-error">{{ errorMsg }}</text>
      </view>
    </view>

    <view class="footer">
      <text class="footer-text">© {{ year }} 青少年无人机大赛</text>
    </view>
  </view>
</template>

<script>
import auth from '../../utils/auth'
import * as requestApi from '../../utils/request'

const request = requestApi && requestApi.default ? requestApi.default : requestApi

export default {
  data() {
    return {
      mode: 'wechat',
      username: '',
      password: '',
      loading: false,
      errorMsg: '',
      year: new Date().getFullYear()
    }
  },

  onLoad(options) {
    const m = String((options && options.mode) || '').trim()
    if (m === 'admin' || m === 'wechat') this.mode = m
  },

  methods: {
    async handleWeChatLogin() {
      if (this.loading) return
      this.errorMsg = ''
      this.loading = true
      try {
        const ok = await auth.loginWithWeChatProfile()
        if (!ok) {
          this.errorMsg = '授权或登录失败，请重试'
          return
        }

        const redirect = uni.getStorageSync('post_login_redirect')
        if (redirect) {
          try { uni.removeStorageSync('post_login_redirect') } catch (e) {}
          if (String(redirect).startsWith('/pages/register/')) {
            uni.switchTab({ url: '/pages/register/register' })
            return
          }
          if (String(redirect).startsWith('/pages/my-applications/')) {
            uni.switchTab({ url: '/pages/my-applications/my-applications' })
            return
          }
          uni.reLaunch({ url: String(redirect) })
          return
        }

        uni.switchTab({ url: '/pages/index/index' })
      } finally {
        this.loading = false
      }
    },

    async handleAdminLogin() {
      if (this.loading) return
      this.errorMsg = ''

      const username = String(this.username || '').trim()
      const password = String(this.password || '').trim()
      if (!username || !password) {
        uni.showToast({ title: '请输入账号和密码', icon: 'none' })
        return
      }

      this.loading = true
      try {
        const res = await request.post('/api/admin/login', { username, password })
        if (res && res.success && res.data && res.data.token) {
          uni.setStorageSync('admin_token', res.data.token)
          uni.reLaunch({ url: '/pages/admin-home/admin-home' })
          return
        }
        this.errorMsg = (res && res.message) ? String(res.message) : '账号或密码错误'
      } catch (e) {
        this.errorMsg = '网络错误，请稍后重试'
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  padding: 24px 18px 18px;
  box-sizing: border-box;
  background: linear-gradient(180deg, rgba(31, 75, 153, 0.14) 0%, rgba(244, 246, 250, 1) 38%);
}

.hero {
  padding: 18px 10px 14px;
  text-align: center;
}

.hero-logo {
  width: 54px;
  height: 54px;
  margin: 0 auto 10px;
}

.hero-title {
  display: block;
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: 0.5px;
}

.hero-subtitle {
  display: block;
  font-size: 13px;
  color: rgba(15, 23, 42, 0.68);
  margin-top: 6px;
}

.panel {
  background: #ffffff;
  border-radius: 14px;
  padding: 14px 14px 16px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

.segmented {
  display: flex;
  background: rgba(15, 23, 42, 0.05);
  border-radius: 12px;
  padding: 4px;
  box-sizing: border-box;
}

.segmented-item {
  flex: 1;
  text-align: center;
  height: 34px;
  line-height: 34px;
  border-radius: 10px;
  font-size: 13px;
  color: rgba(15, 23, 42, 0.7);
}

.segmented-item.active {
  background: #ffffff;
  color: #0f172a;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
}

.panel-body {
  padding-top: 14px;
}

.panel-title {
  display: block;
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.panel-desc {
  display: block;
  font-size: 12px;
  color: rgba(15, 23, 42, 0.62);
  line-height: 18px;
  margin-top: 6px;
  margin-bottom: 14px;
}

.form-item {
  margin-bottom: 12px;
}

.form-label {
  display: block;
  font-size: 12px;
  color: rgba(15, 23, 42, 0.72);
  margin-bottom: 8px;
}

.form-input {
  width: 100%;
  height: 44px;
  line-height: 44px;
  padding: 0 12px;
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: rgba(255, 255, 255, 1);
  box-sizing: border-box;
  font-size: 15px;
  color: #0f172a;
}

.btn {
  width: 100%;
  border-radius: 12px;
  font-weight: 600;
}

.btn-primary {
  background: #1f4b99;
  color: #ffffff;
}

.btn-wechat {
  background: #07c160;
  color: #ffffff;
}

.form-error {
  display: block;
  margin-top: 12px;
  color: #ef4444;
  font-size: 12px;
}

.footer {
  padding: 14px 0 6px;
  text-align: center;
}

.footer-text {
  font-size: 11px;
  color: rgba(15, 23, 42, 0.5);
}
</style>
