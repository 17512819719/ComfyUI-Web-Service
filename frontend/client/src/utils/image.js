/**
 * 加载图片并返回 Promise
 * @param {string} url 图片URL
 * @param {Object} options 选项
 * @param {number} options.retryCount 重试次数
 * @param {number} options.retryDelay 重试延迟(ms)
 * @returns {Promise<HTMLImageElement>}
 */
export const loadImage = (url, { retryCount = 3, retryDelay = 1000 } = {}) => {
  return new Promise((resolve, reject) => {
    const img = new Image();
    let currentRetry = 0;

    const tryLoad = () => {
      img.onload = () => resolve(img);
      img.onerror = () => {
        currentRetry++;
        if (currentRetry <= retryCount) {
          setTimeout(tryLoad, retryDelay * Math.pow(2, currentRetry - 1));
        } else {
          reject(new Error('图片加载失败'));
        }
      };
      img.src = url;
    };

    tryLoad();
  });
};

/**
 * 验证图片文件
 * @param {File} file 文件对象
 * @param {Object} options 选项
 * @param {number} options.maxSize 最大文件大小(bytes)
 * @param {string[]} options.allowedTypes 允许的文件类型
 * @returns {Promise<boolean>}
 */
export const validateImage = async (file, { 
  maxSize = 10 * 1024 * 1024, 
  allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
} = {}) => {
  // 检查文件类型
  if (!allowedTypes.includes(file.type)) {
    throw new Error('不支持的文件类型');
  }

  // 检查文件大小
  if (file.size > maxSize) {
    throw new Error(`文件大小不能超过 ${maxSize / 1024 / 1024}MB`);
  }

  // 检查图片是否可以正常加载
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => resolve(true);
      img.onerror = () => reject(new Error('图片格式无效'));
      img.src = e.target.result;
    };
    reader.onerror = () => reject(new Error('文件读取失败'));
    reader.readAsDataURL(file);
  });
};

/**
 * 压缩图片
 * @param {File} file 文件对象
 * @param {Object} options 选项
 * @param {number} options.maxWidth 最大宽度
 * @param {number} options.maxHeight 最大高度
 * @param {number} options.quality 压缩质量(0-1)
 * @returns {Promise<Blob>}
 */
export const compressImage = async (file, { 
  maxWidth = 2048, 
  maxHeight = 2048, 
  quality = 0.8 
} = {}) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        // 计算压缩后的尺寸
        let width = img.width;
        let height = img.height;
        
        if (width > maxWidth) {
          height = Math.round((height * maxWidth) / width);
          width = maxWidth;
        }
        
        if (height > maxHeight) {
          width = Math.round((width * maxHeight) / height);
          height = maxHeight;
        }

        // 创建 canvas 并绘制图片
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, width, height);

        // 转换为 blob
        canvas.toBlob(
          (blob) => resolve(blob),
          file.type,
          quality
        );
      };
      img.onerror = () => reject(new Error('图片处理失败'));
      img.src = e.target.result;
    };
    reader.onerror = () => reject(new Error('文件读取失败'));
    reader.readAsDataURL(file);
  });
};

/**
 * 创建图片预览URL
 * @param {File|Blob} file 文件对象
 * @returns {string} 预览URL
 */
export const createPreviewUrl = (file) => {
  return URL.createObjectURL(file);
};

/**
 * 释放预览URL
 * @param {string} url 预览URL
 */
export const revokePreviewUrl = (url) => {
  URL.revokeObjectURL(url);
}; 