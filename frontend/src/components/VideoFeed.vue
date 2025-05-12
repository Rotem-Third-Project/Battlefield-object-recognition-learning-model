<template>
  <div class="video-feed">
    <video ref="videoElement" autoplay></video>
  </div>
</template>

<script>
export default {
  name: 'VideoFeed',
  mounted() {
    this.startVideoStream()
  },
  methods: {
    async startVideoStream() {
      try {
        const response = await fetch('http://localhost:8000/video_feed')
        const blob = await response.blob()
        const videoUrl = URL.createObjectURL(blob)
        this.$refs.videoElement.src = videoUrl
      } catch (error) {
        console.error('비디오 스트림을 시작하는 중 오류 발생:', error)
      }
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

video {
  width: 100%;
  height: auto;
  border: 1px solid #ccc;
  border-radius: 4px;
}
</style> 