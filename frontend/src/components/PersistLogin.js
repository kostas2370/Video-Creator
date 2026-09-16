import React, { useEffect, useState } from 'react'
import { Outlet } from 'react-router-dom'
import useAuth from '../hooks/useAuth'
import useRefreshToken from '../hooks/useRefreshToken'
import { useAxiosPrivate } from '../hooks/useAxiosPrivate'


export default function PersistLogin() {

    const refresh = useRefreshToken()
    // access_token, not accessToken — that is the name AuthContext exposes. The
    // camelCase spelling was undefined forever, so the guard below never short-
    // circuited and every mount re-ran the refresh.
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