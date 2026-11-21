import { createContext, useContext, useEffect, useState } from "react";
import { getDeployment } from "../api/apiService";

const DeploymentContext = createContext({ sadtalker_enabled: true, invite_only: false });

export function DeploymentProvider({ children }) {
  const [deployment, setDeployment] = useState({ sadtalker_enabled: false, invite_only: true });
  useEffect(() => {
    let active = true;
    getDeployment().then(result => {
      const data = result.data;
      if (active && result.ok && typeof data?.sadtalker_enabled === "boolean" && typeof data?.invite_only === "boolean") {
        setDeployment({ sadtalker_enabled: data.sadtalker_enabled, invite_only: data.invite_only });
      }
    }).catch(() => {});
    return () => { active = false; };
  }, []);
  return <DeploymentContext.Provider value={deployment}>{children}</DeploymentContext.Provider>;
}

export const useDeployment = () => useContext(DeploymentContext);
