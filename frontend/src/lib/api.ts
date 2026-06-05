import axios, { type AxiosInstance } from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_PREFIX = "/api/v1";

export const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_URL}${API_PREFIX}`,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
  withCredentials: true,   // send httpOnly JWT cookie on every request
});

apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    const message =
      err.response?.data?.detail ?? err.message ?? "Unknown error";
    return Promise.reject(new Error(message));
  }
);
