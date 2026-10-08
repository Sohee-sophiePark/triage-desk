import axios from 'axios';
import { DEMO } from '../demo';

let _token: string | null = null;

export const setAuthToken = (token: string | null) => {
  _token = token;
};

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  headers: { 'Content-Type': 'application/json' },
});

if (DEMO) {
  // Serve GETs from exported JSON snapshots (public/demo/<path>[/page-N].json); writes are refused.
  api.defaults.adapter = async (config) => {
    if ((config.method ?? 'get') !== 'get') throw new Error('This demo is read-only.');
    const page = config.params?.page;
    const res = await fetch(`${import.meta.env.BASE_URL}demo${config.url}${page ? `/page-${page}` : ''}.json`);
    if (!res.ok) throw new Error(`Not in demo data: ${config.url}`);
    return { data: await res.json(), status: 200, statusText: 'OK', headers: {}, config };
  };
}

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
