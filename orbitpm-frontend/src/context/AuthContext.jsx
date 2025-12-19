import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Load API base endpoint URL
  const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

  const checkAuth = async () => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      // Set global Axios auth headers
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      const response = await axios.get(`${API_URL}/auth/me/`);
      
      // Standard response envelope is { success: true, data: { ... } }
      if (response.data?.success) {
        setUser(response.data.data);
      } else {
        logout();
      }
    } catch (error) {
      console.error("Auth session bootstrap failed:", error);
      // Attempt silent JWT recovery
      const isRecovered = await runSilentTokenRefresh();
      if (!isRecovered) {
        logout();
      }
    } finally {
      setLoading(false);
    }
  };

  const runSilentTokenRefresh = async () => {
    const refresh = localStorage.getItem('refreshToken');
    if (!refresh) return false;

    try {
      const response = await axios.post(`${API_URL}/auth/refresh/`, { refresh });
      
      // simplejwt custom view returns: { success: true, data: { access, refresh } }
      const responseData = response.data.success ? response.data.data : response.data;
      const { access, refresh: newRefresh } = responseData;

      localStorage.setItem('accessToken', access);
      if (newRefresh) {
        localStorage.setItem('refreshToken', newRefresh);
      }
      
      axios.defaults.headers.common['Authorization'] = `Bearer ${access}`;
      
      // Re-load user profile details
      const userResponse = await axios.get(`${API_URL}/auth/me/`);
      if (userResponse.data?.success) {
        setUser(userResponse.data.data);
        return true;
      }
      return false;
    } catch (e) {
      console.error("Background JWT rotation failed:", e);
      return false;
    }
  };

  const login = async (email, password) => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/auth/login/`, { email, password });
      const payload = response.data;
      
      // Unpack envelope
      const authData = payload.success ? payload.data : payload;
      const { access, refresh, user: userData } = authData;

      localStorage.setItem('accessToken', access);
      localStorage.setItem('refreshToken', refresh);
      
      axios.defaults.headers.common['Authorization'] = `Bearer ${access}`;
      setUser(userData);
      return { success: true };
    } catch (error) {
      let errMsg = 'Invalid email or password';
      if (error.response?.data) {
        const payloadErr = error.response.data;
        errMsg = payloadErr.message || payloadErr.error?.non_field_errors?.[0] || errMsg;
      }
      return { success: false, error: errMsg };
    } finally {
      setLoading(false);
    }
  };

  const register = async (email, password, confirmPassword, fullName, role, phoneNumber) => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/auth/register/`, {
        email,
        password,
        confirm_password: confirmPassword,
        full_name: fullName,
        role,
        phone_number: phoneNumber
      });
      return { success: true, message: response.data.message };
    } catch (error) {
      const err = error.response?.data?.error || { non_field_errors: ['Registration failed'] };
      return { success: false, error: err };
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    const refresh = localStorage.getItem('refreshToken');
    if (refresh) {
      try {
        await axios.post(`${API_URL}/auth/logout/`, { refresh });
      } catch (err) {
        console.error("Backend token blacklist failed during logout:", err);
      }
    }
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    delete axios.defaults.headers.common['Authorization'];
    setUser(null);
  };

  useEffect(() => {
    checkAuth();
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, runSilentTokenRefresh }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be executed within an AuthProvider scope');
  }
  return context;
};
