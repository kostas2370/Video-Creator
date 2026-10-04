import axios from "axios";
import { API_BASE_URL } from "../endpoints";

const config = { baseURL: API_BASE_URL, withCredentials: true };
// Axios selects JSON for objects and lets the browser set FormData boundaries.
export const axiosInstance = axios.create(config);
export const axiosPrivateInstance = axios.create(config);
