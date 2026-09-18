
// for the case where the API really does live somewhere else.
export const API_HOST = process.env.REACT_APP_API_HOST || ""

export const API_BASE_URL = `${API_HOST}/api/`
export const LOGIN_URL = "login/"
export const REFRESH_URL = "token/refresh/"

export const REGISTER_URL = "register/"
export const PASSWORD_RESET_URL = "password_reset/"
export const PASSWORD_RESET_CONFIRM_URL = "password_reset/confirm/"
export const PASSWORD_RESET_VALIDATE_URL = "password_reset/validate_token/"