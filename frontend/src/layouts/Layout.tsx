import React, { useEffect } from 'react';
import { Outlet, Navigate, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard,
  Users,
  ShieldAlert,
  Scale,
  BarChart2,
  Gem,
  LogOut,
  UserCircle,
  Settings,
  Sun,
  Moon,
} from 'lucide-react';
import { useThemeStore } from '../stores/themeStore';

const Layout = () => {
  const { isAuthenticated, user, logout } = useAuth();
  const location = useLocation();
  const { theme, toggleTheme } = useThemeStore();

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [theme]);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const navigation = [
    { name: 'Dashboard', href: '/', icon: LayoutDashboard },
    { name: 'Customers', href: '/customers', icon: Users },
    { name: 'Risk & Fraud', href: '/risk-fraud', icon: ShieldAlert },
    { name: 'Compliance', href: '/compliance', icon: Scale },
    { name: 'Analytics', href: '/analytics', icon: BarChart2 },
    ...(user?.role === 'admin' ? [{ name: 'Admin', href: '/admin', icon: Settings }] : []),
  ];

  return (
    <div className="min-h-screen bg-background flex flex-col md:flex-row">
      {/* Sidebar Navigation */}
      <div className="w-full md:w-64 bg-card border-r border-border flex-shrink-0 flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-border">
          <Gem className="h-8 w-8 text-primary mr-3" />
          <span className="text-foreground font-bold text-xl tracking-wide">TRIAGE DESK</span>
        </div>

        <div className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
          {navigation.map((item) => {
            const isActive =
              item.href === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(item.href);
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`${
                  isActive
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                } group flex items-center px-3 py-2.5 text-sm font-medium rounded-md transition-colors`}
              >
                <item.icon
                  className={`${
                    isActive ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground'
                  } mr-3 h-5 w-5`}
                  aria-hidden="true"
                />
                {item.name}
              </Link>
            );
          })}
        </div>

        <div className="px-4 pb-2">
          <button
            onClick={toggleTheme}
            className="w-full flex items-center px-3 py-2.5 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted rounded-md transition-colors"
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? (
              <Sun className="mr-3 h-5 w-5" />
            ) : (
              <Moon className="mr-3 h-5 w-5" />
            )}
            {theme === 'dark' ? 'Light mode' : 'Dark mode'}
          </button>
        </div>

        <div className="p-4 border-t border-border">
          <div className="flex items-center">
            <div>
              <UserCircle className="inline-block h-8 w-8 rounded-full text-muted-foreground" />
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-foreground break-all">
                {user?.id}
              </p>
              <p className="text-xs font-medium text-primary capitalize">
                {user?.role.replace('_', ' ')}
              </p>
            </div>
          </div>
          <button
            onClick={logout}
            className="mt-4 w-full flex items-center justify-center px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground bg-muted hover:bg-muted/80 rounded-md transition-colors"
          >
            <LogOut className="mr-2 h-4 w-4" />
            Sign out
          </button>
        </div>
      </div>

      {/* Main Container */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <main className="flex-1 overflow-y-auto bg-background p-6 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default Layout;
