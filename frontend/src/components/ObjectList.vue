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
            <th>우선순위</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="processedObjects.length === 0">
            <td colspan="4" style="text-align: center">위험요소 없음</td>
          </tr>
          <tr v-for="obj in processedObjects" 
              :key="obj.track_id || obj.bbox?.join('-')" 
              :class="[threatClass(obj.threat), {'selected': selectedObjectId === obj.track_id}]"
              @click="selectObject(obj)">
            <td>{{ formatClassName(obj) }}</td>
            <td>{{ obj.track_id || '-' }}</td>
            <td :class="threatClass(obj.threat)">
              {{ obj.threat || 'Normal' }}
            </td>
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
  mounted() {
  console.log('[ObjectList mounted] processedObjects:', this.processedObjects);
  },
  data() {
    return {
      selectedObjectId: null
    };
  },
  computed: {
    processedObjects() {
      return this.$store.state.processedObjects || [];
    }
  },
  watch: {
    processedObjects: {
      handler(newObjects) {
        console.log('객체 업데이트:', newObjects.map(o => ({
          track_id: o.track_id,
          threat: o.threat,
          rank: o.rank,
          direction: o.direction
        })));
      },
      deep: true
    }
  },
  methods: {
    formatClassName(obj) {
      if (!obj.className) return '알 수 없음';
      let name = obj.className;
      if (obj.confidence) {
        const confidence = Math.round(obj.confidence * 100);
        name += ` (${confidence}%)`;
      }
      if (obj.direction && obj.direction !== 'unknown') {
        name += ` [${obj.direction}]`;
      }
      return name;
    },
    selectObject(obj) {
      const objId = obj.track_id;
      if (this.selectedObjectId === objId) {
        this.selectedObjectId = null;
      } else {
        this.selectedObjectId = objId;
      }
      this.$emit('object-selected', this.selectedObjectId ? obj : null);
    },
    threatClass(threat) {
      return {
        'threat-level-3': threat === 'LEVEL 3',
        'threat-level-2': threat === 'LEVEL 2',
        'threat-level-1': threat === 'LEVEL 1',
        'threat-normal': threat === 'Normal' || !threat,
        'threat-pending': !threat
      };
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

#object-list th:nth-child(1) { width: 35%; }
#object-list th:nth-child(2) { width: 10%; }
#object-list th:nth-child(3) { width: 20%; }
#object-list th:nth-child(4) { width: 35%; }

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

.threat-pending {
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

@media (max-width: 768px) {
  .object-list-section {
    display: none;
  }
}
</style>