// localhost, not 127.0.0.1: the auth cookies are SameSite=Strict, and browsers treat
// localhost and 127.0.0.1 as different sites. Served from localhost:3000, an API on
// 127.0.0.1 is cross-site, so the refresh_token cookie is never sent and PersistLogin
// fails on every reload. SameSite ignores the port, so localhost:8000 is same-site.
export const API_BASE_URL = "http://localhost:8000/api/"
export const LOGIN_URL = API_BASE_URL+"login/"
export const REFRESH_URL = API_BASE_URL+"token/refresh/"

export const REGISTER_URL = API_BASE_URL+"register/"