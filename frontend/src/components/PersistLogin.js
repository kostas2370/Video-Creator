import React, { useEffect, useState } from 'react'
import { Outlet } from 'react-router-dom'
import useAuth from '../hooks/useAuth'
import useRefreshToken from '../hooks/useRefreshToken'
import { useAxiosPrivate } from '../hooks/useAxiosPrivate'


export default function PersistLogin() {

    const refresh = useRefreshToken()
    // access_token is the name AuthContext exposes; accessToken reads as undefined.
    const { access_token, setUser } = useAuth()
    const [loading, setLoading] = useState(true)
    useAxiosPrivate()

    useEffect(() => {
        let isMounted = true

        async function verifyUser() {
            try {
                await refresh()
                
            } catch (error) {
                console.log(error?.response)
            } finally {
                isMounted && setLoading(false)
            }
        }

        !access_token ? verifyUser() : setLoading(false)

        return () => {
            isMounted = false
        }
    }, [])

    return (
        loading ? "Loading" : <Outlet />
    )
}