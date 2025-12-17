import React, { createContext, useContext, useState, useEffect } from 'react';

const ThemeContext = createContext(null);

export const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('orbitpm_theme') || 'light';
  });

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  useEffect(() => {
    localStorage.setItem('orbitpm_theme', theme);
    if (theme === 'dark') {
      document.body.classList.add('dark-mode');
      document.body.style.backgroundColor = '#141414';
      document.body.style.color = '#ffffff';
    } else {
      document.body.classList.remove('dark-mode');
      document.body.style.backgroundColor = '#fafafa';
      document.body.style.color = '#1f1f1f';
    }
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useAppTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useAppTheme must be run inside a ThemeProvider');
  }
  return context;
};
