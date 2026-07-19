import {
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import api from "../services/api";
import type { User, LoginCredentials, RegisterCredentials, TokenResponse } from "../types";
import { AuthContext } from "./auth-context";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(
    localStorage.getItem("access_token")
  );
  const [isLoading, setIsLoading] = useState(true);

  const fetchUser = useCallback(async () => {
    if (!token) {
      setIsLoading(false);
      return;
    }
    try {
      const response = await api.get<User>("/auth/me");
      setUser(response.data);
    } catch {
      setToken(null);
      setUser(null);
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const login = async (credentials: LoginCredentials) => {
    try {
      const response = await api.post<TokenResponse>("/auth/login", credentials);
      const accessToken = response.data.access_token;
      localStorage.setItem("access_token", accessToken);
      localStorage.setItem("refresh_token", response.data.refresh_token);

      const userResponse = await api.get<User>("/auth/me");
      setToken(accessToken);
      setUser(userResponse.data);
    } catch (error) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      setToken(null);
      setUser(null);
      throw error;
    }
  };

  const register = async (credentials: RegisterCredentials) => {
    await api.post("/auth/register", credentials);
    await login({ username: credentials.username, password: credentials.password });
  };

  const logout = async () => {
    const refreshToken = localStorage.getItem("refresh_token");
    if (refreshToken && token) {
      try {
        await api.post("/auth/logout", { refresh_token: refreshToken });
      } catch {}
    }
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
