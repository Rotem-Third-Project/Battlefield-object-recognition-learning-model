<template>
  <div id="app">
    <router-view/>
    <KeyboardController />
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
#app {
  font-family: "Share Tech Mono", monospace;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
}
</style>