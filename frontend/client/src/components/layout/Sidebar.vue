<template>
  <div class="sidebar">
    <div class="sidebar-logo">
      <i class="fas fa-magic"></i>
    </div>
    <nav class="sidebar-nav">
      <router-link 
        to="/" 
        class="nav-item" 
        active-class="active"
        exact
      >
        <i class="fas fa-image"></i>
      </router-link>
      <router-link 
        to="/history" 
        class="nav-item"
        active-class="active"
      >
        <i class="fas fa-history"></i>
      </router-link>
      <router-link 
        to="/settings" 
        class="nav-item"
        active-class="active"
      >
        <i class="fas fa-cog"></i>
      </router-link>
    </nav>
  </div>
</template>

<script setup>
// 无需额外逻辑
</script>

<style scoped>
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  width: 80px;
  height: 100vh;
  background: var(--surface-1);
  backdrop-filter: blur(20px);
  border-right: 1px solid var(--border-1);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 0;
  z-index: 1000;
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.1);
}

.sidebar-logo {
  width: 48px;
  height: 48px;
  background: var(--primary-gradient);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 32px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.sidebar-logo::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(255,255,255,0.2) 0%, transparent 50%);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.sidebar-logo:hover {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 8px 32px rgba(99, 102, 241, 0.3);
}

.sidebar-logo:hover::before {
  opacity: 1;
}

.sidebar-logo i {
  color: white;
  font-size: 22px;
  z-index: 1;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
}

.nav-item {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  color: var(--text-muted);
  position: relative;
  overflow: hidden;
  text-decoration: none;
}

.nav-item::before {
  content: '';
  position: absolute;
  inset: 0;
  background: var(--surface-2);
  border-radius: 14px;
  opacity: 0;
  transition: all 0.3s ease;
  transform: scale(0.8);
}

.nav-item:hover::before {
  opacity: 1;
  transform: scale(1);
}

.nav-item:hover, 
.nav-item.active {
  color: var(--accent);
  transform: translateY(-1px);
}

.nav-item.active::before {
  opacity: 1;
  transform: scale(1);
  background: rgba(99, 102, 241, 0.15);
}

.nav-item i {
  font-size: 20px;
  z-index: 1;
}

@media (max-width: 768px) {
  .sidebar {
    width: 70px;
  }
}

@media (max-width: 480px) {
  .sidebar {
    width: 60px;
  }
}
</style> 