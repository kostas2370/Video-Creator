import { toast } from "react-toastify";
import { useEffect } from 'react';
import useAuth from "./useAuth";
import useRefreshToken from "./useRefreshToken";
import { axiosPrivateInstance } from "../api/axiosPrivate";

export function useAxiosPrivate() {

    const { access_token, setAccessToken, csrftoken, user } = useAuth();
    const refresh = useRefreshToken();

    useEffect(() => {

        const requestIntercept = axiosPrivateInstance.interceptors.request.use(
            (config) => {
                if (!config.headers["Authorization"]) {
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
                    prevRequest.headers['X-CSRFToken'] = newCSRFToken;
                    return axiosPrivateInstance(prevRequest);
                }
         
                  else if (status === 400) {
                    toast.error("400 Bad Request !");
                } else if (status === 404) {
                    toast.error("404 Not Found !");
                } else if (status === 403) {
                    toast.error("No permission !");
                }
                toast.error("Internal Server Error");

                return Promise.reject(error);
            }
        );

        return () => {
            axiosPrivateInstance.interceptors.request.eject(requestIntercept);
            axiosPrivateInstance.interceptors.response.eject(responseIntercept);
        };
    }, [access_token , setAccessToken]);

    return axiosPrivateInstance;
}
