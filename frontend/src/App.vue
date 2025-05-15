<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script>
export default {
  mounted() {
    window.addEventListener("keydown", this.handleKey)
  },
  unmounted() {
    window.removeEventListener("keydown", this.handleKey)
  },
  methods: {
    async handleKey(e) {
      const key = e.key.toUpperCase()
      const validKeys = ['W', 'A', 'S', 'D', 'P', 'L']
      if (validKeys.includes(key)) {
        console.log("🚀 키 입력:", key)

        const url = process.env.VUE_APP_API_URL || "http://localhost:5000"
        await fetch(`${url}/input_key`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          body: new URLSearchParams({ key })
        })
      }
    }
  }
}
</script>

<style>
#app {
  font-family: "Share Tech Mono", monospace;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
}
</style>
