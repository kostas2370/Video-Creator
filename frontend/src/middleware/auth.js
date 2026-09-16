import useAuth from "../useAuth"
import { Navigate, Outlet, useLocation } from "react-router-dom"

export default function AuthMiddleware() {
    const  accessToken  = useAuth()
    const location = useLocation()

    return (accessToken ? <Outlet /> : <Navigate to="/login/" state={{ from: location }} replace />)

}