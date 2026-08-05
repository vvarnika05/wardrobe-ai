import { createContext, useContext, useEffect, useState } from "react";
import * as api from "../api/client";

const AuthContext = createContext(null);

/**
 * Holds JWT + user for the whole app.
 * Token lives in localStorage so a browser refresh does not log the user out.
 */
export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => api.getStoredToken());
  const [user, setUser] = useState(null);
  // True while we restore session from localStorage on first load.
  const [loading, setLoading] = useState(true);

  // On mount (and whenever token changes), load /auth/me if we have a token.
  useEffect(() => {
    let cancelled = false;

    async function restoreSession() {
      if (!token) {
        setUser(null);
        setLoading(false);
        return;
      }

      setLoading(true);
      try {
        const me = await api.getMe();
        if (!cancelled) {
          setUser(me);
        }
      } catch {
        // Token missing/expired/invalid — clear it so we don't loop.
        if (!cancelled) {
          api.clearStoredToken();
          setToken(null);
          setUser(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    restoreSession();
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function signup(email, password) {
    const result = await api.signup(email, password);
    api.setStoredToken(result.access_token);
    setToken(result.access_token);
    // getMe will run via the useEffect above once token updates,
    // but we also fetch immediately so callers can redirect right away.
    const me = await api.getMe();
    setUser(me);
    setLoading(false);
    return me;
  }

  async function login(email, password) {
    const result = await api.login(email, password);
    api.setStoredToken(result.access_token);
    setToken(result.access_token);
    const me = await api.getMe();
    setUser(me);
    setLoading(false);
    return me;
  }

  function logout() {
    api.clearStoredToken();
    setToken(null);
    setUser(null);
  }

  const value = {
    token,
    user,
    loading,
    isAuthenticated: Boolean(token && user),
    signup,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return ctx;
}
