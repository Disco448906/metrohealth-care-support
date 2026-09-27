import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight, CalendarDays, ChevronDown, Download, FileText, MessageCircle,
  Pill, ReceiptText, RefreshCw, Search,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { AppointmentManager } from '../components/AppointmentManager';
import api from '../services/api';
import { downloadPatientDocument } from '../services/documentExport';

const DocumentField = ({ label, value }) => value ? <p className="text-sm"><span className="font-medium text-slate-500">{label}:</span> <span className="whitespace-pre-line text-slate-700">{value}</span></p> : null;
const DownloadButton = ({ type, record }) => <button type="button" onClick={() => downloadPatientDocument(type, record)} className="inline-flex items-center gap-1.5 rounded-lg border border-medical-200 px-2.5 py-1.5 text-xs font-semibold text-medical-700 hover:bg-medical-50"><Download className="h-3.5 w-3.5" />Download PDF</button>;
const getBillLines = (bill) => {
  try {
    const lines = typeof bill.line_items === 'string' ? JSON.parse(bill.line_items) : bill.line_items;
    return Array.isArray(lines) && lines.length ? lines : [{ description: bill.description || 'Hospital service', quantity: 1, total: bill.amount }];
  } catch { return [{ description: bill.description || 'Hospital service', quantity: 1, total: bill.amount }]; }
};

const formatDate = (value) => {
  if (!value) return 'Date not listed';
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
};

const statusClasses = {
  CONFIRMED: 'bg-emerald-50 text-emerald-700', RESCHEDULED: 'bg-sky-50 text-sky-700',
  COMPLETED: 'bg-slate-100 text-slate-600', CANCELLED: 'bg-rose-50 text-rose-700',
  PAID: 'bg-emerald-50 text-emerald-700', UNPAID: 'bg-amber-50 text-amber-800',
  PENDING: 'bg-amber-50 text-amber-800', OVERDUE: 'bg-rose-50 text-rose-700',
  OPEN: 'bg-amber-50 text-amber-800', ASSIGNED: 'bg-violet-50 text-violet-700',
  IN_PROGRESS: 'bg-sky-50 text-sky-700', RESOLVED: 'bg-emerald-50 text-emerald-700',
  CLOSED: 'bg-slate-100 text-slate-600',
};

const StatusPill = ({ value }) => (
  <span className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ${statusClasses[value] || 'bg-slate-100 text-slate-600'}`}>
    {(value || 'UNAVAILABLE').replaceAll('_', ' ')}
  </span>
);

function SectionCard({ title, subtitle, icon: Icon, children, count, action }) {
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-medical-50 text-medical-700"><Icon className="h-5 w-5" /></span>
          <div className="min-w-0">
            <h2 className="font-bold text-slate-900">{title}{count != null && <span className="ml-2 text-xs font-medium text-slate-400">{count}</span>}</h2>
            <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>
          </div>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

const EmptyState = ({ children }) => <p className="px-5 py-8 text-center text-sm text-slate-500">{children}</p>;

const matchesSearch = (item, query) => Object.values(item || {}).some((value) => String(value ?? '').toLowerCase().includes(query));

export const CustomerDashboard = () => {
  const { user } = useAuth();
  const [appointments, setAppointments] = useState([]);
  const [records, setRecords] = useState({ reports: [], medicines: [], bills: [] });
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [error, setError] = useState('');
  const [recordSearch, setRecordSearch] = useState('');
  const [ticketFilter, setTicketFilter] = useState('ALL');
  const [expandedTicket, setExpandedTicket] = useState('');
  const [activePanel, setActivePanel] = useState('visits');

  const fetchData = useCallback(async ({ silent = false } = {}) => {
    if (!silent) {
      setLoading(true);
      setError('');
    }
    try {
      const [appointmentResponse, recordsResponse, ticketResponse] = await Promise.all([
        api.get('/api/appointments'), api.get('/api/records/mine'), api.get('/api/tickets'),
      ]);
      setAppointments(appointmentResponse.data || []);
      setRecords({ reports: [], medicines: [], bills: [], ...recordsResponse.data });
      setTickets(ticketResponse.data || []);
      setLastUpdated(new Date());
    } catch (err) {
      if (!silent) setError(err.response?.data?.detail || 'We could not load your account details. Please refresh to try again.');
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const refreshTimer = window.setInterval(() => fetchData({ silent: true }), 15000);
    return () => window.clearInterval(refreshTimer);
  }, [fetchData]);

  const search = recordSearch.trim().toLowerCase();
  const filteredRecords = useMemo(() => ({
    reports: records.reports.filter((item) => matchesSearch(item, search)),
    medicines: records.medicines.filter((item) => matchesSearch(item, search)),
    bills: records.bills.filter((item) => matchesSearch(item, search)),
  }), [records, search]);
  const filteredTickets = tickets.filter((ticket) => {
    if (ticketFilter === 'ALL') return true;
    if (ticketFilter === 'OPEN') return ['OPEN', 'ASSIGNED', 'IN_PROGRESS'].includes(ticket.status);
    if (ticketFilter === 'RESOLVED') return ['RESOLVED', 'CLOSED'].includes(ticket.status);
    return ticket.status === ticketFilter;
  });
  const unpaidBills = records.bills.filter((item) => !['PAID', 'CANCELLED'].includes((item.status || 'UNPAID').toUpperCase()));
  const amountDue = unpaidBills.reduce((sum, bill) => sum + (Number(bill.amount) || 0), 0);

  return (
    <main className="mx-auto max-w-7xl space-y-5 px-4 py-6 sm:px-6 lg:px-8">
      <section className="relative isolate overflow-hidden rounded-[28px] bg-gradient-to-br from-[#0b3447] via-medical-800 to-teal-600 p-6 text-white shadow-lg shadow-medical-900/10 sm:p-8">
        <div aria-hidden="true" className="absolute -right-14 -top-24 h-64 w-64 rounded-full border-[36px] border-white/5" />
        <div aria-hidden="true" className="absolute bottom-[-5rem] right-1/4 h-44 w-44 rounded-full bg-teal-300/10 blur-2xl" />
        <div className="relative flex flex-wrap items-end justify-between gap-5">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.18em] text-teal-100">Patient portal</span>
            <h1 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">Good to see you, {user?.name?.split(' ')[0] || 'there'}</h1>
            <p className="mt-2 max-w-xl text-sm text-white/75">Keep your appointments, health records, and support requests in one place.</p>
            <p className="mt-4 text-[11px] text-white/55">Updates every 15 seconds{lastUpdated ? ` · Last updated ${lastUpdated.toLocaleTimeString()}` : ''}</p>
          </div>
          <div className="flex gap-2">
            <Link to="/chat" className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-3 text-sm font-semibold text-medical-900 shadow-sm transition hover:bg-teal-50"><MessageCircle className="h-4 w-4" />Ask for help<ArrowRight className="h-4 w-4" /></Link>
            <button onClick={fetchData} disabled={loading} aria-label="Refresh account" className="rounded-xl border border-white/25 bg-white/10 p-3 transition hover:bg-white/20 disabled:opacity-60"><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /></button>
          </div>
        </div>
      </section>

      {error && <div role="alert" className="flex items-center justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"><span>{error}</span><button onClick={fetchData} className="font-semibold underline underline-offset-2">Try again</button></div>}

      <nav className="grid grid-cols-3 gap-2 rounded-2xl border border-slate-200/80 bg-white p-2 shadow-sm" aria-label="My care sections">
        {[
          ['visits', 'Appointments', CalendarDays],
          ['records', 'Records & bills', FileText],
          ['requests', 'Support requests', MessageCircle],
        ].map(([key, label, Icon]) => <button key={key} onClick={() => setActivePanel(key)} aria-current={activePanel === key ? 'page' : undefined} className={`flex items-center justify-center gap-2 rounded-xl px-2 py-3 text-xs font-semibold transition sm:text-sm ${activePanel === key ? 'bg-medical-800 text-white shadow-md shadow-medical-900/15' : 'text-slate-600 hover:bg-slate-50 hover:text-medical-800'}`}><Icon className="h-4 w-4" />{label}</button>)}
      </nav>

      {activePanel === 'visits' && <AppointmentManager appointments={appointments} loading={loading} onRefresh={fetchData} />}

      {activePanel === 'records' && <div className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div><h2 className="text-lg font-bold text-slate-900">Records and bills</h2><p className="mt-1 text-sm text-slate-500">Items shared by your doctor or hospital team.</p></div>
          <label className="relative block w-full sm:max-w-sm"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" /><input value={recordSearch} onChange={(event) => setRecordSearch(event.target.value)} type="search" placeholder="Search records and bills" className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-9 pr-3 text-sm shadow-sm outline-none focus:border-medical-400 focus:ring-2 focus:ring-medical-100" /></label>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <SectionCard title="Health reports" subtitle="Shared by your doctor" icon={FileText} count={filteredRecords.reports.length}>
            {loading ? <EmptyState>Loading reports…</EmptyState> : filteredRecords.reports.length === 0 ? <EmptyState>{search ? 'No reports match your search.' : 'Reports will appear here when your doctor adds them.'}</EmptyState> : <div className="divide-y divide-slate-100">{filteredRecords.reports.map((item, index) => <article key={item.record_id || item.id || `${item.title}-${index}`} className="px-5 py-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-semibold text-slate-900">{item.title || item.name || 'Health report'}{String(item.record_id || item.id || '').startsWith('demo_') && <span className="ml-2 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-800">Demo</span>}</p><p className="mt-1 text-xs text-slate-500">{item.report_date ? formatDate(item.report_date) : item.created_at ? new Date(item.created_at).toLocaleDateString() : 'Date not listed'}{item.doctor_name ? ` · ${item.doctor_name}` : ''}</p></div><DownloadButton type="report" record={item} /></div><div className="mt-3 space-y-2 rounded-xl bg-slate-50 p-3"><DocumentField label="Report type" value={item.report_type}/><DocumentField label="Clinical indication" value={item.indication}/><DocumentField label="Findings" value={item.findings || item.details || item.summary}/><DocumentField label="Clinical impression" value={item.impression}/><DocumentField label="Recommendations / follow-up" value={item.recommendations}/></div></article>)}</div>}
          </SectionCard>
          <SectionCard title="Prescriptions" subtitle="Instructions recorded by your doctor" icon={Pill} count={filteredRecords.medicines.length}>
            {loading ? <EmptyState>Loading prescriptions…</EmptyState> : filteredRecords.medicines.length === 0 ? <EmptyState>{search ? 'No prescriptions match your search.' : 'Prescriptions will appear here when your doctor adds them.'}</EmptyState> : <div className="divide-y divide-slate-100">{filteredRecords.medicines.map((item, index) => <article key={item.record_id || item.id || `${item.title}-${index}`} className="px-5 py-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-semibold text-slate-900">{item.medicine || item.title || item.name || 'Prescription'}{String(item.record_id || item.id || '').startsWith('demo_') && <span className="ml-2 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-800">Demo</span>}</p><p className="mt-1 text-xs text-slate-500">Prescribed by {item.doctor_name || 'Your doctor'} · {item.issued_date || (item.created_at || '').slice(0, 10) || 'Date not listed'}</p></div><DownloadButton type="prescription" record={item} /></div><div className="mt-3 grid gap-2 rounded-xl bg-slate-50 p-3 sm:grid-cols-2"><DocumentField label="Diagnosis / indication" value={item.diagnosis}/><DocumentField label="Strength" value={item.strength}/><DocumentField label="Dose" value={item.dosage}/><DocumentField label="Route" value={item.route}/><DocumentField label="Frequency" value={item.frequency}/><DocumentField label="Duration" value={item.duration}/><DocumentField label="Quantity" value={item.quantity}/><DocumentField label="Refills" value={item.refills}/><div className="sm:col-span-2"><DocumentField label="Instructions" value={item.instructions || item.details}/></div></div></article>)}</div>}
          </SectionCard>
          <SectionCard title="Bills" subtitle={amountDue ? `₹${amountDue.toLocaleString()} due` : 'Managed by the hospital team'} icon={ReceiptText} count={filteredRecords.bills.length}>
            {loading ? <EmptyState>Loading bills…</EmptyState> : filteredRecords.bills.length === 0 ? <EmptyState>{search ? 'No bills match your search.' : 'Bills will appear here when they are added.'}</EmptyState> : <div className="divide-y divide-slate-100">{filteredRecords.bills.map((item, index) => <article key={item.bill_id || item.id || index} className="px-5 py-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-semibold text-slate-900">{item.description || item.title || 'Hospital bill'}{String(item.bill_id || item.id || '').startsWith('demo_') && <span className="ml-2 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-800">Demo</span>}</p><p className="mt-1 text-xs text-slate-500">Bill {item.bill_id || 'Billing record'} · Service date {item.service_date || (item.created_at || '').slice(0, 10) || 'Not listed'}</p></div><div className="flex items-center gap-3"><span className="font-bold text-slate-900">{item.currency || '₹'}{Number(item.amount ?? 0).toLocaleString()}</span><StatusPill value={(item.status || 'UNPAID').toUpperCase()} /><DownloadButton type="bill" record={item} /></div></div><div className="mt-3 space-y-2 rounded-xl bg-slate-50 p-3"><p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Itemized charges</p>{getBillLines(item).map((line, lineIndex) => <div key={lineIndex} className="flex justify-between gap-3 text-sm"><span className="text-slate-700">{line.description || 'Hospital service'} <span className="text-xs text-slate-500">× {line.quantity ?? 1}</span></span><span className="shrink-0 font-medium">{item.currency || '₹'}{Number(line.total ?? line.unit_price ?? 0).toLocaleString()}</span></div>)}<div className="grid gap-1 border-t border-slate-200 pt-2 sm:grid-cols-2"><DocumentField label="Provider" value={item.provider_name}/><DocumentField label="Due date" value={item.due_date}/><DocumentField label="Subtotal" value={`${item.currency || '₹'}${Number(item.subtotal ?? item.amount ?? 0).toLocaleString()}`}/><DocumentField label="Tax" value={`${item.currency || '₹'}${Number(item.tax || 0).toLocaleString()}`}/><DocumentField label="Payment method" value={item.payment_method}/></div></div></article>)}</div>}
          </SectionCard>
        </div>
      </div>}

      {activePanel === 'requests' && <SectionCard title="Support requests" subtitle="Select a request to see what the team has done." icon={MessageCircle} count={tickets.length}>
        {tickets.length > 0 && <div className="flex gap-2 px-5 pt-4">{[['ALL', 'All'], ['OPEN', 'Open'], ['RESOLVED', 'Resolved']].map(([value, label]) => <button key={value} onClick={() => setTicketFilter(value)} className={`rounded-full px-3 py-1.5 text-xs font-semibold ${ticketFilter === value ? 'bg-medical-700 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>{label}</button>)}</div>}
        {loading ? <EmptyState>Loading support requests…</EmptyState> : tickets.length === 0 ? <div className="px-5 py-8 text-center"><p className="text-sm text-slate-500">No support requests yet.</p><Link to="/chat" className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-medical-700">Ask for help<ArrowRight className="h-3.5 w-3.5" /></Link></div> : filteredTickets.length === 0 ? <EmptyState>No requests in this group.</EmptyState> : <div className="divide-y divide-slate-100">{filteredTickets.map((ticket) => {
          const expanded = expandedTicket === ticket.ticket_id;
          return <article key={ticket.ticket_id} className="px-5 py-4"><button onClick={() => setExpandedTicket(expanded ? '' : ticket.ticket_id)} aria-expanded={expanded} className="flex w-full items-start justify-between gap-3 text-left"><div className="min-w-0"><p className="truncate font-semibold text-slate-900">{ticket.title || 'Support request'}</p><p className="mt-1 text-xs text-slate-500">{ticket.ticket_id} · {ticket.department || 'Customer support'}</p></div><span className="flex shrink-0 items-center gap-2"><StatusPill value={ticket.status} /><ChevronDown className={`h-4 w-4 text-slate-400 transition ${expanded ? 'rotate-180' : ''}`} /></span></button>
            {expanded && <div className="mt-3 space-y-3 rounded-xl bg-slate-50 p-4 text-sm"><p className="whitespace-pre-line text-slate-700">{ticket.description || 'Request details are not available.'}</p>{ticket.assigned_staff && ticket.assigned_staff !== 'Unassigned' && <p className="text-xs text-slate-500">Assigned to {ticket.assigned_staff}</p>}{Array.isArray(ticket.activity) && ticket.activity.length > 0 && <ol className="space-y-2 border-t border-slate-200 pt-3">{ticket.activity.slice(-5).reverse().map((item, index) => <li key={`${item.created_at}-${index}`}><p className="text-xs font-semibold text-slate-700">{item.action || item.status?.replaceAll('_', ' ') || 'Update'}</p><p className="text-xs text-slate-500">{item.created_at ? new Date(item.created_at).toLocaleString() : ''}{item.note ? ` · ${item.note}` : ''}</p></li>)}</ol>}{ticket.resolution_notes && <p className="border-t border-slate-200 pt-2 text-sm text-emerald-800">{ticket.resolution_notes}</p>}</div>}
          </article>;
        })}</div>}
      </SectionCard>}
    </main>
  );
};
