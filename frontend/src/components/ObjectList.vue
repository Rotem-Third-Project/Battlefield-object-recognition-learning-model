<template>
  <div class="object-list">
    <h3>감지된 객체</h3>
    <ul>
      <li v-for="(obj, index) in detectedObjects" :key="index">
        {{ obj.class }} (신뢰도: {{ (obj.confidence * 100).toFixed(1) }}%)
      </li>
    </ul>
  </div>
</template>

<script>
export default {
  name: 'ObjectList',
  data() {
    return {
      detectedObjects: []
    }
  },
  mounted() {
    this.startObjectDetection()
  },
  methods: {
    async startObjectDetection() {
      try {
        const response = await fetch('http://localhost:8000/detect_objects')
        const data = await response.json()
        this.detectedObjects = data.objects
      } catch (error) {
        console.error('객체 감지 중 오류 발생:', error)
      }
    }
  }
}
</script>

<style scoped>
.object-list {
  position: absolute;
  top: 20px;
  right: 20px;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 15px;
  border-radius: 8px;
  max-width: 300px;
}

h3 {
  margin: 0 0 10px 0;
  font-size: 1.2em;
}

ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

li {
  padding: 5px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

li:last-child {
  border-bottom: none;
}
</style> 