<template>
  <div class="dashboard">
    <div class="left-panel">
      <VideoSection ref="videoSection" :selectedObjectId="selectedObjectId" />
    </div>
    <div class="right-panel">
      <ObjectList @object-selected="onObjectSelected" />
    </div>
    <div class="bottom-panel">
      <HUD />
    </div>
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
  },
  data() {
    return {
      selectedObjectId: null
    }
  },
  methods: {
    onObjectSelected(obj) {
      this.selectedObjectId = obj ? obj.id : null
    }
  }
}
</script>

<style>
body {
  margin: 0;
  padding: 0;
  font-family: "Share Tech Mono", monospace;
  background-color: #0a0a0a;
  color: #00ff00;
  font-size: 1rem;
  overflow: hidden;
  width: 100vw;
  height: 100vh;
}

.dashboard {
  display: grid;
  grid-template-columns: 3fr 1fr;
  grid-template-rows: calc(100vh - 150px) 150px;
  grid-template-areas: 
    "video sidebar"
    "hud hud";
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  gap: 0;
  margin: 0;
  padding: 0;
}

.left-panel {
  grid-area: video;
  overflow: hidden;
  border-right: 1px solid #00ff00;
  border-bottom: 1px solid #00ff00;
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0;
  display: flex;
  justify-content: center;
  align-items: center;
}

.right-panel {
  grid-area: sidebar;
  overflow-y: auto;
  background-color: rgba(0, 0, 0, 0.8);
  border-left: 1px solid #00ff00;
  border-bottom: 1px solid #00ff00;
  width: 100%;
  min-width: 320px;
  height: 100%;
  margin: 0;
  padding: 0;
}

.bottom-panel {
  grid-area: hud;
  border-top: 1px solid #00ff00;
  background-color: rgba(0, 0, 0, 0.8);
  width: 100%;
  height: 150px;
  box-sizing: border-box;
  overflow: hidden;
}

h3 {
  margin: 0.5rem 0;
  text-align: center;
  font-size: 1.5rem;
}
</style> 