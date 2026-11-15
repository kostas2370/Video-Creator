import { useContext, useDebugValue } from "react";
import AuthContext from "../store/AuthContext";

export default function useAuth() {
  const context = useContext(AuthContext);
  useDebugValue(context.access_token ? "Logged In" : "Logged Out");
  return context;
}
