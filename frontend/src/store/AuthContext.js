import { createContext, useState } from "react";

export const AuthContext = createContext({
  user: {},
  access_token: null,
  csrftoken: null,
  setUser: () => {},
  setAccessToken: () => {},
  setCSRFToken: () => {},
});

export function AuthContextProvider({ children }) {
  const [user, setUser] = useState({});
  const [access_token, setAccessToken] = useState();
  const [csrftoken, setCSRFToken] = useState();

  return (
    <AuthContext.Provider value={{ user, setUser, access_token, setAccessToken, csrftoken, setCSRFToken }}>
      {children}
    </AuthContext.Provider>
  );
}

export default AuthContext;
