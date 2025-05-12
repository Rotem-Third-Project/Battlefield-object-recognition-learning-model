<template>
  <div class="dashboard">
    <VideoFeed />
    <CrosshairCanvas />
    <ObjectList />
    <HUD />
  </div>
</template>

<script>
import VideoFeed from '@/components/VideoFeed.vue'
import CrosshairCanvas from '@/components/CrosshairCanvas.vue'
import ObjectList from '@/components/ObjectList.vue'
import HUD from '@/components/HUD.vue'

export default {
  name: 'DashboardView',
  components: {
    VideoFeed,
    CrosshairCanvas,
    ObjectList,
    HUD
  }
}
</script>

<style scoped>
.dashboard {
  position: relative;
  width: 100%;
  height: 100vh;
  background-color: #000;
  overflow: hidden;
}
</style> 