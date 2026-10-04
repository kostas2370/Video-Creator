import useAuth from "./useAuth";
import { logout as logoutRequest } from "../api/apiService";
import { toast } from "react-toastify";

export default function useLogout() {
  const { setUser, setAccessToken, setCSRFToken } = useAuth();
  return async () => {
    const result = await logoutRequest();
    if (!result.ok) { toast.error(result.message); return false; }
    setAccessToken(null); setCSRFToken(null); setUser({});
    return true;
  };
}
