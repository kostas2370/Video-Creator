import { useCallback } from "react";
import useAuth from "./useAuth";

import { refreshToken } from "../api/apiService";
export default function useRefreshToken() {
    const { setAccessToken, setCSRFToken } = useAuth()

    const refresh = useCallback(async () => {
        const response = await refreshToken();
        if (!response.ok) throw new Error(response.message);
        setAccessToken(response.data.access)
        setCSRFToken(response.headers["x-csrftoken"])

        return { accessToken: response.data.access, csrfToken: response.headers["x-csrftoken"] }
    }, [setAccessToken, setCSRFToken])

    return refresh
}