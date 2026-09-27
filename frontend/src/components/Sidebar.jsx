import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Ticket, BarChart3, Users, Settings, AlertTriangle } from 'lucide-react';

export const Sidebar = () => {
  const location = useLocation();

  const links = [
    { path: '/admin', label: 'Dashboard & Tickets', icon: LayoutDashboard },
    { path: '/admin/analytics', label: 'Analytics & SLA', icon: BarChart3 },
  ];

  return (
    <aside className="w-64 bg-white border-r border-slate-200 min-h-[calc(100vh-4rem)] p-4 flex flex-col justify-between">
      <div className="space-y-6">
        <div>
          <span className="px-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Admin Console
          </span>
          <nav className="mt-2 space-y-1">
            {links.map((link) => {
              const Icon = link.icon;
              const active = location.pathname === link.path;
              return (
                <Link
                  key={link.path}
                  to={link.path}
                  className={`flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    active
                      ? 'bg-medical-50 text-medical-700 font-semibold'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="pt-4 border-t border-slate-100">
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-xs text-amber-800 space-y-1">
            <div className="flex items-center space-x-1.5 font-bold">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              <span>Critical Escalation Protocol</span>
            </div>
            <p className="text-slate-600 leading-relaxed">
              Critical tickets (Medication errors, safety incidents) are automatically assigned top priority queue.
            </p>
          </div>
        </div>
      </div>

      <div className="text-xs text-slate-400 text-center py-2">
        MetroHealth OS v1.0.0
      </div>
    </aside>
  );
};
