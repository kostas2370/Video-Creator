// Same origin by default. nginx serves the app and proxies /api to Django, and in
// development CRA's own proxy (see package.json) does the same — so the auth cookies
// are never cross-site and there is no host to get wrong. REACT_APP_API_HOST is there
// for the case where the API really does live somewhere else.
export const API_HOST = process.env.REACT_APP_API_HOST || ""

export const API_BASE_URL = `${API_HOST}/api/`
export const LOGIN_URL = API_BASE_URL+"login/"
export const REFRESH_URL = API_BASE_URL+"token/refresh/"

export const REGISTER_URL = API_BASE_URL+"register/"