import { API_BASE_URL } from "../endpoints"
import { toast } from "react-toastify";

export const SetupInterceptors = http => {

    http.interceptors.request.use(
        config => {
            config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`
            config.headers['content-type'] = 'multipart/form-data'
            return config
        },
        error => {
            return Promise.reject(error)
        }
    )

    http.interceptors.response.use(function(response) {
        return response
    }, function (error) {
        const status = error?.response?.status || 0
        if (status === 401) {
            if (localStorage.getItem('token')) {
                localStorage.clear()
                window.location.assign('/')
                return Promise.reject(error)
            } else {
                return Promise.reject(error)
            }
        }
        if (status === 500){
            toast.error("Internal Server Error")
            return Promise.reject(error)
        }
       
        if (status === 400){
            toast.error("400 Bad Request !")
            return Promise.reject(error)
        }
        if (status === 404){
            toast.error("404 Not Found !")
            return Promise.reject(error)
        }
        if (status === 403){
            toast.error("No permission !")
            return Promise.reject(error)
        }


        
        return Promise.reject(error)
    })
}

export default SetupInterceptors