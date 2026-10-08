import axios from 'axios';

let _token: string | null = null;

export const setAuthToken = (token: string | null) => {
  _token = token;
};

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  if (_token && config.headers) {
    config.headers.Authorization = `Bearer ${_token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && window.location.pathname !== '/login') {
      _token = null;
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
