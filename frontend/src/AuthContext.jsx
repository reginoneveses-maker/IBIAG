import { createContext, useContext, useState, useEffect } from "react";
import axios from "axios";

const BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/$/, "");
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API });
api.interceptors.request.use((cfg) => {
  const t = localStorage.getItem("token");
  if (t && !cfg.headers.Authorization) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

const AuthCtx = createContext({ user: null, login: () => {}, logout: () => {}, loading: true });

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = localStorage.getItem("token");
    if (!t) { setLoading(false); return; }
    api.get("/auth/me")
      .then(r => { if (localStorage.getItem("token") === t) setUser(r.data); })
      .catch(() => { if (localStorage.getItem("token") === t) localStorage.removeItem("token"); })
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const r = await api.post("/auth/login", { email, password });
    localStorage.setItem("token", r.data.access_token);
    setUser(r.data.user);
    return r.data.user;
  };

  const register = async (email, password, name) => {
    const r = await api.post("/auth/register", { email, password, name });
    localStorage.setItem("token", r.data.access_token);
    setUser(r.data.user);
    return r.data.user;
  };

  const logout = async () => {
    // Capture the session before clearing browser state. Explicit headers keep
    // this request tied to the old session if another login starts meanwhile.
    const token = localStorage.getItem("token");
    localStorage.removeItem("token");
    setUser(null);
    if (token) {
      try {
        await api.post("/auth/logout", null, {
          headers: { Authorization: `Bearer ${token}` }, timeout: 10000,
        });
        return true;
      } catch {
        // Local logout succeeds even offline; remote revocation is unconfirmed.
        return false;
      }
    }
    return true;
  };

  const changePassword = async (currentPassword, newPassword) => {
    const token = localStorage.getItem("token");
    if (!token) throw new Error("Session ended");
    await api.post("/auth/password", {current_password: currentPassword, new_password: newPassword},
      {headers: {Authorization: `Bearer ${token}`}, timeout: 15000});
    if (localStorage.getItem("token") === token) {
      localStorage.removeItem("token");
      setUser(null);
    }
  };

  return <AuthCtx.Provider value={{ user, login, register, logout, changePassword, loading }}>{children}</AuthCtx.Provider>;
};

export const useAuth = () => useContext(AuthCtx);
