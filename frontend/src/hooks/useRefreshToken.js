import { useCallback } from "react";
import useAuth from "./useAuth";
import { REFRESH_URL } from "../endpoints";
import { axiosInstance } from "../api/axiosPrivate";
export default function useRefreshToken() {
    const { setAccessToken, setCSRFToken } = useAuth()

    const refresh = useCallback(async () => {
        const response = await axiosInstance.post(REFRESH_URL)
        setAccessToken(response.data.access)
        setCSRFToken(response.headers["x-csrftoken"])

        return { accessToken: response.data.access, csrfToken: response.headers["x-csrftoken"] }
    }, [setAccessToken, setCSRFToken])

    return refresh
}