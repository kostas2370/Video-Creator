import axios from "axios";
import { API_BASE_URL } from "../endpoints";

const config = { baseURL: API_BASE_URL, withCredentials: true };
export const axiosInstance = axios.create(config);
export const axiosPrivateInstance = axios.create(config);
let csrfToken;
let csrfRequest;

// Bootstrap after page reload as well as before login. HttpOnly cookies stay private.
const ensureCSRFToken = async () => {
  if (csrfToken) return csrfToken;
  if (!csrfRequest) {
    csrfRequest = axiosInstance.get("csrf/")
      .then(response => response.headers["x-csrftoken"])
      .finally(() => { csrfRequest = undefined; });
  }
  return csrfRequest;
};

for (const client of [axiosInstance, axiosPrivateInstance]) {
  client.interceptors.request.use(async request => {
    if (!["get", "head", "options"].includes((request.method || "get").toLowerCase())) {
      request.headers["X-CSRFToken"] = await ensureCSRFToken();
    }
    return request;
  });
  client.interceptors.response.use(response => {
    if (response.headers["x-csrftoken"]) csrfToken = response.headers["x-csrftoken"];
    return response;
  });
}
