import axios from "axios"
// Imported rather than repeated: these must stay identical, or requests would be
// split across two origins and the SameSite cookies would only reach one of them.
import { API_BASE_URL as API_URL } from "../endpoints"

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