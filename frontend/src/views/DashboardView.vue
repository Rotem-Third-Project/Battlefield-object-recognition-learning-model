<template>
  <div class="dashboard">
    <div class="main-container">
      <VideoSection />
      <ObjectList />
    </div>
    <HUD />
  </div>
</template>

<script>
import VideoSection from '@/components/VideoSection.vue'
import ObjectList from '@/components/ObjectList.vue'
import HUD from '@/components/HUD.vue'

export default {
  name: 'DashboardView',
  components: {
    VideoSection,
    ObjectList,
    HUD
  }
}
</script>

<style>
body {
  margin: 0;
  font-family: "Share Tech Mono", monospace;
  background-color: #0a0a0a;
  color: #00ff00;
  padding: 1rem;
  font-size: 1rem;
}

.dashboard {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.main-container {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  gap: 2rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
  flex: 1;
}

h3 {
  margin: 0.5rem 0;
  text-align: center;
  font-size: 1.5rem;
}
</style> 