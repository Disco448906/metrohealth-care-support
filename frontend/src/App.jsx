import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { LandingPage } from './pages/LandingPage';

const CustomerDashboard = lazy(() => import('./pages/CustomerDashboard').then((module) => ({ default: module.CustomerDashboard })));
const ChatPage = lazy(() => import('./pages/ChatPage').then((module) => ({ default: module.ChatPage })));
const AdminDashboard = lazy(() => import('./pages/AdminDashboard').then((module) => ({ default: module.AdminDashboard })));
const AnalyticsPage = lazy(() => import('./pages/AnalyticsPage').then((module) => ({ default: module.AnalyticsPage })));
const DoctorDashboard = lazy(() => import('./pages/DoctorDashboard').then((module) => ({ default: module.DoctorDashboard })));
const PatientProfile = lazy(() => import('./pages/PatientProfile').then((module) => ({ default: module.PatientProfile })));

const homeForRole = (role) => role === 'admin' ? '/admin' : role === 'doctor' ? '/doctor' : '/dashboard';

const ProtectedRoute = ({ children, requiredRole }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 text-slate-500 font-medium text-sm">
        Authenticating session...
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (requiredRole && user.role !== requiredRole) {
    return <Navigate to={homeForRole(user.role)} replace />;
  }

  return children;
};

const AppContent = () => {
  const { user } = useAuth();

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 font-sans">
      <Navbar />
      <div className="flex-1">
        <Suspense fallback={
          <div className="flex min-h-[50vh] items-center justify-center px-6 text-sm font-medium text-slate-500" role="status">
            Loading your workspace…
          </div>
        }>
          <Routes>
            <Route
              path="/"
              element={
                user ? (
                  <Navigate to={homeForRole(user.role)} replace />
                ) : (
                  <LandingPage />
                )
              }
            />
            <Route path="/login" element={<Login />} />
            <Route path="/doctor-login" element={<Login doctorMode />} />
            <Route path="/register" element={<Register />} />

            <Route
              path="/profile"
              element={
                <ProtectedRoute requiredRole="customer">
                  <PatientProfile />
                </ProtectedRoute>
              }
            />

            {/* Customer Routes */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute requiredRole="customer">
                  <CustomerDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/chat"
              element={
                <ProtectedRoute requiredRole="customer">
                  <ChatPage />
                </ProtectedRoute>
              }
            />

            {/* Admin Routes */}
            <Route
              path="/admin"
              element={
                <ProtectedRoute requiredRole="admin">
                  <AdminDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/analytics"
              element={
                <ProtectedRoute requiredRole="admin">
                  <AnalyticsPage />
                </ProtectedRoute>
              }
            />

            <Route
              path="/doctor"
              element={
                <ProtectedRoute requiredRole="doctor">
                  <DoctorDashboard />
                </ProtectedRoute>
              }
            />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </div>
    </div>
  );
};

export function App() {
  return (
    <AuthProvider>
      <Router>
        <AppContent />
      </Router>
    </AuthProvider>
  );
}

export default App;
