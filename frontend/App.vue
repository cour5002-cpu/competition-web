<script>
export default {
  onLaunch() {
    try {
      const cur = String(uni.getStorageSync('base_url') || '').trim()
      if (!cur) {
        uni.setStorageSync('base_url', 'https://drone-race.starweave.net')
      }
    } catch (e) {}
  },
  onShow() {
  },
  onHide() {
  }
}
</script>

<style>
:root,
page {
  --bg: #f4f6fa;
  --card: #ffffff;
  --text: #0f172a;
  --muted: rgba(15, 23, 42, 0.62);
  --border: rgba(15, 23, 42, 0.12);
  --surface: rgba(15, 23, 42, 0.05);
  --brand: #1f4b99;
  --brand-2: #0ea5a4;
  --danger: #ef4444;
  --radius: 14px;
  --radius-sm: 12px;
  --shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

page {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Helvetica Neue', Arial, 'Microsoft YaHei', sans-serif;
}

view,
text,
button,
input,
textarea {
  box-sizing: border-box;
}

.page {
  min-height: 100vh;
  padding: 18px;
}

.card {
  background: var(--card);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}

.card-pad {
  padding: 16px;
}

.title-lg {
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
}

.text-muted {
  color: var(--muted);
}

.btn-primary {
  background: var(--brand);
  color: #ffffff;
  border-radius: var(--radius-sm);
  font-weight: 600;
}

.btn-ghost {
  background: transparent;
  color: var(--brand);
  border: 1px solid rgba(31, 75, 153, 0.55);
  border-radius: var(--radius-sm);
  font-weight: 600;
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
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: #ffffff;
  font-size: 15px;
  color: var(--text);
}
</style>
