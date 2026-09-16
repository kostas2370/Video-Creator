// localhost, not 127.0.0.1: the auth cookies are SameSite=Strict and browsers treat
// the two hosts as different sites, so from localhost:3000 the refresh_token cookie
// would never be sent. SameSite ignores the port, so :8000 is still same-site.
export const API_BASE_URL = "http://localhost:8000/api/"
export const LOGIN_URL = API_BASE_URL+"login/"
export const REFRESH_URL = API_BASE_URL+"token/refresh/"

export const REGISTER_URL = API_BASE_URL+"register/"