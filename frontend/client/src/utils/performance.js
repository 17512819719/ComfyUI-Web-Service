/**
 * 性能优化工具函数
 */

// 防抖函数
export const debounce = (func, wait, immediate = false) => {
  let timeout
  return function executedFunction(...args) {
    const later = () => {
      timeout = null
      if (!immediate) func.apply(this, args)
    }
    const callNow = immediate && !timeout
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
    if (callNow) func.apply(this, args)
  }
}

// 节流函数
export const throttle = (func, limit) => {
  let inThrottle
  return function executedFunction(...args) {
    if (!inThrottle) {
      func.apply(this, args)
      inThrottle = true
      setTimeout(() => inThrottle = false, limit)
    }
  }
}

// RAF 节流（使用 requestAnimationFrame）
export const rafThrottle = (func) => {
  let rafId = null
  return function executedFunction(...args) {
    if (rafId === null) {
      rafId = requestAnimationFrame(() => {
        func.apply(this, args)
        rafId = null
      })
    }
  }
}

// 空闲时执行（使用 requestIdleCallback）
export const runWhenIdle = (callback, options = {}) => {
  if ('requestIdleCallback' in window) {
    return requestIdleCallback(callback, options)
  } else {
    // 降级方案
    return setTimeout(callback, 0)
  }
}

// 批量执行任务
export const batchExecute = (tasks, batchSize = 10, delay = 0) => {
  return new Promise((resolve) => {
    let index = 0
    const results = []

    const executeBatch = () => {
      const batch = tasks.slice(index, index + batchSize)
      
      batch.forEach((task, i) => {
        const result = typeof task === 'function' ? task() : task
        results[index + i] = result
      })

      index += batchSize

      if (index < tasks.length) {
        if (delay > 0) {
          setTimeout(executeBatch, delay)
        } else {
          runWhenIdle(executeBatch)
        }
      } else {
        resolve(results)
      }
    }

    executeBatch()
  })
}

// 内存管理
export class MemoryManager {
  constructor() {
    this.cache = new Map()
    this.maxSize = 100
    this.cleanupThreshold = 0.8
  }

  set(key, value, ttl = 300000) { // 默认5分钟TTL
    // 检查是否需要清理
    if (this.cache.size >= this.maxSize * this.cleanupThreshold) {
      this.cleanup()
    }

    this.cache.set(key, {
      value,
      timestamp: Date.now(),
      ttl
    })
  }

  get(key) {
    const item = this.cache.get(key)
    if (!item) return null

    // 检查是否过期
    if (Date.now() - item.timestamp > item.ttl) {
      this.cache.delete(key)
      return null
    }

    return item.value
  }

  delete(key) {
    return this.cache.delete(key)
  }

  cleanup() {
    const now = Date.now()
    const toDelete = []

    for (const [key, item] of this.cache.entries()) {
      if (now - item.timestamp > item.ttl) {
        toDelete.push(key)
      }
    }

    toDelete.forEach(key => this.cache.delete(key))

    // 如果清理后仍然超过阈值，删除最旧的项
    if (this.cache.size >= this.maxSize) {
      const entries = Array.from(this.cache.entries())
      entries.sort((a, b) => a[1].timestamp - b[1].timestamp)
      
      const deleteCount = Math.floor(this.maxSize * 0.2)
      for (let i = 0; i < deleteCount; i++) {
        this.cache.delete(entries[i][0])
      }
    }
  }

  clear() {
    this.cache.clear()
  }

  size() {
    return this.cache.size
  }
}

// 创建全局内存管理器实例
export const memoryManager = new MemoryManager()

// 图片缓存管理
export class ImageCache {
  constructor(maxSize = 50) {
    this.cache = new Map()
    this.maxSize = maxSize
  }

  async get(url, authToken = null) {
    if (this.cache.has(url)) {
      return this.cache.get(url)
    }

    try {
      const headers = {}
      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`
      }

      const response = await fetch(url, { headers })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const blob = await response.blob()
      const objectUrl = URL.createObjectURL(blob)

      // 检查缓存大小
      if (this.cache.size >= this.maxSize) {
        const firstKey = this.cache.keys().next().value
        const firstValue = this.cache.get(firstKey)
        URL.revokeObjectURL(firstValue)
        this.cache.delete(firstKey)
      }

      this.cache.set(url, objectUrl)
      return objectUrl
    } catch (error) {
      console.error('图片缓存失败:', error)
      throw error
    }
  }

  delete(url) {
    if (this.cache.has(url)) {
      const objectUrl = this.cache.get(url)
      URL.revokeObjectURL(objectUrl)
      this.cache.delete(url)
    }
  }

  clear() {
    for (const objectUrl of this.cache.values()) {
      URL.revokeObjectURL(objectUrl)
    }
    this.cache.clear()
  }
}

// 创建全局图片缓存实例
export const imageCache = new ImageCache()

// 性能监控
export class PerformanceMonitor {
  constructor() {
    this.metrics = new Map()
    this.observers = []
  }

  // 记录性能指标
  recordMetric(name, value, type = 'timing') {
    const timestamp = Date.now()
    
    if (!this.metrics.has(name)) {
      this.metrics.set(name, [])
    }

    this.metrics.get(name).push({
      value,
      type,
      timestamp
    })

    // 保持最近100条记录
    const records = this.metrics.get(name)
    if (records.length > 100) {
      records.splice(0, records.length - 100)
    }
  }

  // 测量函数执行时间
  measureFunction(func, name) {
    return (...args) => {
      const start = performance.now()
      const result = func.apply(this, args)
      const end = performance.now()
      
      this.recordMetric(name || func.name, end - start)
      
      return result
    }
  }

  // 测量异步函数执行时间
  measureAsyncFunction(func, name) {
    return async (...args) => {
      const start = performance.now()
      const result = await func.apply(this, args)
      const end = performance.now()
      
      this.recordMetric(name || func.name, end - start)
      
      return result
    }
  }

  // 获取性能统计
  getStats(name) {
    const records = this.metrics.get(name)
    if (!records || records.length === 0) {
      return null
    }

    const values = records.map(r => r.value)
    const sum = values.reduce((a, b) => a + b, 0)
    const avg = sum / values.length
    const min = Math.min(...values)
    const max = Math.max(...values)

    return {
      count: values.length,
      sum,
      avg,
      min,
      max,
      latest: values[values.length - 1]
    }
  }

  // 监控长任务
  observeLongTasks() {
    if ('PerformanceObserver' in window) {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          this.recordMetric('long-task', entry.duration, 'long-task')
        }
      })

      observer.observe({ entryTypes: ['longtask'] })
      this.observers.push(observer)
    }
  }

  // 监控内存使用
  observeMemory() {
    if ('memory' in performance) {
      const recordMemory = () => {
        const memory = performance.memory
        this.recordMetric('memory-used', memory.usedJSHeapSize, 'memory')
        this.recordMetric('memory-total', memory.totalJSHeapSize, 'memory')
        this.recordMetric('memory-limit', memory.jsHeapSizeLimit, 'memory')
      }

      recordMemory()
      this.memoryInterval = setInterval(recordMemory, 10000) // 每10秒记录一次
    }
  }

  // 清理观察器
  disconnect() {
    this.observers.forEach(observer => observer.disconnect())
    this.observers = []

    // 清理内存监控定时器
    if (this.memoryInterval) {
      clearInterval(this.memoryInterval)
      this.memoryInterval = null
    }
  }
}

// 创建全局性能监控实例
export const performanceMonitor = new PerformanceMonitor()

// 检查元素是否在视口中
export const isElementInViewport = (element, threshold = 0) => {
  const rect = element.getBoundingClientRect()
  const windowHeight = window.innerHeight || document.documentElement.clientHeight
  const windowWidth = window.innerWidth || document.documentElement.clientWidth

  return (
    rect.top >= -threshold &&
    rect.left >= -threshold &&
    rect.bottom <= windowHeight + threshold &&
    rect.right <= windowWidth + threshold
  )
}

// 预加载资源
export const preloadResource = (url, type = 'image') => {
  return new Promise((resolve, reject) => {
    if (type === 'image') {
      const img = new Image()
      img.onload = () => resolve(img)
      img.onerror = reject
      img.src = url
    } else if (type === 'script') {
      const script = document.createElement('script')
      script.onload = () => resolve(script)
      script.onerror = reject
      script.src = url
      document.head.appendChild(script)
    } else if (type === 'style') {
      const link = document.createElement('link')
      link.rel = 'stylesheet'
      link.onload = () => resolve(link)
      link.onerror = reject
      link.href = url
      document.head.appendChild(link)
    }
  })
}

// 批量预加载
export const batchPreload = async (urls, type = 'image', concurrency = 3) => {
  const results = []
  
  for (let i = 0; i < urls.length; i += concurrency) {
    const batch = urls.slice(i, i + concurrency)
    const promises = batch.map(url => preloadResource(url, type))
    
    try {
      const batchResults = await Promise.allSettled(promises)
      results.push(...batchResults)
    } catch (error) {
      console.error('批量预加载失败:', error)
    }
  }
  
  return results
}
