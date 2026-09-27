import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ArrowRight,
  BadgeCheck,
  CircleAlert,
  Clock3,
  FileCheck2,
  LayoutDashboard,
  LifeBuoy,
  RefreshCw,
  Search,
  ShieldCheck,
  CreditCard,
  UserRound,
  MessageSquareWarning,
} from 'lucide-react';
import api from '../services/api';
import AdminTicketResolutionPanel from '../components/AdminTicketResolutionPanel';
import { ADMIN_TICKET_CATEGORIES, categoryKeyForTicket, displayTicketStatus, formatTicketDate } from '../components/adminTicketCategories';

const SECTIONS = [
  { key: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  ...ADMIN_TICKET_CATEGORIES.map((category) => ({
    ...category,
    icon: ({ billing: CreditCard, account: UserRound, insurance: FileCheck2, service: MessageSquareWarning, other: LifeBuoy })[category.key],
  })),
  { key: 'resolved', label: 'Resolved Tickets', icon: BadgeCheck },
];

const STATUS_STYLES = {
  NEW: 'border-blue-200 bg-blue-50 text-blue-700',
  IN_PROGRESS: 'border-amber-200 bg-amber-50 text-amber-800',
  RESOLVED: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  ESCALATED: 'border-rose-200 bg-rose-50 text-rose-800',
};
const PRIORITY_STYLES = {
  LOW: 'bg-slate-100 text-slate-600',
  MEDIUM: 'bg-sky-50 text-sky-700',
  HIGH: 'bg-amber-50 text-amber-800',
  CRITICAL: 'bg-rose-50 text-rose-800',
};

function StatusPill({ status }) {
  const value = displayTicketStatus(status);
  const label = value.replaceAll('_', ' ');
  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide ${STATUS_STYLES[value]}`}>{label}</span>;
}

function PriorityPill({ ticket }) {
  const priority = String(ticket.priority || ticket.severity || 'MEDIUM').toUpperCase();
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${PRIORITY_STYLES[priority] || PRIORITY_STYLES.MEDIUM}`}>{priority.toLowerCase()}</span>;
}

function SummaryCard({ label, count, icon: Icon, tone, accent, onClick }) {
  return (
    <button type="button" onClick={onClick} className={`group relative overflow-hidden rounded-2xl border border-slate-200/80 border-t-[3px] ${accent} bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md sm:p-5`}>
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs font-semibold text-slate-500">{label}</span>
        <span className={`grid h-10 w-10 place-items-center rounded-2xl ${tone}`}><Icon className="h-4 w-4" /></span>
      </div>
      <p className="mt-2 text-3xl font-bold tracking-tight text-slate-900">{count}</p>
      <span className="mt-1 inline-flex items-center gap-1 text-[10px] font-semibold text-slate-400 transition group-hover:text-medical-700">View tickets <ArrowRight className="h-3 w-3 transition group-hover:translate-x-0.5" /></span>
    </button>
  );
}

function TicketTable({ tickets, onOpen, emptyMessage }) {
  if (!tickets.length) return <div className="grid place-items-center rounded-2xl border border-dashed border-slate-300 bg-white px-5 py-14 text-center"><span className="grid h-11 w-11 place-items-center rounded-2xl bg-slate-100 text-slate-400"><LifeBuoy className="h-5 w-5" /></span><p className="mt-3 text-sm font-semibold text-slate-700">No tickets here</p><p className="mt-1 max-w-sm text-xs leading-5 text-slate-500">{emptyMessage}</p></div>;

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[850px] border-collapse text-left">
          <thead><tr className="border-b border-slate-100 bg-slate-50/80 text-[10px] font-bold uppercase tracking-[0.12em] text-slate-500">
            <th className="px-5 py-3.5">Ticket ID</th><th className="px-4 py-3.5">Patient</th><th className="px-4 py-3.5">Problem</th><th className="px-4 py-3.5">Priority</th><th className="px-4 py-3.5">Created</th><th className="px-4 py-3.5">Status</th><th className="px-5 py-3.5"><span className="sr-only">Open ticket</span></th>
          </tr></thead>
          <tbody className="divide-y divide-slate-100">
            {tickets.map((ticket) => <tr key={ticket.ticket_id} className="group transition hover:bg-slate-50/70">
              <td className="whitespace-nowrap px-5 py-4 font-mono text-xs font-semibold text-medical-800">{ticket.ticket_id}</td>
              <td className="max-w-[180px] px-4 py-4"><p className="truncate text-xs font-semibold text-slate-800">{ticket.customer_name || 'Patient'}</p><p className="mt-1 truncate text-[10px] text-slate-400">{ticket.customer_id || ''}</p></td>
              <td className="max-w-[300px] px-4 py-4"><p className="truncate text-xs font-semibold text-slate-800">{ticket.title || 'Support request'}</p><p className="mt-1 truncate text-[10px] text-slate-500">{ticket.description || 'No additional details'}</p></td>
              <td className="px-4 py-4"><PriorityPill ticket={ticket} /></td>
              <td className="whitespace-nowrap px-4 py-4 text-xs text-slate-500">{formatTicketDate(ticket.created_at)}</td>
              <td className="px-4 py-4"><StatusPill status={ticket.status} /></td>
              <td className="px-5 py-4 text-right"><button type="button" onClick={() => onOpen(ticket)} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-[11px] font-semibold text-slate-700 transition hover:border-medical-200 hover:bg-medical-50 hover:text-medical-800">Review <ArrowRight className="h-3 w-3" /></button></td>
            </tr>)}
          </tbody>
        </table>
      </div>
      <div className="border-t border-slate-100 bg-slate-50/60 px-5 py-2.5 text-[10px] text-slate-400">{tickets.length} ticket{tickets.length === 1 ? '' : 's'}</div>
    </div>
  );
}

export const AdminDashboard = () => {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeSection, setActiveSection] = useState('dashboard');
  const [summaryStatus, setSummaryStatus] = useState('');
  const [search, setSearch] = useState('');
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchTickets = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true);
    setError('');
    try {
      const response = await api.get('/api/tickets');
      // The API already excludes clinical tickets for admins; keep a UI guard too.
      const safeTickets = (response.data || []).filter((ticket) => categoryKeyForTicket(ticket) !== null);
      setTickets(safeTickets);
      setSelectedTicket((current) => current ? safeTickets.find((ticket) => ticket.ticket_id === current.ticket_id) || null : null);
      setLastUpdated(new Date());
    } catch (fetchError) {
      setError(fetchError.response?.data?.detail || 'The support queue could not be loaded. Please refresh and try again.');
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTickets();
    const refreshTimer = window.setInterval(() => fetchTickets({ silent: true }), 20000);
    return () => window.clearInterval(refreshTimer);
  }, [fetchTickets]);

  const ticketGroups = useMemo(() => {
    const groups = Object.fromEntries(ADMIN_TICKET_CATEGORIES.map((category) => [category.key, []]));
    tickets.forEach((ticket) => {
      const key = categoryKeyForTicket(ticket);
      if (key && groups[key]) groups[key].push(ticket);
    });
    return groups;
  }, [tickets]);

  const counts = useMemo(() => tickets.reduce((result, ticket) => {
    const status = displayTicketStatus(ticket.status);
    result[status] += 1;
    return result;
  }, { NEW: 0, IN_PROGRESS: 0, RESOLVED: 0, ESCALATED: 0 }), [tickets]);

  const activeCategory = ADMIN_TICKET_CATEGORIES.find((category) => category.key === activeSection);
  const isResolvedView = activeSection === 'resolved';
  const sectionTickets = useMemo(() => {
    let items = activeCategory ? ticketGroups[activeCategory.key] : tickets;
    if (isResolvedView) items = tickets.filter((ticket) => displayTicketStatus(ticket.status) === 'RESOLVED');
    else if (activeSection === 'dashboard' && summaryStatus) items = tickets.filter((ticket) => displayTicketStatus(ticket.status) === summaryStatus);
    else if (activeCategory) items = items.filter((ticket) => displayTicketStatus(ticket.status) !== 'RESOLVED');
    const query = search.trim().toLowerCase();
    if (query) items = items.filter((ticket) => [ticket.ticket_id, ticket.customer_name, ticket.customer_id, ticket.title, ticket.description].some((value) => String(value || '').toLowerCase().includes(query)));
    return [...items].sort((a, b) => new Date(b.updated_at || b.created_at || 0) - new Date(a.updated_at || a.created_at || 0));
  }, [activeCategory, activeSection, isResolvedView, search, summaryStatus, ticketGroups, tickets]);

  const sectionTitle = activeCategory?.label || (isResolvedView ? 'Resolved Tickets' : 'Support Dashboard');
  const sectionDescription = activeCategory
    ? `Review and resolve ${activeCategory.label.toLowerCase()} requests with tools made for this queue.`
    : isResolvedView
      ? 'A record of non-clinical requests that have been completed.'
      : 'A clear view of incoming non-clinical requests across the support team.';

  const searchPlaceholder = activeSection === 'dashboard' ? 'Search tickets by patient, ID, or problem' : `Search ${activeCategory?.shortLabel || 'resolved'} tickets`;

  return (
    <main className="mx-auto w-full max-w-[1600px] px-3 py-5 sm:px-5 lg:px-7 lg:py-7">
      <div className="grid items-start gap-5 lg:grid-cols-[250px_minmax(0,1fr)] xl:gap-7">
        <aside className="rounded-2xl border border-slate-200/80 bg-white p-3 shadow-sm lg:sticky lg:top-5">
          <div className="flex items-center gap-3 px-2 py-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-medical-700 text-white shadow-sm"><ShieldCheck className="h-5 w-5" /></span>
            <div><p className="text-sm font-bold text-slate-900">Care Support</p><p className="mt-0.5 text-[10px] font-medium uppercase tracking-wider text-slate-400">Admin workspace</p></div>
          </div>
          <p className="px-3 pb-2 pt-4 text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400">Workspace</p>
          <nav aria-label="Admin dashboard sections" className="grid gap-1">
            {SECTIONS.map((section) => {
              const Icon = section.icon;
              const active = activeSection === section.key;
              const count = section.key === 'resolved'
                ? counts.RESOLVED
                : section.key === 'dashboard'
                  ? null
                  : ticketGroups[section.key]?.filter((ticket) => displayTicketStatus(ticket.status) !== 'RESOLVED').length;
              return <button key={section.key} type="button" onClick={() => { setActiveSection(section.key); setSearch(''); }} aria-current={active ? 'page' : undefined} className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-xs font-semibold transition ${active ? 'bg-medical-50 text-medical-800' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'}`}>
                <Icon className={`h-4 w-4 shrink-0 ${active ? 'text-medical-700' : 'text-slate-400'}`} /><span className="min-w-0 flex-1 truncate">{section.label}</span>{count !== null && count !== undefined && <span className={`rounded-full px-2 py-0.5 text-[10px] ${active ? 'bg-white text-medical-800' : 'bg-slate-100 text-slate-500'}`}>{count}</span>}
              </button>;
            })}
          </nav>
          <div className="mt-5 rounded-xl bg-slate-50 p-3"><div className="flex items-center gap-2 text-[10px] font-semibold text-slate-600"><Clock3 className="h-3.5 w-3.5 text-slate-400" />Queue refreshes automatically</div><p className="mt-1.5 pl-5 text-[10px] text-slate-400">{lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString()}` : 'Waiting for queue data'}</p></div>
        </aside>

        <section className="min-w-0 space-y-5">
          <header className="relative isolate flex flex-wrap items-end justify-between gap-4 overflow-hidden rounded-[28px] bg-gradient-to-br from-[#102d4b] via-medical-800 to-teal-700 p-5 text-white shadow-lg shadow-medical-900/10 sm:p-7">
            <div aria-hidden="true" className="absolute -right-10 -top-24 h-64 w-64 rounded-full border-[36px] border-white/5" />
            <div className="relative max-w-2xl"><p className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.16em] text-teal-100"><ShieldCheck className="h-3.5 w-3.5" />Support operations</p><h1 className="mt-4 text-2xl font-bold tracking-tight sm:text-3xl">{sectionTitle}</h1><p className="mt-2 text-xs leading-5 text-white/70 sm:text-sm">{sectionDescription}</p></div>
            <button type="button" onClick={() => fetchTickets()} disabled={loading} className="relative inline-flex items-center gap-2 rounded-xl border border-white/20 bg-white/10 px-3.5 py-2.5 text-xs font-semibold text-white transition hover:bg-white/20 disabled:opacity-60"><RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />Refresh queue</button>
          </header>

          <section aria-label="Ticket summary" className="grid grid-cols-2 gap-3 xl:grid-cols-4">
            <SummaryCard label="New tickets" count={counts.NEW} icon={CircleAlert} tone="bg-blue-50 text-blue-700" accent="border-t-blue-500" onClick={() => { setActiveSection('dashboard'); setSummaryStatus('NEW'); setSearch(''); }} />
            <SummaryCard label="In progress" count={counts.IN_PROGRESS} icon={Clock3} tone="bg-amber-50 text-amber-700" accent="border-t-amber-500" onClick={() => { setActiveSection('dashboard'); setSummaryStatus('IN_PROGRESS'); setSearch(''); }} />
            <SummaryCard label="Resolved" count={counts.RESOLVED} icon={BadgeCheck} tone="bg-emerald-50 text-emerald-700" accent="border-t-emerald-500" onClick={() => { setSummaryStatus(''); setActiveSection('resolved'); setSearch(''); }} />
            <SummaryCard label="Escalated" count={counts.ESCALATED} icon={CircleAlert} tone="bg-rose-50 text-rose-700" accent="border-t-rose-500" onClick={() => { setActiveSection('dashboard'); setSummaryStatus('ESCALATED'); setSearch(''); }} />
          </section>

          {activeSection === 'dashboard' && <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {ADMIN_TICKET_CATEGORIES.map((category) => {
              const Icon = SECTIONS.find((section) => section.key === category.key)?.icon || LifeBuoy;
              const items = ticketGroups[category.key] || [];
              const pending = items.filter((ticket) => displayTicketStatus(ticket.status) !== 'RESOLVED').length;
              return <button key={category.key} type="button" onClick={() => { setActiveSection(category.key); setSummaryStatus(''); setSearch(''); }} className="group rounded-2xl border border-slate-200/80 bg-gradient-to-br from-white to-medical-50/40 p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-medical-200 hover:shadow-md">
                <div className="flex items-start justify-between gap-3"><span className="grid h-11 w-11 place-items-center rounded-2xl bg-medical-50 text-medical-700 transition group-hover:bg-medical-700 group-hover:text-white"><Icon className="h-5 w-5" /></span><span className="rounded-full bg-white px-2.5 py-1 text-[10px] font-semibold text-slate-500 shadow-sm">{items.length} total</span></div>
                <h2 className="mt-4 text-sm font-bold text-slate-900">{category.label}</h2>
                <p className="mt-1 text-xs text-slate-500">{pending} pending ticket{pending === 1 ? '' : 's'} to review</p>
                <span className="mt-4 inline-flex items-center gap-1.5 text-[11px] font-semibold text-medical-700">Open queue <ArrowRight className="h-3 w-3 transition group-hover:translate-x-0.5" /></span>
              </button>;
            })}
          </section>}

          <section className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div><h2 className="text-sm font-bold text-slate-900">{activeSection === 'dashboard' ? 'Recent non-clinical tickets' : isResolvedView ? 'Completed requests' : 'Pending tickets'}</h2><p className="mt-1 text-[10px] text-slate-500">{activeSection === 'dashboard' ? 'All five support queues · clinical cases remain with the doctor team' : sectionDescription}</p></div>
              <label className="relative w-full sm:w-72"><Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder={searchPlaceholder} className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-9 pr-3 text-xs outline-none transition placeholder:text-slate-400 focus:border-medical-400 focus:ring-2 focus:ring-medical-100" /></label>
            </div>
            {error && <div role="alert" className="flex items-start justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800"><span>{error}</span><button onClick={() => fetchTickets()} className="font-bold underline">Retry</button></div>}
            {loading ? <div className="grid place-items-center rounded-2xl border border-slate-200 bg-white py-16 text-xs text-slate-500"><RefreshCw className="mb-3 h-5 w-5 animate-spin text-medical-600" />Loading support queue…</div> : <TicketTable tickets={activeSection === 'dashboard' ? sectionTickets.slice(0, 8) : sectionTickets} onOpen={setSelectedTicket} emptyMessage={isResolvedView ? 'Resolved non-clinical tickets will appear here.' : activeCategory ? 'This category has no pending tickets. Resolved items are available in Resolved Tickets.' : 'New patient requests will appear here as they arrive.'} />}
          </section>
        </section>
      </div>

      {selectedTicket && <AdminTicketResolutionPanel ticket={selectedTicket} onClose={() => setSelectedTicket(null)} onUpdated={() => fetchTickets({ silent: true })} />}
    </main>
  );
};
