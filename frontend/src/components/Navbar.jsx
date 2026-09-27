import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Activity, LayoutDashboard, BarChart3, LogOut, ShieldCheck, Stethoscope, MessageCircle, CalendarDays, UserRound } from 'lucide-react';

export const Navbar = () => {
  const { user, logout, isAdmin, isDoctor } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path) => location.pathname === path;

  return (
    <nav className="bg-white border-b border-slate-200 sticky top-0 z-40 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center space-x-3">
            <Link to="/" className="flex items-center space-x-2">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-medical-600 to-medical-500 flex items-center justify-center text-white shadow-md">
                <Activity className="w-6 h-6" />
              </div>
              <div>
                <span className="text-lg font-bold text-slate-900 tracking-tight block leading-tight">
                  MetroHealth <span className="text-medical-600">AI</span>
                </span>
                <span className="text-xs text-slate-500 font-medium block">
                  Customer Care System
                </span>
              </div>
            </Link>

            {/* Navigation links */}
            {user && (
              <div className="hidden md:flex ml-8 space-x-1">
                {isDoctor ? (
                  <Link
                    to="/doctor"
                    className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center space-x-1.5 ${
                      isActive('/doctor') ? 'bg-medical-50 text-medical-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                    }`}
                  >
                    <Stethoscope className="w-4 h-4" />
                    <span>Doctor Schedule</span>
                  </Link>
                ) : !isAdmin ? (
                  <>
                    <Link
                      to="/dashboard"
                      className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center space-x-1.5 ${
                        isActive('/dashboard') ? 'bg-medical-50 text-medical-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                      }`}
                    >
                      <CalendarDays className="w-4 h-4" />
                      <span>My care</span>
                    </Link>
                    <Link
                      to="/chat"
                      className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center space-x-1.5 ${
                        isActive('/chat') ? 'bg-medical-50 text-medical-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                      }`}
                    >
                      <MessageCircle className="w-4 h-4" />
                      <span>Care assistant</span>
                    </Link>
                    <Link
                      to="/profile"
                      className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center space-x-1.5 ${
                        isActive('/profile') ? 'bg-medical-50 text-medical-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                      }`}
                    >
                      <UserRound className="w-4 h-4" />
                      <span>My profile</span>
                    </Link>
                  </>
                ) : (
                  <>
                    <Link
                      to="/admin"
                      className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center space-x-1.5 ${
                        isActive('/admin') ? 'bg-medical-50 text-medical-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                      }`}
                    >
                      <LayoutDashboard className="w-4 h-4" />
                      <span>Ticket Console</span>
                    </Link>
                    <Link
                      to="/admin/analytics"
                      className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center space-x-1.5 ${
                        isActive('/admin/analytics') ? 'bg-medical-50 text-medical-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                      }`}
                    >
                      <BarChart3 className="w-4 h-4" />
                      <span>Analytics</span>
                    </Link>
                  </>
                )}
              </div>
            )}
          </div>

          {/* User profile & Actions */}
          <div className="flex items-center space-x-4">
            {user && !isAdmin && !isDoctor && (
              <Link
                to="/profile"
                className="rounded-lg p-2 text-slate-500 transition-colors hover:bg-medical-50 hover:text-medical-700 md:hidden"
                title="My profile"
                aria-label="My profile"
              >
                <UserRound className="h-5 w-5" />
              </Link>
            )}
            {user ? (
              <div className="flex items-center space-x-3">
                <div className="text-right hidden sm:block">
                  <div className="text-sm font-semibold text-slate-800 flex items-center justify-end space-x-1">
                    <span>{user.name}</span>
                    {isAdmin ? <ShieldCheck className="w-4 h-4 text-emerald-600 inline" /> : isDoctor ? <Stethoscope className="w-4 h-4 text-medical-600 inline" /> : null}
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    isAdmin ? 'bg-emerald-100 text-emerald-800' : 'bg-medical-100 text-medical-800'
                  }`}>
                    {isAdmin ? 'Admin / Staff' : isDoctor ? 'Doctor Account' : 'Patient Account'}
                  </span>
                </div>

                <button
                  onClick={handleLogout}
                  className="p-2 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                  title="Sign Out"
                >
                  <LogOut className="w-5 h-5" />
                </button>
              </div>
            ) : (
              <div className="flex items-center space-x-2">
                <Link
                  to="/login"
                  className="px-4 py-2 text-sm font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  className="px-4 py-2 text-sm font-medium text-white bg-medical-600 hover:bg-medical-700 rounded-lg shadow-sm transition-colors"
                >
                  Register
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};
