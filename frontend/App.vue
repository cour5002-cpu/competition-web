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
</style>
