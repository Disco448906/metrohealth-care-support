import React, { useState, useEffect, useCallback } from 'react';
import { Sidebar } from '../components/Sidebar';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line, Legend, AreaChart, Area
} from 'recharts';
import { BarChart3, TrendingUp, ShieldAlert, RefreshCw } from 'lucide-react';
import api from '../services/api';

export const AnalyticsPage = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchAnalytics = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true);
    try {
      const res = await api.get('/api/analytics');
      setData(res.data);
      setLastUpdated(new Date());
    } catch (err) {
      console.error("Analytics fetch error:", err);
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAnalytics();
    const refreshTimer = window.setInterval(() => fetchAnalytics({ silent: true }), 15000);
    return () => window.clearInterval(refreshTimer);
  }, [fetchAnalytics]);

  const SEVERITY_COLORS = {
    LOW: '#10b981',
    MEDIUM: '#f59e0b',
    HIGH: '#f97316',
    CRITICAL: '#e11d48'
  };

  const catData = data?.complaints_by_category
    ? Object.keys(data.complaints_by_category).map((key) => ({
        name: key,
        count: data.complaints_by_category[key]
      }))
    : [];

  const sevData = data?.complaints_by_severity
    ? Object.keys(data.complaints_by_severity).map((key) => ({
        name: key,
        value: data.complaints_by_severity[key],
        color: SEVERITY_COLORS[key] || '#64748b'
      }))
    : [];

  const autoVsTicketData = [
    { name: 'Resolved in self-service', value: data?.auto_resolutions_count ?? 0, color: '#0284c7' },
    { name: 'Appointment assistance', value: data?.appointment_assistances_count ?? 0, color: '#10b981' },
    { name: 'Support tickets', value: data?.total_tickets_count ?? 0, color: '#8b5cf6' }
  ].filter((item) => item.value > 0);

  const statusData = data?.tickets_by_status
    ? Object.keys(data.tickets_by_status).map((key) => ({
        status: key,
        count: data.tickets_by_status[key]
      }))
    : [];

  return (
    <div className="flex bg-slate-50 min-h-[calc(100vh-4rem)]">
      <Sidebar />

      <main className="flex-1 p-6 space-y-8 overflow-x-hidden">
        
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight flex items-center space-x-2">
              <BarChart3 className="w-6 h-6 text-medical-600" />
              <span>Customer Support Analytics</span>
            </h1>
            <p className="text-xs text-slate-500">
              Live service outcomes from recorded customer interactions and staff tickets{lastUpdated ? ` · Updated ${lastUpdated.toLocaleTimeString()}` : ''}
            </p>
          </div>
          <button
            onClick={fetchAnalytics}
            className="px-3.5 py-2 bg-white border border-slate-300 rounded-xl text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors flex items-center space-x-1.5 shadow-sm"
          >
            <RefreshCw className="w-4 h-4 text-slate-500" />
            <span>Refresh Analytics</span>
          </button>
        </div>

        {/* SLA Top Metric Cards */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm space-y-1">
            <span className="text-xs font-bold text-sky-600 block uppercase">Self-service resolved</span>
            <div className="text-3xl font-black text-sky-700">{data?.auto_resolution_rate ?? 0}%</div>
            <span className="text-[10px] text-slate-500">FAQs and completed appointment actions</span>
          </div>

          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm space-y-1">
            <span className="text-xs font-bold text-purple-600 block uppercase">Ticket Creation %</span>
            <div className="text-3xl font-black text-purple-700">{data?.ticket_creation_rate ?? 0}%</div>
            <span className="text-[10px] text-slate-500">Human support queue</span>
          </div>

          <div className="bg-white p-4 rounded-2xl border border-rose-200 bg-rose-50/30 shadow-sm space-y-1">
            <span className="text-xs font-bold text-rose-700 block uppercase flex items-center space-x-1">
              <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
              <span>Critical Issues</span>
            </span>
            <div className="text-3xl font-black text-rose-800">{data?.critical_tickets_count || 0}</div>
            <span className="text-[10px] text-rose-600 font-bold">Safety escalations</span>
          </div>

          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm space-y-1">
            <span className="text-xs font-bold text-amber-600 block uppercase">Open Tickets</span>
            <div className="text-3xl font-black text-amber-700">{data?.open_tickets_count || 0}</div>
            <span className="text-[10px] text-slate-500">Unresolved cases</span>
          </div>

          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm space-y-1">
            <span className="text-xs font-bold text-emerald-600 block uppercase">Resolved Tickets</span>
            <div className="text-3xl font-black text-emerald-700">{data?.resolved_tickets_count || 0}</div>
            <span className="text-[10px] text-slate-500">Successfully closed</span>
          </div>

          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm space-y-1">
            <span className="text-xs font-bold text-slate-600 block uppercase">Avg resolution time</span>
            <div className="text-3xl font-black text-slate-800">{data?.average_resolution_hours != null ? `${data.average_resolution_hours}h` : '—'}</div>
            <span className="text-[10px] text-slate-500">Resolved tickets only</span>
          </div>

        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          
          {/* Chart 1: Complaints by Category */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <h3 className="font-bold text-slate-900 text-base">Customer interactions by category</h3>
            <div className="h-64">
              {catData.length === 0 ? <p className="flex h-full items-center justify-center text-sm text-slate-500">No interactions recorded yet.</p> : <ResponsiveContainer width="100%" height="100%">
                <BarChart data={catData}>
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} tickLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} />
                  <Tooltip cursor={{ fill: '#f1f5f9' }} />
                  <Bar dataKey="count" fill="#0284c7" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>}
            </div>
          </div>

          {/* Chart 2: Complaints by Severity */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <h3 className="font-bold text-slate-900 text-base">Interactions by severity</h3>
            <div className="h-64">
              {(data?.total_complaints || 0) === 0 ? <p className="flex h-full items-center justify-center text-sm text-slate-500">No interactions recorded yet.</p> : <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={sevData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                  >
                    {sevData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>}
            </div>
          </div>

          {/* Chart 3: Auto-Resolution vs Ticket Creation */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <h3 className="font-bold text-slate-900 text-base">Interaction outcome mix</h3>
            <div className="h-64">
              {autoVsTicketData.length === 0 ? <p className="flex h-full items-center justify-center text-sm text-slate-500">No interactions recorded yet.</p> : <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={autoVsTicketData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={85}
                    paddingAngle={5}
                    label
                  >
                    {autoVsTicketData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend verticalAlign="bottom" height={36} />
                </PieChart>
              </ResponsiveContainer>}
            </div>
          </div>

          {/* Chart 4: Ticket Status Distribution */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <h3 className="font-bold text-slate-900 text-base">Ticket Pipeline Status Distribution</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={statusData}>
                  <XAxis dataKey="status" stroke="#94a3b8" fontSize={12} tickLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} />
                  <Tooltip cursor={{ fill: '#f1f5f9' }} />
                  <Bar dataKey="count" fill="#8b5cf6" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>

        {/* Full-width Trend Chart */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="font-bold text-slate-900 text-base flex items-center space-x-2">
              <TrendingUp className="w-5 h-5 text-medical-600" />
              <span>Monthly interaction trends & resolution volume</span>
            </h3>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data?.monthly_trends || []}>
                <XAxis dataKey="month" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={12} />
                <Tooltip />
                <Legend />
                <Area type="monotone" dataKey="complaints" name="Total Interactions" stroke="#0284c7" fill="#e0f2fe" />
                <Area type="monotone" dataKey="auto_resolved" name="Resolved in self-service" stroke="#10b981" fill="#d1fae5" />
                <Area type="monotone" dataKey="appointment_assisted" name="Appointment assistance" stroke="#f59e0b" fill="#fef3c7" />
                <Area type="monotone" dataKey="tickets" name="Tickets Created" stroke="#8b5cf6" fill="#ede9fe" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

      </main>
    </div>
  );
};
