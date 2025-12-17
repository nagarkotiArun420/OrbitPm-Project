import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Injects active JWT Bearer credentials before every outbound call
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: Intercepts 401 expired statuses, triggers refresh tokens silently, and transparently retries requests
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Prevent infinite cycles by checking an internal retry flag
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('refreshToken');

      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh/`, {
            refresh: refreshToken,
          });

          // Extract token from standard envelope
          const responseData = response.data.success ? response.data.data : response.data;
          const { access } = responseData;

          localStorage.setItem('accessToken', access);
          
          // Re-attach header and retry original query
          originalRequest.headers['Authorization'] = `Bearer ${access}`;
          return apiClient(originalRequest);
        } catch (refreshError) {
          console.error("Session refresh cycle expired:", refreshError);
          // Wipe localStorage tokens and send user to login page
          localStorage.removeItem('accessToken');
          localStorage.removeItem('refreshToken');
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      } else {
        localStorage.removeItem('accessToken');
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;
