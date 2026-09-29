import { useEffect, useState } from "react";

export function useAuth() {
  const [token, setToken] = useState(() => localStorage.getItem("token"));

  useEffect(() => {
    if (token) localStorage.setItem("token", token);
    else localStorage.removeItem("token");
  }, [token]);

  return { token, login: setToken, logout: () => setToken(null) };
}
