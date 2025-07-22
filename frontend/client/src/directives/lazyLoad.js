/**
 * 图片懒加载指令
 * 使用 IntersectionObserver API 实现高性能懒加载
 */

// 创建 IntersectionObserver 实例
const createObserver = (callback, options = {}) => {
  const defaultOptions = {
    root: null,
    rootMargin: '50px 0px',
    threshold: 0.1
  }

  return new IntersectionObserver(callback, { ...defaultOptions, ...options })
}

// 图片加载状态管理
const imageLoadStates = new WeakMap()

// 默认占位图片（1x1 透明像素）
const PLACEHOLDER_IMAGE = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="1" height="1"%3E%3C/svg%3E'

// 懒加载处理函数
const handleIntersection = (entries, observer) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const img = entry.target
      const state = imageLoadStates.get(img)
      
      if (state && !state.loaded && !state.loading) {
        loadImage(img, state)
      }
    }
  })
}

// 创建全局观察器
const lazyObserver = createObserver(handleIntersection)

// 加载图片
const loadImage = async (img, state) => {
  if (state.loading || state.loaded) return

  state.loading = true
  
  try {
    // 添加加载状态类
    img.classList.add('lazy-loading')
    
    // 创建新的图片对象进行预加载
    const imageLoader = new Image()
    
    // 设置加载成功回调
    imageLoader.onload = () => {
      // 设置实际图片源
      img.src = state.src
      img.classList.remove('lazy-loading')
      img.classList.add('lazy-loaded')
      
      // 更新状态
      state.loaded = true
      state.loading = false
      
      // 停止观察该元素
      lazyObserver.unobserve(img)
      
      // 触发自定义事件
      img.dispatchEvent(new CustomEvent('lazy-loaded', {
        detail: { src: state.src }
      }))
    }
    
    // 设置加载失败回调
    imageLoader.onerror = () => {
      img.classList.remove('lazy-loading')
      img.classList.add('lazy-error')
      
      // 更新状态
      state.loading = false
      state.error = true
      
      // 触发自定义事件
      img.dispatchEvent(new CustomEvent('lazy-error', {
        detail: { src: state.src }
      }))
    }
    
    // 开始加载图片
    imageLoader.src = state.src
    
  } catch (error) {
    console.error('懒加载图片失败:', error)
    state.loading = false
    state.error = true
    img.classList.remove('lazy-loading')
    img.classList.add('lazy-error')
  }
}

// 懒加载指令定义
export const lazyLoad = {
  // 指令挂载时
  mounted(el, binding) {
    // 只处理 img 元素
    if (el.tagName !== 'IMG') {
      console.warn('v-lazy-load 指令只能用于 img 元素')
      return
    }

    const src = binding.value
    if (!src) {
      console.warn('v-lazy-load 指令需要提供图片 URL')
      return
    }

    // 初始化状态
    const state = {
      src,
      loaded: false,
      loading: false,
      error: false
    }
    
    imageLoadStates.set(el, state)

    // 设置占位图片
    if (!el.src || el.src === '') {
      el.src = PLACEHOLDER_IMAGE
    }

    // 添加懒加载类
    el.classList.add('lazy-image')

    // 开始观察元素
    lazyObserver.observe(el)
  },

  // 指令更新时
  updated(el, binding) {
    const state = imageLoadStates.get(el)
    if (!state) return

    const newSrc = binding.value
    if (newSrc !== state.src) {
      // 重置状态
      state.src = newSrc
      state.loaded = false
      state.loading = false
      state.error = false

      // 重置类名
      el.classList.remove('lazy-loaded', 'lazy-error', 'lazy-loading')
      el.classList.add('lazy-image')

      // 重新设置占位图片
      el.src = PLACEHOLDER_IMAGE

      // 重新开始观察
      lazyObserver.observe(el)
    }
  },

  // 指令卸载时
  unmounted(el) {
    // 停止观察
    lazyObserver.unobserve(el)
    
    // 清理状态
    imageLoadStates.delete(el)
  }
}

// 预加载指令（用于重要图片的预加载）
export const preload = {
  mounted(el, binding) {
    const src = binding.value
    if (!src) return

    // 立即开始预加载
    const imageLoader = new Image()
    imageLoader.src = src
  }
}

// 批量懒加载函数
export const batchLazyLoad = (images, options = {}) => {
  const observer = createObserver(handleIntersection, options)
  
  images.forEach(img => {
    if (img.tagName === 'IMG') {
      observer.observe(img)
    }
  })
  
  return observer
}

// 手动触发懒加载
export const triggerLazyLoad = (img) => {
  const state = imageLoadStates.get(img)
  if (state && !state.loaded && !state.loading) {
    loadImage(img, state)
  }
}

// 检查是否支持 IntersectionObserver
export const isIntersectionObserverSupported = () => {
  return 'IntersectionObserver' in window
}

// 降级方案：基于滚动事件的懒加载
export const fallbackLazyLoad = (img, src) => {
  const checkVisibility = () => {
    const rect = img.getBoundingClientRect()
    const isVisible = rect.top < window.innerHeight && rect.bottom > 0
    
    if (isVisible) {
      img.src = src
      window.removeEventListener('scroll', checkVisibility)
      window.removeEventListener('resize', checkVisibility)
    }
  }
  
  window.addEventListener('scroll', checkVisibility, { passive: true })
  window.addEventListener('resize', checkVisibility, { passive: true })
  
  // 立即检查一次
  checkVisibility()
}

export default lazyLoad
