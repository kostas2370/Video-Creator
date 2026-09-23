import { useEffect } from 'react';
import useAuth from "./useAuth";
import useRefreshToken from "./useRefreshToken";
import { axiosPrivateInstance } from "../api/axiosPrivate";

export function useAxiosPrivate() {

    const { access_token, setAccessToken, csrftoken } = useAuth();
    const refresh = useRefreshToken();

    useEffect(() => {

        const requestIntercept = axiosPrivateInstance.interceptors.request.use(
            (config) => {
                if (!config.headers["Authorization"]) {
                    if (access_token) {
                        config.headers["Authorization"] = `Bearer ${access_token}`;
                    }
                    config.headers['X-CSRFToken'] = csrftoken;
                }
                return config;
            },
            (error) => Promise.reject(error)
        );

        const responseIntercept = axiosPrivateInstance.interceptors.response.use(
            (response) => response,
            async (error) => {
                const status = error?.response?.status;
                const prevRequest = error?.config;

                if ((status === 403 || status === 401) && !prevRequest?.sent) {
                    prevRequest.sent = true;
                    const { csrfToken: newCSRFToken, accessToken: newAccessToken } = await refresh();
                    setAccessToken(newAccessToken);
                    prevRequest.headers['Authorization'] = `Bearer ${newAccessToken}`;
                    prevRequest.headers['X-CSRFToken'] = newCSRFToken;
                    return axiosPrivateInstance(prevRequest);
                }

                return Promise.reject(error);
            }
        );

        return () => {
            axiosPrivateInstance.interceptors.request.eject(requestIntercept);
            axiosPrivateInstance.interceptors.response.eject(responseIntercept);
        };
    }, [access_token, csrftoken, refresh, setAccessToken]);

    return axiosPrivateInstance;
}
