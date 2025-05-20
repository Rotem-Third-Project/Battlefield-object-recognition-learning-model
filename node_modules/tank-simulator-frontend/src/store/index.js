import { createStore } from 'vuex';

export default createStore({
  state: {
    detectedObjects: [],
    simulatorStatus: {
      playerPos: { x: 60, y: 10, z: 27.23 },
      playerSpeed: 0,
      playerHealth: 100,
      enemyHealth: 100,
      distance: 0,
      isInfoReceived: false
    }
  },
  getters: {
    getThreatClass: () => (threat) => {
      if (!threat || threat === 'Pending') return 'threat-pending';
      return `threat-${threat.toLowerCase().replace(' ', '-')}`;
    }
  },
  mutations: {
    setDetectedObjects(state, objects) {
      // 이전 객체의 threat, direction 유지
      const existingObjects = state.detectedObjects.reduce((map, obj) => {
        const objId = obj.track_id;
        map[objId] = obj;
        return map;
      }, {});
      
      const mergedObjects = objects.map(newObj => {
        const objId = newObj.track_id;
        const existing = existingObjects[objId];
        if (existing && existing.threat && existing.threat !== 'Pending' && existing.direction !== 'unknown') {
          return {
            ...newObj,
            threat: existing.threat,
            direction: existing.direction,
            direction_confidence: existing.direction_confidence
          };
        }
        return { ...newObj, threat: newObj.threat || 'Pending' };
      });
      
      state.detectedObjects = mergedObjects;
      console.log('setDetectedObjects:', state.detectedObjects.map(o => ({ track_id: o.track_id, threat: o.threat || 'Pending' })));
    },
    updateObjectThreat(state, { id, threat, direction, direction_confidence }) {
      const index = state.detectedObjects.findIndex(obj => obj.track_id === id);
      if (index !== -1) {
        state.detectedObjects[index].threat = threat;
        state.detectedObjects[index].direction = direction;
        state.detectedObjects[index].direction_confidence = direction_confidence;
        state.detectedObjects = [...state.detectedObjects];
        console.log(`Updated threat for track_id=${id}: ${threat}`);
      }
    },
    updateSimulatorStatus(state, status) {
      state.simulatorStatus = { ...state.simulatorStatus, ...status };
    }
  },
  actions: {
    async fetchDetectedObjects({ commit, state }) {
      try {
        const response = await fetch('/get_detected_objects');
        const data = await response.json();
        if (data.objects) {
          const existingObjects = state.detectedObjects.reduce((map, obj) => {
            const objId = obj.track_id;
            map[objId] = obj;
            return map;
          }, {});
          const mergedObjects = data.objects.map(newObj => {
            const objId = newObj.track_id;
            const existing = existingObjects[objId];
            if (existing && existing.threat && existing.threat !== 'Pending' && existing.direction !== 'unknown') {
              console.log(`Preserving threat for track_id=${objId}: ${existing.threat}`);
              return {
                ...newObj,
                threat: existing.threat,
                direction: existing.direction,
                direction_confidence: existing.direction_confidence
              };
            }
            return { ...newObj, threat: newObj.threat || 'Pending' };
          });
          commit('setDetectedObjects', mergedObjects);
        }
      } catch (error) {
        console.error('객체 감지 데이터 가져오기 실패:', error);
        commit('setDetectedObjects', []);
      }
    },
    async updatePriorities({ commit }, objects) {
      if (!objects || objects.length === 0) {
        commit('setDetectedObjects', objects);
        return;
      }
      const DIRECTION_WEIGHT = 0.5;
      const SIZE_WEIGHT = 0.3;
      const DISTANCE_WEIGHT = 0.2;
      const direction_weights = {
        "enemy_front": 0.5,
        "enemy_side": 0.3,
        "enemy_rear": 0.1,
        "unknown": 0.0
      };
      const center_x = 2560 / 2;
      const center_y = 1440 / 2;
      const max_distance = Math.sqrt(center_x**2 + center_y**2);
      const max_height = Math.max(...objects.map(obj => (obj.bbox[3] - obj.bbox[1])), 1);
      const updatedObjects = objects.map(obj => {
        const direction = obj.direction || "unknown";
        const dir_score = direction_weights[direction] || 0.0;
        const height = obj.bbox[3] - obj.bbox[1];
        const size_score = (height ** 2) / (max_height ** 2);
        const box_center_x = (obj.bbox[0] + obj.bbox[2]) / 2;
        const box_center_y = (obj.bbox[1] + obj.bbox[3]) / 2;
        const distance = Math.sqrt((center_x - box_center_x)**2 + (center_y - box_center_y)**2);
        const distance_score = 1.0 - (distance / max_distance);
        const total_score = (DIRECTION_WEIGHT * dir_score) + (SIZE_WEIGHT * size_score) + (DISTANCE_WEIGHT * distance_score);
        return { ...obj, priority_score: total_score, threat: obj.threat || 'Pending' };
      });
      const sortedObjects = updatedObjects.sort((a, b) => b.priority_score - a.priority_score);
      const prioritizedObjects = sortedObjects.map((obj, index) => ({ ...obj, rank: index + 1 }));
      commit('setDetectedObjects', prioritizedObjects);
    },
    async updateStatus({ commit }, status) {
      commit('updateSimulatorStatus', status);
    }
  }
});