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
          <tr v-if="detectedObjects.length === 0">
            <td colspan="5" style="text-align: center">위험요소 없음</td>
          </tr>
          <tr v-for="obj in detectedObjects" 
              :key="obj.id" 
              :class="[getThreatClass(obj.threat), {'selected': selectedObjectId === obj.id}]"
              @click="selectObject(obj)">
            <td>{{ obj.className }}</td>
            <td>{{ obj.id }}</td>
            <td :class="getThreatClass(obj.threat)">{{ obj.threat }}</td>
            <td class="location-cell">{{ formatLocation(obj.bbox) }}</td>
            <td :class="['priority-cell', `rank-${obj.rank}`]">{{ obj.rank }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
// 직접 백엔드 URL 사용
const API_URL = '/api'

export default {
  name: 'ObjectList',
  data() {
    return {
      detectedObjects: [],
      lastUpdateTime: Date.now(),
      selectedObjectId: null,
      fetchIntervalId: null
    }
  },
  mounted() {
    this.fetchObjects()
    // 100ms 마다 업데이트하여 빠른 반응성 확보
    this.fetchIntervalId = setInterval(this.fetchObjects, 100)
  },
  beforeDestroy() {
    // 인터벌 제거하여 메모리 누수 방지
    if (this.fetchIntervalId) {
      clearInterval(this.fetchIntervalId)
    }
  },
  methods: {
    async fetchObjects() {
      try {
        const response = await fetch('/get_detected_objects')
        if (!response.ok) {
          return
        }
        const data = await response.json()
        
        // API 응답 구조 대응 (ranked_objects 또는 objects)
        const objects = data.ranked_objects || data.objects || []
        
        // 객체가 없으면 테이블 비우기
        if (objects.length === 0) {
          if (this.detectedObjects.length > 0) {
            this.detectedObjects = []
            this.lastUpdateTime = Date.now()
          }
          return
        }
        
        // 객체 ID 목록을 비교하여 변화가 있을 때만 업데이트
        // (성능 최적화 - 불필요한 렌더링 방지)
        let shouldUpdate = this.detectedObjects.length !== objects.length
        
        if (!shouldUpdate) {
          const currentIds = this.detectedObjects.map(obj => obj.id).sort().join(',')
          const newIds = objects.map(obj => obj.id).sort().join(',')
          shouldUpdate = currentIds !== newIds
        }
        
        // 변화가 있을 때만 업데이트
        if (shouldUpdate) {
          this.detectedObjects = objects
          this.lastUpdateTime = Date.now()
          
          // 선택된 객체가 사라졌으면 선택 해제
          if (this.selectedObjectId !== null) {
            const stillExists = this.detectedObjects.some(obj => obj.id === this.selectedObjectId)
            if (!stillExists) {
              this.selectedObjectId = null
              // 선택 해제 이벤트 발생
              this.$emit('object-selected', null)
            }
          }
        }
      } catch (error) {
        // 에러 핸들링 - 콘솔 로그 최소화
      }
    },
    formatLocation(bbox) {
      if (!bbox) return '--'
      const x = Math.round((bbox[0] + bbox[2]) / 2)
      const y = Math.round((bbox[1] + bbox[3]) / 2)
      return `(${x}, ${y})`
    },
    getThreatClass(threat) {
      if (!threat) return 'threat-none'
      return `threat-${threat.toLowerCase().replace(' ', '-')}`
    },
    selectObject(obj) {
      // 같은 객체를 다시 클릭하면 선택 해제
      if (this.selectedObjectId === obj.id) {
        this.selectedObjectId = null
      } else {
        this.selectedObjectId = obj.id
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
  height: 100%;
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