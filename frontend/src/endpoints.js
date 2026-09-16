// Derived from whatever host the app was opened on, not hardcoded. The auth cookies
// are SameSite=Strict, and localhost and 127.0.0.1 count as different sites — pinning
// the API to one of them means opening the app on the other silently drops the
// refresh_token cookie, so login works but every reload logs you back out. SameSite
// ignores the port, so same hostname on :8000 stays same-site either way.
export const API_HOST =
  process.env.REACT_APP_API_HOST ||
  `${window.location.protocol}//${window.location.hostname}:8000`

export const API_BASE_URL = `${API_HOST}/api/`
export const LOGIN_URL = API_BASE_URL+"login/"
export const REFRESH_URL = API_BASE_URL+"token/refresh/"

export const REGISTER_URL = API_BASE_URL+"register/"