import { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import useAuth from "../hooks/useAuth";
import useRefreshToken from "../hooks/useRefreshToken";
import { useAxiosPrivate } from "../hooks/useAxiosPrivate";

export default function PersistLogin({ fallback = "Loading" }) {
  const refresh = useRefreshToken();
  const { access_token } = useAuth();
  const [loading, setLoading] = useState(true);
  useAxiosPrivate();

  useEffect(() => {
    let mounted = true;

    async function verifyUser() {
      try {
        await refresh();
      } catch {
        // A missing or expired session is handled by the protected route.
      } finally {
        if (mounted) setLoading(false);
      }
    }

    if (access_token) setLoading(false);
    else verifyUser();

    return () => { mounted = false; };
  }, [access_token, refresh]);

  return loading ? fallback : <Outlet />;
}
