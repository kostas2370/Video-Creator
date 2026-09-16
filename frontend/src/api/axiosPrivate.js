import axios from "axios"

// Must match API_BASE_URL in endpoints.js — see the SameSite note there.
const API_URL = "http://localhost:8000/api/"

export const axiosInstance = axios.create({
    baseURL: API_URL,
    withCredentials: true,
    headers: {
        "Content-Type": 'multipart/form-data'
    }
})

export const axiosPrivateInstance = axios.create({
    baseURL: API_URL,
    withCredentials: true,
    headers: {
        "Content-Type": 'multipart/form-data'
    }
})