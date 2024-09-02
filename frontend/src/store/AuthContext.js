import { useState, createContext } from 'react'


export const AuthContext = createContext({
    user: {},
    setUser: () => { },
    access_token: null,
    refresh_token: null,
    csrftoken: null,
    setAccessToken: () => { },
    setRefreshToken: () => { },
    setCSRFToken: () => { }
})

export function AuthContextProvider(props) {

    const [user, setUser] = useState({})
    const [access_token, setAccessToken] = useState()
    const [refresh_token, setRefreshToken] = useState()
    const [csrftoken, setCSRFToken] = useState()

    return <AuthContext.Provider value={{
        user, setUser,
        access_token, setAccessToken,
        refresh_token, setRefreshToken,
        csrftoken, setCSRFToken
    }}>
        {props.children}
    </AuthContext.Provider>
}

export default AuthContext