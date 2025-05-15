<template>
  <div class="object-list-section">
    <h3>탐지된 객체 목록</h3>
    <div class="object-list-wrapper">
      <table id="object-list">
        <thead>
          <tr>
            <th>클래스명</th>
            <th>ID</th>
            <th>위험등급</th>
            <th>위치</th>
            <th>우선순위</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="obj in detectedObjects" :key="obj.id">
            <td>{{ obj.class }}</td>
            <td>{{ obj.id }}</td>
            <td>{{ obj.threat_level }}</td>
            <td class="location-cell">{{ obj.location }}</td>
            <td :class="['priority-cell', `rank-${obj.priority}`]">
              {{ obj.priority }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
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
    this.fetchObjects()
    setInterval(this.fetchObjects, 1000)
  },
  methods: {
    async fetchObjects() {
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
.object-list-section {
  flex: 3;
  max-height: 100%;
  overflow-y: auto;
  background-color: rgba(0, 255, 0, 0.05);
  border: 2px solid #00ff00;
  padding: 1rem;
  box-shadow: 0 0 8px #00ff00;
  border-radius: 10px;
}

#object-list {
  width: 100%;
  border-collapse: collapse;
  font-family: monospace;
  font-size: 0.9rem;
}

#object-list th,
#object-list td {
  border: 1px solid #00ff00;
  padding: 8px;
  text-align: center;
}

#object-list th {
  background-color: #111;
  color: #00ff00;
}

#object-list tbody tr:nth-child(even) {
  background-color: rgba(0, 255, 0, 0.05);
}

.priority-cell {
  font-weight: bold;
}

.priority-cell.rank-1 {
  color: #ff3c3c;
}

.priority-cell.rank-2 {
  color: #ffa500;
}

.priority-cell.rank-3 {
  color: #00ff00;
}

.location-cell {
  font-family: monospace;
}

@media (max-width: 768px) {
  .object-list-section {
    display: none;
  }
}
</style>