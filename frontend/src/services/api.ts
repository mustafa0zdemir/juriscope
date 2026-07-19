import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";
import type { TokenResponse } from "../types";

export const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api/v1";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

type RetryableRequest = InternalAxiosRequestConfig & { _retry?: boolean };

function clearStoredTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetryableRequest | undefined;
    const refreshToken = localStorage.getItem("refresh_token");
    const requestUrl = originalRequest?.url ?? "";
    const isAuthRequest = ["/auth/login", "/auth/register", "/auth/refresh"].some((path) => requestUrl.includes(path));

    if (error.response?.status === 401 && originalRequest && refreshToken && !originalRequest._retry && !isAuthRequest) {
      originalRequest._retry = true;
      try {
        const response = await axios.post<TokenResponse>(`${API_BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });
        localStorage.setItem("access_token", response.data.access_token);
        localStorage.setItem("refresh_token", response.data.refresh_token);
        originalRequest.headers.Authorization = `Bearer ${response.data.access_token}`;
        return api(originalRequest);
      } catch {
        clearStoredTokens();
        window.location.href = "/login";
      }
    } else if (error.response?.status === 401 && !isAuthRequest) {
      clearStoredTokens();
      window.location.href = "/login";
    }
    return Promise.reject(error);
  },
);

export default api;
