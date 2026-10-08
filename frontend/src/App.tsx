import React, { lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Layout from './layouts/Layout';
import Login from './pages/Login';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const Customers = lazy(() => import('./pages/Customers'));
const CustomerDetail = lazy(() => import('./pages/CustomerDetail'));
const RiskFraud = lazy(() => import('./pages/RiskFraud'));
const Compliance = lazy(() => import('./pages/Compliance'));
const Analytics = lazy(() => import('./pages/Analytics'));
const CaseDetail = lazy(() => import('./pages/CaseDetail'));
const Admin = lazy(() => import('./pages/Admin'));

const ALL_ROLES = ['admin', 'risk_analyst', 'fraud_investigator', 'compliance_officer'];
const CASE_ROLES = ['admin', 'risk_analyst', 'fraud_investigator', 'compliance_officer'];

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { token } = useAuth();
  return token ? <>{children}</> : <Navigate to="/login" replace />;
};

const RequireRole = ({ roles, children }: { roles: string[]; children: React.ReactNode }) => {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (!roles.includes(user.role)) return <Navigate to="/" replace />;
  return <>{children}</>;
};

function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route index element={<Dashboard />} />
            <Route
              path="customers"
              element={<RequireRole roles={ALL_ROLES}><Customers /></RequireRole>}
            />
            <Route
              path="customers/:id"
              element={<RequireRole roles={ALL_ROLES}><CustomerDetail /></RequireRole>}
            />
            <Route
              path="risk-fraud"
              element={<RequireRole roles={ALL_ROLES}><RiskFraud /></RequireRole>}
            />
            <Route
              path="compliance"
              element={<RequireRole roles={ALL_ROLES}><Compliance /></RequireRole>}
            />
            <Route
              path="analytics"
              element={<RequireRole roles={ALL_ROLES}><Analytics /></RequireRole>}
            />
            <Route
              path="cases/:id"
              element={<RequireRole roles={CASE_ROLES}><CaseDetail /></RequireRole>}
            />
            <Route
              path="admin"
              element={<RequireRole roles={['admin']}><Admin /></RequireRole>}
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
