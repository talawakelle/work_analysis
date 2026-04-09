import axios from "axios";
import { getAuthIdentity } from "../lib/auth";

const baseURL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";

export const api = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const identity = getAuthIdentity();
  if (identity.username) {
    config.headers["X-Auth-User"] = identity.username;
  }
  return config;
});
