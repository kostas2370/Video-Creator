import useAuth from "./useAuth"
import { axiosPrivateInstance } from "../api/axiosPrivate"
import Cookies from "js-cookie"
import { useNavigate } from "react-router-dom"
export default function useLogout() {
    const { setUser, setAccessToken, setCSRFToken } = useAuth()
    const {navigate}= useNavigate()

    const logout = async () => {
        try {
            await axiosPrivateInstance.post("logout/")

            setAccessToken(null)
            setCSRFToken(null)
            setUser({})

        } catch (error) {
            console.log(error)
        }
    }

    return logout
}