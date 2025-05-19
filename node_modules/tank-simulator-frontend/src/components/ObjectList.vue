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
          <tr v-if="storeObjects.length === 0">
            <td colspan="5" style="text-align: center">위험요소 없음</td>
          </tr>
          <tr v-for="obj in storeObjects" 
              :key="obj.id || obj.track_id" 
              :class="[$store.getters.getThreatClass(obj.threat), {'selected': selectedObjectId === obj.id}]"
              @click="selectObject(obj)">
            <td>{{ formatClassName(obj) }}</td>
            <td>{{ obj.track_id || obj.id || '-' }}</td>
            <td :class="$store.getters.getThreatClass(obj.threat)">{{ obj.threat || 'Normal' }}</td>
            <td class="location-cell">{{ formatLocation(obj.bbox) }}</td>
            <td :class="['priority-cell', `rank-${obj.rank || '3'}`]">{{ obj.rank || '-' }}</td>
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
      selectedObjectId: null
    }
  },
  computed: {
    // Vuex 스토어에서 탐지된 객체 데이터 가져오기
    storeObjects() {
      return this.$store.state.detectedObjects || []
    }
  },
  methods: {
    formatClassName(obj) {
      if (!obj.className) return '알 수 없음'
      
      // 신뢰도 정보가 있으면 표시
      let name = obj.className
      if (obj.confidence) {
        const confidence = Math.round(obj.confidence * 100)
        name += ` (${confidence}%)`
      }
      return name
    },
    formatLocation(bbox) {
      if (!bbox) return '--'
      const x = Math.round((bbox[0] + bbox[2]) / 2)
      const y = Math.round((bbox[1] + bbox[3]) / 2)
      return `(${x}, ${y})`
    },
    selectObject(obj) {
      // 객체 ID 결정 (track_id 또는 id)
      const objId = obj.track_id || obj.id
      
      // 같은 객체를 다시 클릭하면 선택 해제
      if (this.selectedObjectId === objId) {
        this.selectedObjectId = null
      } else {
        this.selectedObjectId = objId
      }
      
      // 이벤트 발생: 객체 선택 정보를 부모 컴포넌트나 이벤트 버스로 전달
      this.$emit('object-selected', this.selectedObjectId ? obj : null)
    }
  }
}
</script>

<style scoped>
.object-list-section {
  width: 100%;
  height: 50%;
  max-height: 100%;
  overflow-y: auto;
  background-color: rgba(0, 255, 0, 0.05);
  border: 2px solid #00ff00;
  padding: 0.5rem;
  box-shadow: 0 0 8px #00ff00;
  border-radius: 10px;
  box-sizing: border-box;
  margin: 0;
  display: flex;
  flex-direction: column;
}

h3 {
  margin: 0 0 0.5rem 0;
  padding: 0;
  font-size: 1.2rem;
  text-align: center;
}

.object-list-wrapper {
  width: 100%;
  flex: 1;
  overflow-y: auto;
  margin: 0;
  padding: 0;
}

#object-list {
  width: 100%;
  min-width: 300px;
  border-collapse: collapse;
  font-family: monospace;
  font-size: 0.9rem;
  table-layout: fixed;
}

#object-list th {
  position: sticky;
  top: 0;
  background-color: #111;
  z-index: 10;
  color: #00ff00;
}

#object-list th:nth-child(1) { width: 35%; } /* 클래스명 */
#object-list th:nth-child(2) { width: 10%; } /* ID */
#object-list th:nth-child(3) { width: 20%; } /* 위험등급 */
#object-list th:nth-child(4) { width: 20%; } /* 위치 */
#object-list th:nth-child(5) { width: 15%; } /* 우선순위 */

#object-list th,
#object-list td {
  border: 1px solid #00ff00;
  padding: 6px 4px;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

#object-list tbody tr:nth-child(even) {
  background-color: rgba(0, 255, 0, 0.05);
}

#object-list tbody tr {
  cursor: pointer;
  transition: background-color 0.2s;
}

#object-list tbody tr:hover {
  background-color: rgba(0, 255, 0, 0.1);
}

#object-list tbody tr.selected {
  background-color: rgba(0, 255, 0, 0.2);
  box-shadow: 0 0 5px #00ff00 inset;
}

.threat-level-1 {
  color: #28a745;
  font-weight: bold;
}

.threat-level-2 {
  color: #ff9800;
  font-weight: bold;
}

.threat-level-3 {
  color: #dc3545;
  font-weight: bold;
}

.threat-normal {
  color: gray;
}

.threat-none {
  color: #666;
}

.priority-cell {
  font-weight: bold;
}

.priority-cell.rank-1 {
  color: #dc3545;
  background-color: rgba(220, 53, 69, 0.1);
}

.priority-cell.rank-2 {
  color: #ff9800;
  background-color: rgba(255, 152, 0, 0.1);
}

.priority-cell.rank-3 {
  color: #28a745;
  background-color: rgba(40, 167, 69, 0.1);
}

.location-cell {
  font-family: monospace;
  color: #ffffff;
  background-color: rgba(0, 255, 0, 0.05);
}

@media (max-width: 768px) {
  .object-list-section {
    display: none;
  }
}
</style> 