<template>
  <view class="container">
    <view class="success-card">
      <image class="success-icon" :src="successIcon" mode="aspectFit"></image>
      <text class="success-title">报名成功！</text>
      <text class="success-message">您的报名信息已提交，请等待审核</text>
      
      <view class="next-steps">
        <text class="steps-title">后续步骤：</text>
        <view class="step-item">
          <text class="step-number">1</text>
          <text class="step-text">等待管理员审核报名信息</text>
        </view>
        <view class="step-item">
          <text class="step-number">2</text>
          <text class="step-text">审核通过后分配参赛号</text>
        </view>
        <view class="step-item">
          <text class="step-number">3</text>
          <text class="step-text">比赛结束后可查询获奖情况</text>
        </view>
      </view>
      
      <view class="action-buttons">
        <button class="btn-secondary" @click="viewMyApplications">查看我的报名</button>
        <button class="btn-primary" @click="goHome">返回首页</button>
      </view>
    </view>
  </view>
</template>

<script>
export default {
  data() {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 24 24" fill="none" stroke="#0ea5a4" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M8.2 12.2l2.3 2.4 5.1-5.2"/></svg>`
    return {
      successIcon: `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
    }
  },
  methods: {
    viewMyApplications() {
      uni.navigateTo({
        url: '/pages/application-query/application-query'
      })
    },
    
    goHome() {
      uni.switchTab({
        url: '/pages/index/index'
      })
    }
  }
}
</script>

<style scoped>
.container {
  padding: 20px;
  background-color: var(--bg);
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.success-card {
  background-color: var(--card);
  border-radius: 18px;
  padding: 40px 30px;
  text-align: center;
  box-shadow: var(--shadow);
  max-width: 350px;
  width: 100%;
}

.success-icon {
  width: 72px;
  height: 72px;
  margin: 0 auto 18px;
}

.success-title {
  display: block;
  font-size: 24px;
  font-weight: bold;
  color: var(--text);
  margin-bottom: 10px;
}

.success-message {
  display: block;
  font-size: 16px;
  color: var(--muted);
  margin-bottom: 30px;
  line-height: 1.5;
}

.next-steps {
  text-align: left;
  background-color: rgba(15, 23, 42, 0.04);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 30px;
}

.steps-title {
  display: block;
  font-size: 16px;
  font-weight: bold;
  color: var(--text);
  margin-bottom: 15px;
}

.step-item {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.step-item:last-child {
  margin-bottom: 0;
}

.step-number {
  width: 24px;
  height: 24px;
  background-color: var(--brand);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
  margin-right: 12px;
  flex-shrink: 0;
}

.step-text {
  font-size: 14px;
  color: rgba(15, 23, 42, 0.78);
  line-height: 1.4;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.btn-primary {
  background-color: var(--brand);
  color: white;
  border: none;
  border-radius: 14px;
  padding: 15px 30px;
  font-size: 16px;
  font-weight: bold;
}

.btn-secondary {
  background-color: transparent;
  color: var(--brand);
  border: 2px solid rgba(31, 75, 153, 0.55);
  border-radius: 14px;
  padding: 13px 30px;
  font-size: 16px;
}
</style>
