<template>
  <view class="container">
    <view class="card">
      <text class="title">隐私政策</text>

      <text class="p">我们非常重视你的个人信息与隐私保护。本政策说明我们在你使用“青少年无人机大赛”小程序过程中，如何收集、使用、存储与保护你的个人信息，以及你享有的权利。</text>

      <text class="h">一、我们收集的信息</text>
      <text class="p">1. 你在报名时填写的信息：学校、学段、参赛项目、联系人信息、指导老师信息、领队信息、参赛人手机号、参赛人邮箱等。</text>
      <text class="p">2. 你在报名查询/获奖查询时输入的信息：报名时填写的手机号等用于查询的必要信息。</text>
      <text class="p">3. 你在微信授权登录时提供的头像、昵称等公开信息（以微信授权页面实际展示为准）。</text>

      <text class="h">二、我们如何使用信息</text>
      <text class="p">我们仅在实现以下目的所必需的范围内使用你的信息：</text>
      <text class="p">1. 完成赛事报名、报名审核与状态查询。</text>
      <text class="p">2. 生成与查询获奖证书，并提供下载服务。</text>
      <text class="p">3. 用于联系沟通、通知报名结果或退回原因（可能通过电话/短信/邮件/公众号通知等方式，以最终配置为准）。</text>
      <text class="p">4. 为保障服务安全、排查故障与改进体验进行必要的日志记录与分析。</text>

      <text class="h">三、信息的存储与保护</text>
      <text class="p">我们会采取合理的技术与管理措施保护你的信息安全，包括但不限于访问控制、加密存储等。我们仅在实现本政策所述目的所必需的期限内保存你的信息，超过保存期限后将进行删除或匿名化处理（法律法规另有规定的除外）。</text>

      <text class="h">四、信息共享与披露</text>
      <text class="p">除非法律法规另有规定或取得你的明确同意，我们不会向第三方共享或公开披露你的个人信息。为完成赛事组织管理需要，相关信息可能在赛事组织方/承办方的授权范围内使用。</text>

      <text class="h">五、你的权利</text>
      <text class="p">你有权查询、更正你提交的个人信息。如需删除信息或撤回授权，可通过赛事组织方公布的联系方式与我们联系，我们将在合理期限内处理。</text>

      <text class="h">六、政策更新</text>
      <text class="p">我们可能适时更新本政策，并在本小程序公示。更新后继续使用即视为你同意更新内容。</text>
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
