<template>
  <div 
    ref="containerRef" 
    class="virtual-scroller" 
    @scroll="handleScroll"
    :style="containerStyle"
  >
    <!-- 虚拟滚动容器 -->
    <div class="virtual-scroller-content" :style="contentStyle">
      <!-- 渲染可见项目 -->
      <div
        v-for="item in visibleItems"
        :key="getItemKey(item.data)"
        class="virtual-item"
        :style="getItemStyle(item.index)"
      >
        <slot :item="item.data" :index="item.index" />
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'

export default {
  name: 'VirtualScroller',
  props: {
    items: {
      type: Array,
      default: () => []
    },
    itemHeight: {
      type: Number,
      default: 300
    },
    containerHeight: {
      type: Number,
      default: 600
    },
    overscan: {
      type: Number,
      default: 5
    },
    keyField: {
      type: String,
      default: 'id'
    }
  },
  emits: ['scroll', 'visible-change'],
  setup(props, { emit }) {
    const containerRef = ref(null)
    const scrollTop = ref(0)
    const isScrolling = ref(false)
    const scrollTimer = ref(null)

    // 计算可见区域
    const visibleRange = computed(() => {
      const containerHeight = props.containerHeight
      const itemHeight = props.itemHeight
      const overscan = props.overscan

      const startIndex = Math.max(0, Math.floor(scrollTop.value / itemHeight) - overscan)
      const endIndex = Math.min(
        props.items.length - 1,
        Math.ceil((scrollTop.value + containerHeight) / itemHeight) + overscan
      )

      return { startIndex, endIndex }
    })

    // 可见项目
    const visibleItems = computed(() => {
      const { startIndex, endIndex } = visibleRange.value
      const items = []

      for (let i = startIndex; i <= endIndex; i++) {
        if (props.items[i]) {
          items.push({
            index: i,
            data: props.items[i]
          })
        }
      }

      return items
    })

    // 容器样式
    const containerStyle = computed(() => ({
      height: `${props.containerHeight}px`,
      overflow: 'auto',
      position: 'relative'
    }))

    // 内容样式
    const contentStyle = computed(() => ({
      height: `${props.items.length * props.itemHeight}px`,
      position: 'relative'
    }))

    // 获取项目样式
    const getItemStyle = (index) => ({
      position: 'absolute',
      top: `${index * props.itemHeight}px`,
      left: '0',
      right: '0',
      height: `${props.itemHeight}px`
    })

    // 获取项目键值
    const getItemKey = (item) => {
      return item[props.keyField] || item.id || Math.random()
    }

    // 处理滚动事件
    const handleScroll = () => {
      if (!containerRef.value) return

      const newScrollTop = containerRef.value.scrollTop
      scrollTop.value = newScrollTop
      isScrolling.value = true

      // 清除之前的定时器
      if (scrollTimer.value) {
        clearTimeout(scrollTimer.value)
      }

      // 设置滚动结束定时器
      scrollTimer.value = setTimeout(() => {
        isScrolling.value = false
      }, 150)

      // 发射滚动事件
      emit('scroll', {
        scrollTop: newScrollTop,
        isScrolling: isScrolling.value
      })
    }

    // 滚动到指定位置
    const scrollToIndex = (index) => {
      if (!containerRef.value) return

      const targetScrollTop = index * props.itemHeight
      containerRef.value.scrollTop = targetScrollTop
    }

    // 滚动到顶部
    const scrollToTop = () => {
      scrollToIndex(0)
    }

    // 滚动到底部
    const scrollToBottom = () => {
      scrollToIndex(props.items.length - 1)
    }

    // 监听可见范围变化
    watch(visibleRange, (newRange, oldRange) => {
      if (newRange.startIndex !== oldRange?.startIndex || 
          newRange.endIndex !== oldRange?.endIndex) {
        emit('visible-change', {
          startIndex: newRange.startIndex,
          endIndex: newRange.endIndex,
          visibleItems: visibleItems.value
        })
      }
    })

    // 监听项目变化，重置滚动位置
    watch(() => props.items.length, (newLength, oldLength) => {
      if (newLength === 0) {
        scrollTop.value = 0
      }
    })

    onMounted(() => {
      // 初始化滚动位置
      nextTick(() => {
        if (containerRef.value) {
          scrollTop.value = containerRef.value.scrollTop
        }
      })
    })

    onUnmounted(() => {
      if (scrollTimer.value) {
        clearTimeout(scrollTimer.value)
      }
    })

    return {
      containerRef,
      scrollTop,
      isScrolling,
      visibleItems,
      containerStyle,
      contentStyle,
      getItemStyle,
      getItemKey,
      handleScroll,
      scrollToIndex,
      scrollToTop,
      scrollToBottom
    }
  }
}
</script>

<style scoped>
.virtual-scroller {
  width: 100%;
  overflow-x: hidden;
  overflow-y: auto;
}

.virtual-scroller-content {
  width: 100%;
}

.virtual-item {
  width: 100%;
}

/* 滚动条样式 */
.virtual-scroller::-webkit-scrollbar {
  width: 8px;
}

.virtual-scroller::-webkit-scrollbar-track {
  background: var(--surface-2);
  border-radius: 4px;
}

.virtual-scroller::-webkit-scrollbar-thumb {
  background: var(--border-2);
  border-radius: 4px;
}

.virtual-scroller::-webkit-scrollbar-thumb:hover {
  background: var(--text-muted);
}

/* 滚动性能优化 */
.virtual-scroller {
  -webkit-overflow-scrolling: touch;
  scroll-behavior: smooth;
}

.virtual-item {
  will-change: transform;
  contain: layout style paint;
}
</style>
