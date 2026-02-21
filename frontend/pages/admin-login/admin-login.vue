<template>
  <view class="container">
    <view class="card">
      <text class="title">管理员登录</text>

      <view class="form-item">
        <text class="label">账号</text>
        <input v-model="username" class="input" type="text" placeholder="请输入管理员账号" />
      </view>

      <view class="form-item">
        <text class="label">密码</text>
        <input v-model="password" class="input" type="password" placeholder="请输入密码" />
      </view>

      <button class="btn" :disabled="loading" @click="handleLogin">
        {{ loading ? '登录中...' : '登录' }}
      </button>

      <button class="btn-secondary" @click="goStudent">
        返回学生端
      </button>
    </view>
  </view>
</template>

<script>
import * as requestApi from '../../utils/request'

const request = requestApi && requestApi.default ? requestApi.default : requestApi

export default {
  data() {
    return {
      username: '',
      password: '',
      loading: false
    }
  },

  onHide() {
    this.resetPage()
  },

  onUnload() {
    this.resetPage()
  },

  methods: {
    resetPage() {
      this.username = ''
      this.password = ''
      this.loading = false
    },
    goStudent() {
      uni.switchTab({ url: '/pages/index/index' })
    },

    async handleLogin() {
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
          uni.redirectTo({ url: '/pages/admin-home/admin-home' })
          return
        }

        uni.showModal({
          title: '登录失败',
          content: (res && res.message) ? String(res.message) : '账号或密码错误',
          showCancel: false
        })
      } catch (e) {
        uni.showModal({
          title: '登录失败',
          content: '网络错误，请稍后重试',
          showCancel: false
        })
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
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  box-sizing: border-box;
}

.card {
  width: 100%;
  background-color: var(--card);
  border-radius: 14px;
  padding: 20px;
  box-shadow: var(--shadow);
  box-sizing: border-box;
}

.title {
  display: block;
  font-size: 20px;
  font-weight: bold;
  color: var(--text);
  margin-bottom: 18px;
  text-align: center;
}

.form-item {
  margin-bottom: 12px;
}

.label {
  display: block;
  font-size: 14px;
  color: rgba(15, 23, 42, 0.72);
  margin-bottom: 8px;
}

.input {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: 12px;
  height: 44px;
  line-height: 44px;
  padding: 0 12px;
  font-size: 16px;
  background-color: #fff;
  box-sizing: border-box;
}

.btn {
  margin-top: 10px;
  background-color: var(--brand);
  color: #fff;
  border-radius: 12px;
}

.btn-secondary {
  margin-top: 10px;
  background-color: transparent;
  color: var(--brand);
  border: 1px solid rgba(31, 75, 153, 0.55);
  border-radius: 12px;
}
</style>
