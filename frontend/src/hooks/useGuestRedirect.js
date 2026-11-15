import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Cookies from "js-cookie";
import useAuth from "./useAuth";

export function useGuestRedirect() {
  const { access_token } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const token = Cookies.get("access_token");
    if (access_token || (token && token !== "ey")) navigate("/", { replace: true });
  }, [access_token, navigate]);
}
