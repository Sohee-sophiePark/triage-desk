import React, { createContext, useContext, useState, ReactNode } from 'react';
import { jwtDecode } from 'jwt-decode';
import { setAuthToken } from '../services/api';
import { DEMO } from '../demo';

interface JwtPayload {
  sub: string;
  role: string;
  exp: number;
}

interface User {
  id: string;
  role: string;
  exp: number;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (token: string) => void;
  switchPersona: (role: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(DEMO ? { id: 'demo', role: 'admin', exp: 0 } : null);
  const [token, setToken] = useState<string | null>(DEMO ? 'demo' : null);

  const switchPersona = (role: string) => {
    setToken('demo');
    setUser({ id: 'demo', role, exp: 0 });
  };

  const login = (newToken: string) => {
    const decoded = jwtDecode<JwtPayload>(newToken);
    setToken(newToken);
    setUser({ id: decoded.sub, role: decoded.role, exp: decoded.exp });
    setAuthToken(newToken);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    setAuthToken(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, switchPersona, logout, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
