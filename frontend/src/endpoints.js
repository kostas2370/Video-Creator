// Same origin by default. nginx serves the app and proxies /api to Django, and in
// development CRA's own proxy (see package.json) does the same — so the auth cookies
// are never cross-site and there is no host to get wrong. REACT_APP_API_HOST is there
// for the case where the API really does live somewhere else.
export const API_HOST = process.env.REACT_APP_API_HOST || ""

export const API_BASE_URL = `${API_HOST}/api/`
// Relative to API_BASE_URL, which is the axios baseURL — see api/axiosPrivate.
export const LOGIN_URL = "login/"
export const REFRESH_URL = "token/refresh/"

export const REGISTER_URL = "register/"

// django_rest_passwordreset, mounted under api/password_reset/ in usermanagement/urls.
// The first mints a token and emails the link; the other two are what that link's page
// calls back with.
export const PASSWORD_RESET_URL = "password_reset/"
export const PASSWORD_RESET_CONFIRM_URL = "password_reset/confirm/"
export const PASSWORD_RESET_VALIDATE_URL = "password_reset/validate_token/"