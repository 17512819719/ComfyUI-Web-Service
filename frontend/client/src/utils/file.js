import JSZip from 'jszip';

/**
 * 验证文件类型
 * @param {File} file 文件对象
 * @param {string[]} allowedTypes 允许的文件类型数组
 * @returns {boolean}
 */
export const validateFileType = (file, allowedTypes) => {
  return allowedTypes.includes(file.type)
}

/**
 * 验证文件大小
 * @param {File} file 文件对象
 * @param {number} maxSize 最大文件大小（字节）
 * @returns {boolean}
 */
export const validateFileSize = (file, maxSize) => {
  return file.size <= maxSize
}

/**
 * 格式化文件大小
 * @param {number} bytes 文件大小（字节）
 * @returns {string}
 */
export const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`
}

/**
 * 获取文件扩展名
 * @param {string} filename 文件名
 * @returns {string}
 */
export const getFileExtension = (filename) => {
  return filename.slice((filename.lastIndexOf('.') - 1 >>> 0) + 2)
}

/**
 * 下载文件
 * @param {string} url 文件URL
 * @param {string} filename 保存的文件名
 */
export const downloadFile = (url, filename) => {
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

/**
 * 读取文件为 Data URL
 * @param {File} file 文件对象
 * @returns {Promise<string>}
 */
export const readFileAsDataURL = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

/**
 * 读取文件为文本
 * @param {File} file 文件对象
 * @returns {Promise<string>}
 */
export const readFileAsText = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = reject
    reader.readAsText(file)
  })
}

/**
 * 将 Base64 转换为 Blob
 * @param {string} base64 Base64 字符串
 * @returns {Blob}
 */
export const base64ToBlob = (base64) => {
  const parts = base64.split(';base64,')
  const contentType = parts[0].split(':')[1]
  const raw = window.atob(parts[1])
  const rawLength = raw.length
  const uInt8Array = new Uint8Array(rawLength)

  for (let i = 0; i < rawLength; ++i) {
    uInt8Array[i] = raw.charCodeAt(i)
  }

  return new Blob([uInt8Array], { type: contentType })
}

/**
 * 将 Blob 转换为 File
 * @param {Blob} blob Blob 对象
 * @param {string} filename 文件名
 * @returns {File}
 */
export const blobToFile = (blob, filename) => {
  return new File([blob], filename, { type: blob.type })
}

/**
 * 批量下载文件并打包为zip
 * @param {Array<{url: string, filename: string}>} files 文件列表
 * @param {string} zipName zip文件名
 * @param {Object} options 选项
 * @param {Function} options.onProgress 进度回调
 * @param {Object} options.headers 请求头
 */
export const downloadFilesAsZip = async (files, zipName, { 
  onProgress, 
  headers = {} 
} = {}) => {
  const zip = new JSZip();
  const total = files.length;
  let completed = 0;

  try {
    // 下载所有文件
    const promises = files.map(async ({ url, filename }) => {
      const response = await fetch(url, { headers });
      if (!response.ok) throw new Error(`下载失败: ${filename}`);
      
      const blob = await response.blob();
      zip.file(filename, blob);
      
      completed++;
      onProgress?.({ completed, total, percentage: (completed / total) * 100 });
    });

    await Promise.all(promises);

    // 生成zip文件
    const zipBlob = await zip.generateAsync({ type: 'blob' });
    downloadFile(URL.createObjectURL(zipBlob), zipName);

  } catch (error) {
    throw new Error(`打包下载失败: ${error.message}`);
  }
};

/**
 * 检查文件类型是否允许
 * @param {File} file 文件对象
 * @param {string[]} allowedTypes 允许的MIME类型
 * @returns {boolean} 是否允许
 */
export const isFileTypeAllowed = (file, allowedTypes) => {
  return allowedTypes.includes(file.type);
};

/**
 * 生成唯一文件名
 * @param {string} originalName 原始文件名
 * @returns {string} 唯一文件名
 */
export const generateUniqueFilename = (originalName) => {
  const ext = getFileExtension(originalName);
  const timestamp = Date.now();
  const random = Math.random().toString(36).substring(2, 8);
  return `${timestamp}-${random}.${ext}`;
}; 