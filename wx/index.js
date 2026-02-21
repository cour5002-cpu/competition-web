Page({
  data: {
    // 这里的规则必须对应你后端的 config.COMPETITION_RULES
    rules: {
      '个人飞行赛': { '物流搬运': { count: 1, levels: ['小学', '初中'] } },
      '无人机足球': { '3v3足球': { count: 3, levels: ['初中', '高中'] } }
    },
    multiArray: [
      [{ name: '个人飞行赛' }, { name: '无人机足球' }],
      [{ name: '物流搬运' }]
    ],
    selectedCategory: '个人飞行赛',
    selectedTask: '物流搬运',
    selectedLevel: '',
    levelList: ['小学', '初中', '高中'],
    neededCount: 1,
    playerNames: [] // 暂存选手姓名
  },

  // 处理选手姓名输入，封装成后端需要的对象数组
  onPlayerInput: function(e) {
    let index = e.currentTarget.dataset.index;
    let names = this.data.playerNames;
    names[index] = { "participant_name": e.detail.value };
    this.setData({ playerNames: names });
  },

  submitRegistration: function(e) {
    const val = e.detail.value;
    const postData = {
      category: this.data.selectedCategory,
      task: this.data.selectedTask,
      education_level: this.data.selectedLevel,
      participant_count: this.data.neededCount,
      school_name: val.school_name,
      contact_name: val.contact_name,
      contact_phone: val.contact_phone,
      contact_email: val.contact_email,
      participants: this.data.playerNames // 这里就是后端要的 list
    };

    wx.showLoading({ title: '提交中' });
    wx.request({
      url: 'http://127.0.0.1:5001/api/register', // 确保路径包含蓝图前缀
      method: 'POST',
      data: postData,
      success: (res) => {
        if (res.data.success) {
          wx.showToast({ title: '报名成功' });
        } else {
          wx.showModal({ title: '失败', content: res.data.message + (res.data.errors ? ": " + res.data.errors.join(',') : "") });
        }
      },
      fail: () => wx.showToast({ title: '网络错误', icon: 'none' }),
      complete: () => wx.hideLoading()
    });
  }
});