<template>
  <div class="settings-modal" v-if="visible">
    <div class="modal-content">
      <div class="modal-header">
        <h3>服务器设置</h3>
        <button class="close-btn" @click="close">×</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label>服务器地址</label>
          <input 
            type="text" 
            v-model="serverUrl"
            placeholder="请输入后端API服务器的地址和端口，通常为 http://本机IP:8000"
          >
          <p class="help-text">请输入后端API服务器的地址和端口，通常为 http://本机IP:8000</p>
        </div>
      </div>
      <div class="modal-footer">
        <button class="save-btn" @click="saveSettings">保存设置</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/store/auth'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:visible'])

const authStore = useAuthStore()
const serverUrl = ref(authStore.apiServer)

const close = () => {
  emit('update:visible', false)
}

const saveSettings = () => {
  if (!serverUrl.value) {
    alert('请填写服务器地址')
    return
  }
  authStore.setApiServer(serverUrl.value)
  close()
  alert('服务器设置已保存！')
}

onMounted(() => {
  serverUrl.value = authStore.apiServer
})
</script>

<style scoped>
.settings-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.modal-header {
  padding: 1rem;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #666;
}

.modal-body {
  padding: 1rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #666;
}

.form-group input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.help-text {
  margin-top: 0.5rem;
  color: #666;
  font-size: 0.9rem;
}

.modal-footer {
  padding: 1rem;
  border-top: 1px solid #eee;
  text-align: right;
}

.save-btn {
  background-color: #4a90e2;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
}

.save-btn:hover {
  background-color: #357abd;
}
</style> 