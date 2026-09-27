import axios from 'axios';

const configuredApiUrl = import.meta.env.VITE_API_URL?.trim();
const apiBaseUrl = (configuredApiUrl || 'https://metrohealth-care-support.onrender.com').replace(/\/+$/, '');

const api = axios.create({
  baseURL: apiBaseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to attach JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export default api;
