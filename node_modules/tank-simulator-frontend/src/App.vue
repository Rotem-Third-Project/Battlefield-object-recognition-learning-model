<template>
  <div id="app">
    <KeyboardController />
    <router-view/>
  </div>
</template>

<script>
import KeyboardController from './components/KeyboardController.vue'

export default {
  components: {
    KeyboardController
  }
}
</script>

<style>
html, body {
  margin: 0;
  padding: 0;
  width: 100vw;
  height: 100vh;
  overflow: hidden; /* 👉 스크롤 제거 핵심 */
}

#app {
  font-family: "Share Tech Mono", monospace;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;

  width: 100vw;
  height: 100vh;
  overflow: hidden; /* 혹시 내부 요소가 넘쳐도 숨기기 */
}
</style>
