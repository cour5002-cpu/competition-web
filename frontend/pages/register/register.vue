<template>
  <view class="register-container">
    <view class="header">
      <text class="title">青少年无人机大赛</text>
    </view>
    
    <form @submit="handleSubmit">
      <!-- 项目大类选择 -->
      <view class="form-item">
        <text class="label">项目大类 *</text>
        <picker 
          :range="categories" 
          :value="categoryIndex" 
          @change="onCategoryChange"
          class="picker"
        >
          <view class="picker-text">
            {{ categoryIndex !== -1 ? categories[categoryIndex] : '请选择项目大类' }}
          </view>
        </picker>
      </view>
      
      <!-- 具体任务选择 -->
      <view class="form-item" v-if="tasks.length > 0">
        <text class="label">具体任务 *</text>
        <picker 
          :range="taskNames" 
          :value="taskIndex" 
          @change="onTaskChange"
          class="picker task-picker"
        >
          <view class="picker-text task-picker-text" :style="taskTextStyle">
            {{ taskIndex !== -1 ? taskNames[taskIndex] : '请选择具体任务' }}
          </view>
        </picker>
      </view>
      
      <!-- 学段选择 -->
      <view class="form-item" v-if="selectedTask">
        <text class="label">学段 *</text>
        <picker 
          :range="educationLevels" 
          :value="educationIndex" 
          @change="onEducationChange"
          class="picker"
        >
          <view class="picker-text">
            {{ educationIndex !== -1 ? educationLevels[educationIndex] : '请选择学段' }}
          </view>
        </picker>
        <text class="hint" v-if="selectedTask">
          允许学段：{{ selectedTask.allowed_levels.join('、') }}
        </text>
      </view>
      
      <!-- 行政区域联动（全国省/市/区县） -->
      <view class="form-item">
        <text class="label">行政区域 *</text>
        <picker
          mode="region"
          :value="regionValue"
          @change="onRegionPickerChange"
          class="picker"
        >
          <view class="picker-text">
            {{ regionValue && regionValue.length === 3 ? regionValue.join(' ') : '请选择省/市/区县' }}
          </view>
        </picker>
      </view>
      
      <!-- 学校信息 -->
      <view class="form-item">
        <text class="label">学校名称 *</text>
        <input 
          v-model="formData.school_name"
          type="text"
          placeholder="请输入学校名称"
          class="input"
        />
      </view>
      
      <!-- 指导老师信息 -->
      <view class="form-item">
        <text class="label">指导老师姓名 *</text>
        <input
          v-model="formData.teacher_name"
          type="text"
          placeholder="请输入指导老师姓名"
          class="input"
        />
      </view>

      <view class="form-item">
        <text class="label">指导老师电话 *</text>
        <input
          v-model="formData.teacher_phone"
          type="number"
          placeholder="请输入11位手机号"
          maxlength="11"
          class="input"
        />
      </view>

      <!-- 领队信息 -->
      <view class="form-item">
        <text class="label">领队姓名 *</text>
        <input
          v-model="formData.leader_name"
          type="text"
          placeholder="请输入领队姓名"
          class="input"
        />
      </view>

      <view class="form-item">
        <text class="label">领队电话 *</text>
        <input
          v-model="formData.leader_phone"
          type="number"
          placeholder="请输入11位手机号"
          maxlength="11"
          class="input"
        />
      </view>

      <!-- 参赛人信息 -->
      <view class="form-item">
        <text class="label">参赛人手机号 *</text>
        <input
          v-model="formData.participant_phone"
          type="number"
          placeholder="请输入11位手机号"
          maxlength="11"
          class="input"
        />
      </view>

      <view class="form-item">
        <text class="label">参赛人邮箱 *</text>
        <input
          v-model="formData.participant_email"
          type="email"
          placeholder="请输入邮箱地址"
          class="input"
        />
      </view>
      
      <!-- 选手信息 -->
      <view class="form-section" v-if="participantCount > 0">
        <text class="section-title">选手信息 *</text>
        <text class="hint">
          {{ getParticipantHint() }}
        </text>
        
        <view 
          v-for="(participant, index) in formData.participants" 
          :key="index"
          class="participant-item"
        >
          <text class="participant-label">选手{{ index + 1 }}姓名 *</text>
          <input 
            v-model="participant.participant_name"
            type="text"
            :placeholder="`请输入选手${index + 1}姓名`"
            class="input"
          />
        </view>
      </view>
      
      <!-- 提交按钮 -->
      <button 
        class="submit-btn"
        :disabled="!canSubmit"
        @click="handleSubmit"
      >
        {{ isResubmit ? '再次提交' : '提交报名' }}
      </button>
    </form>
  </view>
</template>

<script>
import request from '../../utils/request'
import auth from '../../utils/auth'

export default {
  data() {
    return {
      // 竞赛规则
      competitionRules: {},
      categories: [],
      tasks: [],
      taskNames: [],
      educationLevels: ['小学', '初中', '高中/职高（含中专）'],
      
      // 选择器索引
      categoryIndex: -1,
      taskIndex: -1,
      educationIndex: -1,

      // 全国省/市/区县 选择器
      regionValue: [],
      
      // 选中的任务
      selectedTask: null,
      participantCount: 0,
      
      // 表单数据
      formData: {
        category: '',
        task: '',
        education_level: '',
        school_region: '',
        school_city: '',
        school_district: '',
        school_name: '',
        teacher_name: '',
        teacher_phone: '',
        leader_name: '',
        leader_phone: '',
        participant_phone: '',
        participant_email: '',
        participants: []
      },

      isResubmit: false,
      resubmitApplicationId: ''
    }
  },
  
  computed: {
    canSubmit() {
      // 检查必填字段
      if (!this.formData.category || !this.formData.task || !this.formData.education_level) {
        return false
      }
      if (!this.regionValue || this.regionValue.length !== 3) {
        return false
      }
      if (!this.formData.school_name) {
        return false
      }
      if (!this.formData.teacher_name || !this.formData.teacher_phone) return false
      if (!this.formData.leader_name || !this.formData.leader_phone) return false
      if (!this.formData.participant_phone || !this.formData.participant_email) return false
      
      // 检查选手信息
      if (this.participantCount === 0) return false
      for (let i = 0; i < this.participantCount; i++) {
        if (!this.formData.participants[i] || !this.formData.participants[i].participant_name) {
          return false
        }
      }
      
      return true
    },

    taskTextStyle() {
      if (this.taskIndex === -1) return {}
      const text = String((this.taskNames && this.taskNames[this.taskIndex]) || '')
      const len = text.length
      if (len >= 46) return { fontSize: '9px' }
      if (len >= 40) return { fontSize: '10px' }
      if (len >= 34) return { fontSize: '11px' }
      if (len >= 28) return { fontSize: '12px' }
      if (len >= 22) return { fontSize: '13px' }
      return {}
    }
  },
  
  async onShow() {
    await auth.requireUserLoginOrRedirect('/pages/register/register')
    this.tryLoadResubmitFromStorage()
  },

  onLoad() {
    this.loadCompetitionRules()
  },
  
  methods: {
    tryLoadResubmitFromStorage() {
      let id = ''
      try {
        id = String(uni.getStorageSync('resubmit_application_id') || '').trim()
      } catch (e) {
        id = ''
      }

      if (!id) {
        this.isResubmit = false
        this.resubmitApplicationId = ''
        return
      }

      this.isResubmit = true
      this.resubmitApplicationId = id

      // 规则尚未加载完成时，稍后再回填
      if (!this.competitionRules || !this.categories || this.categories.length === 0) {
        return
      }

      this.loadApplicationDetailAndPrefill(id)
    },

    async loadApplicationDetailAndPrefill(id) {
      try {
        uni.showLoading({ title: '加载报名信息...' })
        const res = await request.get(`/api/my-applications/${id}`)
        uni.hideLoading()
        if (!res || !res.success || !res.data) {
          uni.showModal({
            title: '加载失败',
            content: (res && res.message) ? res.message : '无法获取报名信息',
            showCancel: false
          })
          return
        }

        const a = res.data

        // 回填基础字段
        this.formData.category = String(a.category || '')
        this.formData.task = String(a.task || '')
        this.formData.education_level = String(a.education_level || '')

        this.formData.school_region = String(a.school_region || '')
        this.formData.school_city = String(a.school_city || '')
        this.formData.school_district = String(a.school_district || '')
        this.regionValue = [this.formData.school_region, this.formData.school_city, this.formData.school_district]

        this.formData.school_name = String(a.school_name || '')
        this.formData.teacher_name = String(a.teacher_name || '')
        this.formData.teacher_phone = String(a.teacher_phone || '')
        this.formData.leader_name = String(a.leader_name || '')
        this.formData.leader_phone = String(a.leader_phone || '')
        this.formData.participant_phone = String(a.participant_phone || '')
        this.formData.participant_email = String(a.participant_email || '')

        // 选择器索引与任务/人数
        this.categoryIndex = this.categories.indexOf(this.formData.category)
        if (this.categoryIndex < 0) this.categoryIndex = -1

        if (this.formData.category && this.competitionRules && this.competitionRules[this.formData.category]) {
          this.tasks = Object.keys(this.competitionRules[this.formData.category])
          this.taskNames = this.tasks.map(task => {
            const rule = this.competitionRules[this.formData.category][task]
            return `${task} (${rule.participant_count}人)`
          })
        } else {
          this.tasks = []
          this.taskNames = []
        }

        this.taskIndex = this.tasks.indexOf(this.formData.task)
        if (this.taskIndex < 0) this.taskIndex = -1
        this.selectedTask = (this.formData.category && this.formData.task && this.competitionRules && this.competitionRules[this.formData.category])
          ? (this.competitionRules[this.formData.category][this.formData.task] || null)
          : null

        const pc = Number(a.participant_count || 0)
        this.participantCount = pc > 0 ? pc : (this.selectedTask ? this.selectedTask.participant_count : 0)

        this.educationIndex = this.educationLevels.indexOf(this.formData.education_level)
        if (this.educationIndex < 0) this.educationIndex = -1

        // 选手列表回填
        const parts = Array.isArray(a.participants) ? a.participants : []
        const sorted = parts.slice().sort((x, y) => Number(x.seq_no || 0) - Number(y.seq_no || 0))
        this.formData.participants = []
        for (let i = 0; i < this.participantCount; i++) {
          const p = sorted[i] || {}
          this.formData.participants.push({
            participant_name: String(p.participant_name || '')
          })
        }
      } catch (e) {
        uni.hideLoading()
        uni.showToast({ title: '网络错误', icon: 'error' })
      }
    },

    async loadCompetitionRules() {
      try {
        const data = await request.get('/api/competition-rules')
        if (data.success) {
          this.competitionRules = data.data
          this.categories = Object.keys(this.competitionRules)

          // 如果是退回修改场景，规则加载完后再执行回填
          if (this.isResubmit && this.resubmitApplicationId) {
            this.loadApplicationDetailAndPrefill(this.resubmitApplicationId)
          } else {
            this.tryLoadResubmitFromStorage()
          }
        }
      } catch (error) {
        console.error('加载竞赛规则失败:', error)
      }
    },
    
    onCategoryChange(e) {
      this.categoryIndex = e.detail.value
      this.formData.category = this.categories[this.categoryIndex]

      // 切换项目大类后，为避免带入旧数据，清空除 category 外的已填信息
      this.formData.task = ''
      this.formData.education_level = ''
      this.formData.school_region = ''
      this.formData.school_city = ''
      this.formData.school_district = ''
      this.formData.school_name = ''
      this.formData.teacher_name = ''
      this.formData.teacher_phone = ''
      this.formData.leader_name = ''
      this.formData.leader_phone = ''
      this.formData.participant_phone = ''
      this.formData.participant_email = ''
      this.regionValue = []
      
      // 重置任务选择
      this.taskIndex = -1
      this.educationIndex = -1
      this.selectedTask = null
      this.participantCount = 0
      this.formData.participants = []
      
      // 加载该大类下的任务
      if (this.formData.category) {
        this.tasks = Object.keys(this.competitionRules[this.formData.category])
        this.taskNames = this.tasks.map(task => {
          const rule = this.competitionRules[this.formData.category][task]
          return `${task} (${rule.participant_count}人)`
        })
      } else {
        this.tasks = []
        this.taskNames = []
      }
    },
    
    onTaskChange(e) {
      this.taskIndex = e.detail.value
      const taskKey = this.tasks[this.taskIndex]
      this.formData.task = taskKey
      this.selectedTask = this.competitionRules[this.formData.category][taskKey]
      this.participantCount = this.selectedTask.participant_count
      
      // 重置学段选择
      this.educationIndex = -1
      this.formData.education_level = ''
      
      // 初始化选手信息
      this.formData.participants = []
      for (let i = 0; i < this.participantCount; i++) {
        this.formData.participants.push({
          participant_name: ''
        })
      }
    },
    
    onEducationChange(e) {
      this.educationIndex = e.detail.value
      this.formData.education_level = this.educationLevels[this.educationIndex]
    },

    onRegionPickerChange(e) {
      const value = e.detail.value
      this.regionValue = value
      this.formData.school_region = value[0] || ''
      this.formData.school_city = value[1] || ''
      this.formData.school_district = value[2] || ''
    },
    
    getParticipantHint() {
      if (!this.selectedTask) return ''
      
      const hints = {
        '无人机足球': '第一位默认为前锋，其余为后卫',
        '机器人格斗': '第一位默认为主力，其余为辅助',
        '编程挑战': '按顺序排列，第一位为队长'
      }
      
      return hints[this.formData.category] || ''
    },
    
    async handleSubmit() {
      if (!this.canSubmit) {
        uni.showToast({
          title: '请完善必填信息',
          icon: 'error'
        })
        return
      }
      
      try {
        uni.showLoading({
          title: '提交中...'
        })

        const payload = {
          ...this.formData,
          participant_count: this.participantCount
        }

        const data = (this.isResubmit && this.resubmitApplicationId)
          ? await request.put(`/api/my-applications/${this.resubmitApplicationId}`, payload)
          : await request.post('/api/register', payload)

        uni.hideLoading()

        if (data.success) {
          uni.showToast({
            title: this.isResubmit ? '已再次提交' : '报名成功',
            icon: 'success'
          })

          const SUBSCRIBE_STATE_KEY = 'wx_subscribe_audit_state'
          const SUBSCRIBE_STATE_ACCEPTED = 'accepted'
          const SUBSCRIBE_STATE_IGNORED = 'ignored'

          const getSubscribeState = () => {
            try {
              const v = uni.getStorageSync(SUBSCRIBE_STATE_KEY)
              return String(v || '').trim()
            } catch (e) {
              return ''
            }
          }

          const setSubscribeState = (v) => {
            try {
              uni.setStorageSync(SUBSCRIBE_STATE_KEY, v)
            } catch (e) {}
          }

          const shouldAskSubscribe = () => {
            const state = getSubscribeState()
            if (state === SUBSCRIBE_STATE_ACCEPTED) return false
            if (this.isResubmit) return state === SUBSCRIBE_STATE_IGNORED
            return !state
          }

          const askSubscribeOnce = async () => {
            const tmplId = 'a1s7ioFW5JEliylSx1hGJSd35x01NrKTFadK54XnuHY'
            return await new Promise((resolve) => {
              try {
                uni.showModal({
                  title: '订阅通知',
                  content: '是否订阅“报名审核结果通知”？订阅后管理员通过/退回会通知你。',
                  confirmText: '订阅',
                  cancelText: '暂不',
                  success: (r) => {
                    if (!r || !r.confirm) {
                      setSubscribeState(SUBSCRIBE_STATE_IGNORED)
                      resolve(false)
                      return
                    }

                    try {
                      const fn = (typeof wx !== 'undefined' && wx && typeof wx.requestSubscribeMessage === 'function')
                        ? wx.requestSubscribeMessage
                        : ((typeof uni !== 'undefined' && uni && typeof uni.requestSubscribeMessage === 'function') ? uni.requestSubscribeMessage : null)
                      if (!fn) {
                        uni.showToast({ title: '当前环境不支持订阅', icon: 'none' })
                        setSubscribeState(SUBSCRIBE_STATE_IGNORED)
                        resolve(false)
                        return
                      }

                      fn({
                        tmplIds: [tmplId],
                        success: (res) => {
                          let status = ''
                          try {
                            if (res && typeof res === 'object') {
                              const s = res[tmplId]
                              if (s) status = String(s)
                            }
                          } catch (e) {}

                          if (status === 'accept') {
                            setSubscribeState(SUBSCRIBE_STATE_ACCEPTED)
                            uni.showToast({ title: '订阅成功', icon: 'none' })
                            resolve(true)
                            return
                          }

                          setSubscribeState(SUBSCRIBE_STATE_IGNORED)
                          const errMsg = (res && res.errMsg) ? String(res.errMsg) : ''
                          const detail = status ? `状态：${status}` : ''
                          uni.showModal({
                            title: '订阅未生效',
                            content: [detail, errMsg].filter(Boolean).join('\n') || '订阅失败/已取消',
                            showCancel: false,
                            success: () => resolve(false)
                          })
                        },
                        fail: (err) => {
                          setSubscribeState(SUBSCRIBE_STATE_IGNORED)
                          const msg = (err && err.errMsg) ? String(err.errMsg) : '订阅失败/已取消'
                          uni.showModal({
                            title: '订阅失败',
                            content: msg,
                            showCancel: false,
                            success: () => resolve(false)
                          })
                        }
                      })
                    } catch (e) {
                      setSubscribeState(SUBSCRIBE_STATE_IGNORED)
                      uni.showToast({ title: '订阅失败', icon: 'none' })
                      resolve(false)
                    }
                  },
                  fail: () => {
                    setSubscribeState(SUBSCRIBE_STATE_IGNORED)
                    resolve(false)
                  }
                })
              } catch (e) {
                setSubscribeState(SUBSCRIBE_STATE_IGNORED)
                resolve(false)
              }
            })
          }

          if (shouldAskSubscribe()) {
            try {
              await askSubscribeOnce()
            } catch (e) {}
          }

          if (this.isResubmit) {
            try {
              uni.removeStorageSync('resubmit_application_id')
            } catch (e) {}
            this.isResubmit = false
            this.resubmitApplicationId = ''
          }
          
          // 重置表单
          this.resetForm()

          uni.navigateTo({
            url: '/pages/success/success'
          })
        } else {
          let msg = data.message || '提交失败，请重试'
          try {
            if (Array.isArray(data.errors) && data.errors.length > 0) {
              const joined = data.errors.join('\n')
              if (joined.includes('仅允许学段')) {
                msg = '学段不符合报名要求，请重新选择填写\n\n' + joined
              } else {
                msg = msg + '\n\n' + joined
              }
            }
          } catch (e) {}

          uni.showModal({
            title: '报名失败',
            content: msg,
            showCancel: false
          })
        }
      } catch (error) {
        uni.hideLoading()
        uni.showToast({
          title: '网络错误',
          icon: 'error'
        })
      }
    },
    
    resetForm() {
      this.categoryIndex = -1
      this.taskIndex = -1
      this.educationIndex = -1
      this.regionValue = []
      this.selectedTask = null
      this.participantCount = 0
      this.tasks = []
      this.taskNames = []
      
      this.formData = {
        category: '',
        task: '',
        education_level: '',
        school_region: '',
        school_city: '',
        school_district: '',
        school_name: '',
        teacher_name: '',
        teacher_phone: '',
        leader_name: '',
        leader_phone: '',
        participant_phone: '',
        participant_email: '',
        participants: []
      }
    }
  }
}
</script>

<style scoped>
.register-container {
  padding: 20px;
  background-color: var(--bg);
  min-height: 100vh;
}

.header {
  text-align: center;
  margin-bottom: 30px;
}

.title {
  font-size: 24px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: 0.5px;
}

.form-item {
  margin-bottom: 20px;
  background-color: var(--card);
  padding: 15px;
  border-radius: 14px;
  box-shadow: var(--shadow);
}

.form-section {
  margin-bottom: 20px;
  background-color: var(--card);
  padding: 15px;
  border-radius: 14px;
  box-shadow: var(--shadow);
}

.label {
  display: block;
  font-size: 13px;
  color: rgba(15, 23, 42, 0.78);
  margin-bottom: 8px;
}

.section-title {
  display: block;
  font-size: 18px;
  font-weight: bold;
  color: var(--text);
  margin-bottom: 15px;
}

.picker {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: 12px;
  height: 44px;
  padding: 0 12px;
  background-color: #fff;
  box-sizing: border-box;
  display: flex;
  align-items: center;
}

.task-picker {
  padding: 0 6px;
}

.picker-text {
  width: 100%;
  color: var(--text);
  font-size: 16px;
  box-sizing: border-box;
  line-height: 44px;
}

.task-picker-text {
  white-space: nowrap;
  overflow: hidden;
  line-height: 44px;
  letter-spacing: -0.2px;
}

.input {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: 12px;
  height: 44px;
  padding: 0 12px;
  font-size: 16px;
  background-color: #fff;
  box-sizing: border-box;
  line-height: 44px;
}

.hint {
  font-size: 12px;
  color: var(--muted);
  margin-top: 5px;
  display: block;
}

.participant-item {
  margin-bottom: 15px;
}

.participant-label {
  display: block;
  font-size: 14px;
  color: rgba(15, 23, 42, 0.78);
  margin-bottom: 5px;
}

.submit-btn {
  width: 100%;
  background-color: var(--brand);
  color: white;
  border: none;
  border-radius: 12px;
  padding: 15px;
  font-size: 18px;
  font-weight: bold;
  margin-top: 30px;
}

.submit-btn[disabled] {
  background-color: #ccc;
  color: #999;
}
</style>
