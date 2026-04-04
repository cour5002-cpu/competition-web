import request from './request'

const TOKEN_KEY = 'user_token'
const USER_INFO_KEY = 'user_profile'
const POST_LOGIN_REDIRECT_KEY = 'post_login_redirect'

export const hasUserToken = () => {
  const raw = uni.getStorageSync(TOKEN_KEY)
  const token = String(raw || '').trim()
  if (!token) return false
  if (token === 'undefined' || token === 'null' || token === 'false' || token === '0') return false
  return true
}

export const confirmUserLoginOrRedirect = async (
  redirectUrl = '/pages/index/index',
  modalOptions = {}
) => {
  if (hasUserToken()) return true

  try {
    uni.setStorageSync(POST_LOGIN_REDIRECT_KEY, redirectUrl)
  } catch (e) {}

  const title = (modalOptions && modalOptions.title) ? String(modalOptions.title) : '需要登录'
  const content = (modalOptions && modalOptions.content)
    ? String(modalOptions.content)
    : '该功能需要先登录，是否现在去登录？'

  const confirmed = await new Promise((resolve) => {
    uni.showModal({
      title,
      content,
      confirmText: '去登录',
      cancelText: '取消',
      success: (res) => resolve(!!(res && res.confirm)),
      fail: () => resolve(false)
    })
  })

  if (!confirmed) return false

  const pages = (typeof getCurrentPages === 'function') ? getCurrentPages() : []
  const current = pages && pages.length ? pages[pages.length - 1] : null
  const route = current && current.route ? `/${current.route}` : ''
  if (route === '/pages/auth/auth') return false

  uni.reLaunch({
    url: '/pages/auth/auth'
  })
  return false
}

export const requireUserLoginOrRedirect = async (redirectUrl = '/pages/index/index') => {
  if (hasUserToken()) return true

  try {
    uni.setStorageSync(POST_LOGIN_REDIRECT_KEY, redirectUrl)
  } catch (e) {}

  const pages = (typeof getCurrentPages === 'function') ? getCurrentPages() : []
  const current = pages && pages.length ? pages[pages.length - 1] : null
  const route = current && current.route ? `/${current.route}` : ''
  if (route === '/pages/auth/auth') return false

  uni.reLaunch({
    url: '/pages/auth/auth'
  })
  return false
}

export const loginWithWeChatProfile = async () => {
  const token = uni.getStorageSync(TOKEN_KEY)
  if (token) return true

  let userInfo
  try {
    userInfo = await new Promise((resolve, reject) => {
      uni.getUserProfile({
        desc: '用于报名与获奖证书查询',
        success: (res) => resolve(res && res.userInfo ? res.userInfo : {}),
        fail: reject
      })
    })
  } catch (e) {
    return false
  }

  uni.setStorageSync(USER_INFO_KEY, userInfo || {})

  let loginRes
  try {
    loginRes = await new Promise((resolve, reject) => {
      uni.login({
        provider: 'weixin',
        success: resolve,
        fail: reject
      })
    })
  } catch (e) {
    uni.showModal({
      title: '登录失败',
      content: '未获取到微信登录 code',
      showCancel: false
    })
    return false
  }

  const code = (loginRes && loginRes.code) ? String(loginRes.code) : ''
  if (!code) {
    uni.showModal({
      title: '登录失败',
      content: '未获取到微信登录 code',
      showCancel: false
    })
    return false
  }

  const res = await request.post('/api/wx/login', { code, user_info: userInfo || {} })
  if (res && res.success && res.data && res.data.token) {
    uni.setStorageSync(TOKEN_KEY, res.data.token)
    return true
  }

  uni.showModal({
    title: '登录失败',
    content: (res && res.message) || '微信登录失败，请稍后重试',
    showCancel: false
  })
  return false
}

export const logoutUser = () => {
  try {
    uni.removeStorageSync(TOKEN_KEY)
  } catch (e) {}
}

export default {
  hasUserToken,
  requireUserLoginOrRedirect,
  confirmUserLoginOrRedirect,
  loginWithWeChatProfile,
  logoutUser
}
