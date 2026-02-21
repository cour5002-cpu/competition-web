<template>
  <view class="container">
    <view class="header">
      <text class="title">可视化统计</text>
      <text class="subtitle">按维度统计报名数量</text>
    </view>

    <view class="card">
      <view class="row">
        <text class="label">维度</text>
        <picker :range="dimensionOptions" range-key="text" :value="dimensionIndex" @change="onDimensionChange">
          <view class="picker">{{ dimensionOptions[dimensionIndex].text }}</view>
        </picker>
      </view>

      <view class="row">
        <text class="label">展示</text>
        <view class="seg">
          <view class="seg-item" :class="chartType === 'bar' ? 'active' : ''" @click="setChartType('bar')">柱状</view>
          <view class="seg-item" :class="chartType === 'pie' ? 'active' : ''" @click="setChartType('pie')">饼状</view>
        </view>
      </view>

      <view class="row">
        <text class="label">状态</text>
        <picker :range="statusOptions" range-key="text" :value="statusIndex" @change="onStatusChange">
          <view class="picker">{{ statusOptions[statusIndex].text }}</view>
        </picker>
      </view>

      <view class="row">
        <text class="label">赛别</text>
        <picker :range="categoryOptions" range-key="text" :value="categoryIndex" @change="onCategoryChange">
          <view class="picker">{{ categoryOptions[categoryIndex].text }}</view>
        </picker>
      </view>

      <button class="btn" @click="refresh">刷新</button>
    </view>

    <view class="card" style="margin-top: 12px;">
      <view v-if="loading" class="tip">加载中...</view>
      <view v-else>
        <view v-if="!items.length" class="tip">暂无数据</view>

        <view v-else>
          <view v-if="chartType === 'bar'">
            <canvas
              class="chart-canvas"
              canvas-id="barCanvas"
              :style="{ width: canvasWidthPx + 'px', height: canvasHeightPx + 'px' }"
              :width="canvasWidthPx"
              :height="canvasHeightPx"
            ></canvas>
          </view>

          <view v-else>
            <canvas
              class="chart-canvas"
              canvas-id="pieCanvas"
              :style="{ width: canvasWidthPx + 'px', height: canvasHeightPx + 'px' }"
              :width="canvasWidthPx"
              :height="canvasHeightPx"
            ></canvas>

            <view class="legend" v-if="items && items.length">
              <view v-for="(it, idx) in items" :key="idx" class="legend-row">
                <view class="dot" :style="{ backgroundColor: colorOf(idx) }"></view>
                <view class="legend-label">{{ it.label }}</view>
                <view class="legend-right">{{ it.count }}（{{ percent(it.count) }}）</view>
              </view>
            </view>
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

const request = requestApi && requestApi.default ? requestApi.default : requestApi

export default {
  data() {
    return {
      dimensionOptions: [
        { value: 'school', text: '按学校' },
        { value: 'education_level', text: '按学段' }
      ],
      dimensionIndex: 0,

      statusOptions: [
        { value: '', text: '全部' },
        { value: 'pending', text: '待审核' },
        { value: 'approved', text: '已通过' },
        { value: 'rejected', text: '已退回' }
      ],
      statusIndex: 0,

      chartType: 'bar',
      categoryOptions: [{ value: '', text: '全部' }],
      categoryIndex: 0,

      loading: false,
      items: [],
      total: 0,
      maxCount: 0,

      canvasWidthPx: 320,
      canvasHeightPx: 240
    }
  },

  async onShow() {
    const token = String(uni.getStorageSync('admin_token') || '').trim()
    if (!token) {
      uni.reLaunch({ url: '/pages/auth/auth?mode=admin' })
      return
    }

    try {
      const sys = uni.getSystemInfoSync()
      const w = Number((sys && sys.windowWidth) || 375)
      this.canvasWidthPx = Math.max(260, w - 40)
      this.canvasHeightPx = 240
    } catch (e) {}

    await this.loadCategories()
    await this.refresh()
  },

  methods: {
    goBack() {
      uni.navigateBack({ delta: 1 })
    },

    onDimensionChange(e) {
      this.dimensionIndex = Number(e.detail.value || 0)
      this.refresh()
    },

    onStatusChange(e) {
      this.statusIndex = Number(e.detail.value || 0)
      this.refresh()
    },

    onCategoryChange(e) {
      this.categoryIndex = Number(e.detail.value || 0)
      this.refresh()
    },

    setChartType(t) {
      this.chartType = t
      this.drawChart()
    },

    async loadCategories() {
      try {
        const res = await request.get('/api/competition-rules')
        const rules = (res && res.success && res.data) ? res.data : {}
        const cats = rules && typeof rules === 'object' ? Object.keys(rules) : []
        const opts = [{ value: '', text: '全部' }].concat(cats.map(c => ({ value: c, text: c })))
        this.categoryOptions = opts
        if (this.categoryIndex >= opts.length) this.categoryIndex = 0
      } catch (e) {
        this.categoryOptions = [{ value: '', text: '全部' }]
        this.categoryIndex = 0
      }
    },

    async refresh() {
      try {
        this.loading = true
        const dim = this.dimensionOptions[this.dimensionIndex].value
        const status = this.statusOptions[this.statusIndex].value
        const category = (this.categoryOptions[this.categoryIndex] && this.categoryOptions[this.categoryIndex].value) || ''

        const params = { dimension: dim, top_n: 20 }
        if (status) params.status = status
        if (category) params.category = category

        const res = await request.get('/api/admin/stats/applications', params)
        const list = (res && res.success && res.data && res.data.items) ? res.data.items : []

        const normalized = Array.isArray(list) ? list.map(x => ({
          label: String((x && x.label) || ''),
          count: Number((x && x.count) || 0)
        })) : []

        const total = normalized.reduce((s, x) => s + (Number(x.count) || 0), 0)
        const maxCount = normalized.reduce((m, x) => Math.max(m, Number(x.count) || 0), 0)

        this.items = normalized
        this.total = total
        this.maxCount = maxCount

        this.$nextTick(() => {
          this.drawChart()
        })
      } catch (e) {
        uni.showToast({ title: '统计请求失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    },

    drawChart() {
      if (!this.items || !this.items.length) return
      if (this.chartType === 'bar') {
        this.drawBarChart()
      } else {
        this.drawPieChart()
      }
    },

    drawBarChart() {
      const ctx = uni.createCanvasContext('barCanvas', this)
      const W = Number(this.canvasWidthPx) || 320
      const H = Number(this.canvasHeightPx) || 240
      const paddingLeft = 40
      const paddingRight = 16
      const paddingTop = 16
      const paddingBottom = 44

      ctx.setFillStyle('#ffffff')
      ctx.fillRect(0, 0, W, H)

      const plotW = W - paddingLeft - paddingRight
      const plotH = H - paddingTop - paddingBottom
      const maxV = Math.max(1, Number(this.maxCount) || 1)

      // axes
      ctx.setStrokeStyle('#9ca3af')
      ctx.setLineWidth(1)
      ctx.beginPath()
      ctx.moveTo(paddingLeft, paddingTop)
      ctx.lineTo(paddingLeft, paddingTop + plotH)
      ctx.lineTo(paddingLeft + plotW, paddingTop + plotH)
      ctx.stroke()

      // y ticks
      ctx.setFontSize(10)
      ctx.setFillStyle('#6b7280')
      const ticks = 4
      for (let i = 0; i <= ticks; i++) {
        const y = paddingTop + plotH - (plotH * i) / ticks
        const v = Math.round((maxV * i) / ticks)
        ctx.setStrokeStyle('#e5e7eb')
        ctx.beginPath()
        ctx.moveTo(paddingLeft, y)
        ctx.lineTo(paddingLeft + plotW, y)
        ctx.stroke()
        ctx.fillText(String(v), 4, y + 3)
      }

      const n = this.items.length
      const gap = 10
      const barW = Math.max(8, Math.floor((plotW - gap * (n + 1)) / n))

      for (let i = 0; i < n; i++) {
        const item = this.items[i]
        const v = Number(item.count) || 0
        const h = Math.round((v / maxV) * plotH)
        const x = paddingLeft + gap + i * (barW + gap)
        const y = paddingTop + plotH - h

        ctx.setFillStyle(this.colorOf(i))
        ctx.fillRect(x, y, barW, h)

        // value on top
        ctx.setFillStyle('#111827')
        ctx.setFontSize(10)
        ctx.fillText(String(v), x, Math.max(paddingTop + 10, y - 4))

        // x labels (truncate)
        const label = String(item.label || '')
        const shortLabel = label.length > 6 ? label.slice(0, 6) + '…' : label
        ctx.setFillStyle('#374151')
        ctx.setFontSize(10)
        ctx.fillText(shortLabel, x, paddingTop + plotH + 18)
      }

      ctx.draw()
    },

    drawPieChart() {
      const ctx = uni.createCanvasContext('pieCanvas', this)
      const W = Number(this.canvasWidthPx) || 320
      const H = Number(this.canvasHeightPx) || 240

      ctx.setFillStyle('#ffffff')
      ctx.fillRect(0, 0, W, H)

      const total = Math.max(0, Number(this.total) || 0)
      if (total <= 0) {
        ctx.draw()
        return
      }

      const cx = Math.floor(W / 2)
      const cy = Math.floor(H / 2)
      const r = Math.max(40, Math.floor(Math.min(W, H) * 0.32))

      let start = -Math.PI / 2
      for (let i = 0; i < this.items.length; i++) {
        const v = Number(this.items[i].count) || 0
        const angle = (v / total) * Math.PI * 2
        const end = start + angle
        ctx.beginPath()
        ctx.moveTo(cx, cy)
        ctx.arc(cx, cy, r, start, end)
        ctx.closePath()
        ctx.setFillStyle(this.colorOf(i))
        ctx.fill()
        start = end
      }

      // inner circle for donut effect
      ctx.beginPath()
      ctx.moveTo(cx, cy)
      ctx.arc(cx, cy, Math.floor(r * 0.55), 0, Math.PI * 2)
      ctx.closePath()
      ctx.setFillStyle('#ffffff')
      ctx.fill()

      ctx.setFillStyle('#111827')
      ctx.setFontSize(12)
      ctx.fillText('总计', cx - 14, cy - 2)
      ctx.setFontSize(14)
      ctx.fillText(String(total), cx - 10, cy + 18)

      ctx.draw()
    },

    percent(count) {
      const c = Number(count) || 0
      const t = Number(this.total) || 0
      if (t <= 0) return '0%'
      const p = (c / t) * 100
      return p.toFixed(1) + '%'
    },

    colorOf(idx) {
      const colors = ['#4F46E5', '#06B6D4', '#F97316', '#10B981', '#EF4444', '#8B5CF6', '#F59E0B', '#14B8A6']
      return colors[idx % colors.length]
    }
  }
}
</script>

<style scoped>
.container {
  min-height: 100vh;
  background-color: var(--bg);
  padding: 20px;
  box-sizing: border-box;
}

.header {
  background: linear-gradient(135deg, rgba(31, 75, 153, 1) 0%, rgba(14, 165, 164, 1) 100%);
  border-radius: 12px;
  padding: 20px;
  color: #fff;
  margin-bottom: 15px;
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.18);
}

.title {
  display: block;
  font-size: 20px;
  font-weight: bold;
}

.subtitle {
  display: block;
  font-size: 12px;
  margin-top: 6px;
  opacity: 0.9;
}

.card {
  background-color: var(--card);
  border-radius: 14px;
  padding: 16px;
  box-shadow: var(--shadow);
}

.row {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.label {
  width: 60px;
  color: rgba(15, 23, 42, 0.72);
  font-size: 13px;
}

.picker {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background-color: #fff;
  color: var(--text);
  font-size: 14px;
}

.input {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background-color: #fff;
  font-size: 14px;
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
  color: var(--text);
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
}

.btn {
  margin-top: 4px;
  background-color: var(--brand);
  color: #fff;
  border-radius: 12px;
  font-weight: 600;
}

.btn-secondary {
  margin-top: 12px;
  background-color: transparent;
  color: var(--brand);
  border: 1px solid rgba(31, 75, 153, 0.55);
  border-radius: 12px;
  font-weight: 600;
}

.tip {
  color: var(--muted);
  font-size: 14px;
  text-align: center;
  padding: 12px 0;
}

.chart-canvas {
  display: block;
  background-color: #fff;
  border-radius: 12px;
}

.legend {
  margin-top: 12px;
}

.legend-row {
  display: flex;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}

.legend-label {
  flex: 1;
  font-size: 14px;
  color: var(--text);
}

.legend-right {
  font-size: 12px;
  color: var(--muted);
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 10px;
}

.footer {
  margin-top: 10px;
}
</style>
