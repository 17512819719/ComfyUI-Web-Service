import { defineStore } from 'pinia'

export const useConfigStore = defineStore('config', {
  state: () => ({
    serverUrl: localStorage.getItem('serverUrl') || 'http://localhost:8000'
  }),
  
  actions: {
    setServerUrl(url) {
      this.serverUrl = url
      localStorage.setItem('serverUrl', url)
    }
  }
}) 