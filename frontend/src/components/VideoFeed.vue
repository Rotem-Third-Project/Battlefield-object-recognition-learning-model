<template>
  <div class="video-feed">
    <img :src="videoUrl" alt="Video Feed" />
  </div>
</template>

<script>
export default {
  name: 'VideoFeed',
  data() {
    return {
      videoUrl: `${process.env.VUE_APP_API_URL}/video_feed`
    }
  }
}
</script>

<style scoped>
.video-feed {
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
}
img {
  width: 100%;
  height: auto;
  border: 1px solid #ccc;
  border-radius: 4px;
}
</style>
