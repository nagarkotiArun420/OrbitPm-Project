import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import LoadingSpinner from '../components/common/LoadingSpinner';

const ProtectedRoute = ({ allowedRoles = [] }) => {
  const { user, loading } = useAuth();

  // Show a full-screen loading spinner while Auth session bootstraps
  if (loading) {
    return <LoadingSpinner fullScreen tip="Verifying authorization..." />;
  }

  // No session exists, bounce to public login page
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Gated endpoint, check user roles
  if (allowedRoles.length > 0 && !allowedRoles.includes(user.role)) {
    return <Navigate to="/404" replace />;
  }

  // Session is fully verified, render matched nested children
  return <Outlet />;
};

export default ProtectedRoute;
