<template>
  <view class="container">
    <view class="card">
      <text class="title">用户服务协议</text>

      <text class="p">欢迎使用“青少年无人机大赛”小程序（以下简称“本小程序”）。为使用本小程序服务，请你仔细阅读并充分理解本协议。你点击同意或开始使用，即视为你已阅读并同意本协议。</text>

      <text class="h">一、服务内容</text>
      <text class="p">本小程序为赛事报名、报名查询、获奖证书查询与下载等功能提供技术服务。</text>

      <text class="h">二、账号与登录</text>
      <text class="p">你可通过微信授权登录使用本小程序。你应保证提供信息真实、准确、完整。</text>

      <text class="h">三、信息收集与使用</text>
      <text class="p">为实现报名、报名查询、证书查询与联系沟通等功能，本小程序可能收集并使用你提交的手机号等信息。具体收集范围、使用目的、方式与用途详见《隐私政策》。</text>

      <text class="h">四、用户义务</text>
      <text class="p">你不得利用本小程序从事违法违规活动，不得恶意提交虚假报名信息，不得干扰本小程序正常运行。</text>

      <text class="h">五、免责与责任限制</text>
      <text class="p">因不可抗力、网络故障、系统维护等导致服务中断或数据延迟的，本小程序将在合理范围内尽力恢复，但不承担由此造成的间接损失。</text>

      <text class="h">六、协议变更</text>
      <text class="p">我们可能根据业务或法律法规要求对本协议进行更新。更新后在本小程序公示，继续使用即表示你接受更新内容。</text>

      <text class="h">七、联系我们</text>
      <text class="p">如你对本协议或服务有任何疑问，可通过赛事组织方公布的渠道与我们联系。</text>
    </view>
  </view>
</template>

<script>
export default {
  data() {
    return {}
  }
}
</script>

<style scoped>
.container {
  min-height: 100vh;
  padding: 16px;
  box-sizing: border-box;
}

.card {
  background: #ffffff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}

.title {
  display: block;
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 12px;
}

.h {
  display: block;
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  margin-top: 14px;
  margin-bottom: 6px;
}

.p {
  display: block;
  font-size: 13px;
  color: rgba(15, 23, 42, 0.75);
  line-height: 20px;
}
</style>
