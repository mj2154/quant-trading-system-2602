import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useChartPersistenceStore = defineStore('chartPersistence', () => {
  const visible = ref(false)

  function show() {
    visible.value = true
  }

  function hide() {
    visible.value = false
  }

  return { visible, show, hide }
})
