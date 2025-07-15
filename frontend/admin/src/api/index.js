import axios from 'axios';

// 动态获取API基础URL，支持配置
const getApiBaseUrl = () => {
  // 优先使用环境变量
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }

  // 从localStorage获取用户配置
  const savedApiServer = localStorage.getItem('apiServer');
  if (savedApiServer) {
    return savedApiServer.replace(/\/$/, '');
  }

  // 默认值：尝试当前域名的8000端口
  const currentHost = window.location.hostname;
  return `http://${currentHost}:8000`;
};

const api = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 15000, // 增加超时时间
});

// 请求拦截器
api.interceptors.request.use(
  config => {
    // 动态更新baseURL（支持运行时切换服务器）
    config.baseURL = getApiBaseUrl();

    // 添加认证token
    const token = localStorage.getItem('token') || localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // 添加请求日志
    console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, {
      baseURL: config.baseURL,
      headers: config.headers,
      data: config.data
    });

    return config;
  },
  error => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  response => {
    console.log(`[API Response] ${response.config.method?.toUpperCase()} ${response.config.url}`, {
      status: response.status,
      data: response.data
    });
    return response;
  },
  error => {
    console.error('[API Response Error]', {
      url: error.config?.url,
      status: error.response?.status,
      message: error.message,
      data: error.response?.data
    });

    // 处理认证失败
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('authToken');

      // 如果不在登录页面，跳转到登录页面
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }

    // 处理网络错误
    if (!error.response) {
      console.error('网络连接失败，请检查服务器状态');
    }

    return Promise.reject(error);
  }
);

// 导出API实例和工具函数
export default api;

// 导出配置函数，供组件使用
export const updateApiBaseUrl = (newUrl) => {
  localStorage.setItem('apiServer', newUrl);
  console.log(`API服务器地址已更新为: ${newUrl}`);
};

// 导出当前API地址获取函数
export const getCurrentApiUrl = () => getApiBaseUrl();