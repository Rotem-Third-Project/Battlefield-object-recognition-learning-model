<template>
  <div class="control-panel">
    <button @click="sendKey('W')">⬆ 전진</button>
    <button @click="sendKey('S')">⬇ 후진</button>
    <button @click="sendKey('A')">⬅ 좌회전</button>
    <button @click="sendKey('D')">➡ 우회전</button>
    <button @click="sendKey('P')">➕ 기어 업</button>
    <button @click="sendKey('L')">➖ 기어 다운</button>
  </div>
</template>

<script>
export default {
  methods: {
    async sendKey(key) {
      await fetch(`${process.env.VUE_APP_API_URL}/input_key`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: new URLSearchParams({ key })
      })
    }
  }
}
</script>

<style scoped>
.control-panel {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  justify-content: center;
  margin: 1rem 0;
}
button {
  padding: 0.7rem 1.2rem;
  font-size: 1rem;
  background: #00ff00;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}
button:hover {
  background: #00cc00;
}
</style>
