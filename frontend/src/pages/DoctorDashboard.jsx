import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { CalendarDays, ClipboardList, Clock3, FileText, MapPin, Pencil, Pill, RefreshCw, Save, ShieldAlert, Stethoscope, UserRound, X } from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';

const prettyDate = (value) => {
  if (!value) return 'Date not set';
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
};

const statusStyle = {
  CONFIRMED: 'bg-emerald-100 text-emerald-800',
  RESCHEDULED: 'bg-indigo-100 text-indigo-800',
  COMPLETED: 'bg-slate-100 text-slate-700',
  CANCELLED: 'bg-rose-100 text-rose-800',
};

const EMPTY_RECORD_DRAFT = { patient_id: '', type: 'report', title: '', report_type: 'Clinical report', indication: '', findings: '', impression: '', recommendations: '', report_date: '', medicine: '', strength: '', dosage: '', route: '', frequency: '', duration: '', quantity: '', refills: '0', diagnosis: '', instructions: '', issued_date: '' };

export const DoctorDashboard = () => {
  const { user } = useAuth();
  const [appointments, setAppointments] = useState([]);
  const [clinicalRecords, setClinicalRecords] = useState({ reports: [], medicines: [] });
  const [clinicalTickets, setClinicalTickets] = useState([]);
  const [recordDraft, setRecordDraft] = useState(EMPTY_RECORD_DRAFT);
  const [editingRecord, setEditingRecord] = useState(null);
  const [recordSaving, setRecordSaving] = useState(false);
  const [recordNotice, setRecordNotice] = useState('');
  const [ticketReplies, setTicketReplies] = useState({});
  const [ticketFeedback, setTicketFeedback] = useState({});
  const [savingTicket, setSavingTicket] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState(null);
  const [activePanel, setActivePanel] = useState('schedule');

  const loadSchedule = useCallback(async ({ silent = false } = {}) => {
    if (!silent) {
      setLoading(true);
      setError('');
    }
    try {
      const [response, records, tickets] = await Promise.all([
        api.get('/api/appointments/doctor/schedule'),
        api.get('/api/records/doctor/patients'),
        api.get('/api/tickets/doctor/queue')
      ]);
      setAppointments(response.data);
      setClinicalRecords({ reports: [], medicines: [], ...records.data });
      setClinicalTickets(tickets.data);
      setLastUpdated(new Date());
    } catch (err) {
      if (!silent) setError(err.response?.data?.detail || 'Could not load your appointment schedule.');
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSchedule();
    const refreshTimer = window.setInterval(() => loadSchedule({ silent: true }), 15000);
    return () => window.clearInterval(refreshTimer);
  }, [loadSchedule]);

  const assignedPatients = useMemo(() => [...new Map(
    appointments
      .filter((appointment) => appointment.customer_id || appointment.patient_id)
      .map((appointment) => [appointment.customer_id || appointment.patient_id, appointment])
  ).values()], [appointments]);
  const patientRecords = useMemo(() => [
    ...clinicalRecords.reports.map((item) => ({ ...item, recordType: 'report' })),
    ...clinicalRecords.medicines.map((item) => ({ ...item, recordType: 'medicine' })),
  ].sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || ''))), [clinicalRecords]);
  const openConcernCount = clinicalTickets.filter((ticket) => !['RESOLVED', 'CLOSED'].includes(ticket.status)).length;

  const resetRecordForm = () => {
    setRecordDraft(EMPTY_RECORD_DRAFT);
    setEditingRecord(null);
    setRecordNotice('');
  };

  const beginRecordEdit = (item) => {
    setEditingRecord({ record_id: item.record_id, patient_id: item.patient_id });
    setRecordDraft({
      patient_id: item.patient_id,
      type: item.recordType,
      title: item.recordType === 'report' ? item.title || '' : '',
      report_type: item.report_type || 'Clinical report',
      indication: item.indication || '',
      findings: item.recordType === 'report' ? item.findings || item.details || '' : '',
      impression: item.impression || '',
      recommendations: item.recommendations || '',
      report_date: item.report_date || '',
      medicine: item.recordType === 'medicine' ? item.medicine || item.title || '' : '',
      strength: item.strength || '',
      dosage: item.dosage || '',
      route: item.route || '',
      frequency: item.frequency || '',
      duration: item.duration || '',
      quantity: item.quantity || '',
      refills: item.refills ?? '0',
      diagnosis: item.diagnosis || '',
      instructions: item.instructions || item.details || '',
      issued_date: item.issued_date || '',
    });
    setRecordNotice('');
  };

  const saveRecord = async (event) => {
    event.preventDefault();
    setRecordSaving(true);
    setRecordNotice('');
    try {
      const patient = appointments.find((appointment) => (appointment.customer_id || appointment.patient_id) === recordDraft.patient_id);
      const payload = recordDraft.type === 'report'
        ? { type: 'report', title: recordDraft.title, report_type: recordDraft.report_type, indication: recordDraft.indication, findings: recordDraft.findings, details: recordDraft.findings, impression: recordDraft.impression, recommendations: recordDraft.recommendations, report_date: recordDraft.report_date, patient_name: patient?.patient_name || patient?.customer_name || '' }
        : { type: 'medicine', title: recordDraft.medicine, medicine: recordDraft.medicine, diagnosis: recordDraft.diagnosis, strength: recordDraft.strength, dosage: recordDraft.dosage, route: recordDraft.route, frequency: recordDraft.frequency, duration: recordDraft.duration, quantity: recordDraft.quantity, refills: recordDraft.refills, instructions: recordDraft.instructions, details: recordDraft.instructions, issued_date: recordDraft.issued_date, patient_name: patient?.patient_name || patient?.customer_name || '' };
      if (editingRecord) {
        await api.put(`/api/records/doctor/${encodeURIComponent(editingRecord.patient_id)}/${encodeURIComponent(editingRecord.record_id)}`, payload);
      } else {
        await api.post(`/api/records/doctor/${encodeURIComponent(recordDraft.patient_id)}`, payload);
      }
      setRecordNotice(editingRecord ? 'Patient record updated.' : 'Record saved to the patient portal.');
      setRecordDraft(EMPTY_RECORD_DRAFT);
      setEditingRecord(null);
      await loadSchedule();
    } catch (err) {
      setRecordNotice(err.response?.data?.detail || 'The record could not be saved. Please try again.');
    } finally {
      setRecordSaving(false);
    }
  };

  return (
    <main className="mx-auto max-w-7xl space-y-5 px-4 py-6 sm:px-6 lg:px-8">
      <section className="relative isolate overflow-hidden rounded-[28px] bg-gradient-to-br from-[#102d4b] via-medical-800 to-cyan-700 p-6 text-white shadow-lg shadow-sky-950/10 sm:p-8">
        <div aria-hidden="true" className="absolute -right-10 -top-20 h-56 w-56 rounded-full border-[34px] border-white/5" />
        <div aria-hidden="true" className="absolute bottom-[-6rem] right-1/3 h-48 w-48 rounded-full bg-cyan-300/10 blur-2xl" />
        <div className="relative flex flex-wrap items-end justify-between gap-5">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.18em] text-cyan-100"><Stethoscope className="h-3.5 w-3.5" />Care team</span>
            <h1 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">Welcome, {user?.name || 'Doctor'}</h1>
            <p className="mt-2 text-sm text-white/75">Your schedule, assigned patients, and care follow-ups.</p>
            <p className="mt-4 text-[11px] text-white/55">Updates every 15 seconds{lastUpdated ? ` · Last updated ${lastUpdated.toLocaleTimeString()}` : ''}</p>
          </div>
          <button onClick={loadSchedule} disabled={loading} className="inline-flex items-center gap-2 rounded-xl border border-white/20 bg-white/10 px-4 py-3 text-sm font-semibold transition hover:bg-white/20 disabled:opacity-60">
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>
      </section>

      <nav className="grid grid-cols-2 gap-2 rounded-2xl border border-slate-200/80 bg-white p-2 shadow-sm" aria-label="Doctor workspace sections">
        {[
          ['schedule', 'Appointments', CalendarDays],
          ['patients', 'Patients & concerns', ClipboardList],
        ].map(([key, label, Icon]) => <button key={key} onClick={() => setActivePanel(key)} aria-current={activePanel === key ? 'page' : undefined} className={`flex items-center justify-center gap-2 rounded-xl px-3 py-3 text-sm font-semibold transition ${activePanel === key ? 'bg-medical-800 text-white shadow-md shadow-medical-900/15' : 'text-slate-600 hover:bg-slate-50 hover:text-medical-800'}`}><Icon className="h-4 w-4" />{label}</button>)}
      </nav>

      {activePanel === 'patients' && <section className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center gap-3 border-b border-slate-100 px-5 py-4">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-violet-50 text-violet-700"><FileText className="h-5 w-5" /></span>
            <div className="min-w-0 flex-1"><h2 className="font-bold text-slate-900">Patient records</h2>
            <p className="mt-1 text-xs leading-5 text-slate-500">Review records for patients assigned to your account. Add or edit an entry to update the patient portal.</p>
            </div><span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">{patientRecords.length}</span>
          </div>

          <form className="m-4 grid gap-3 rounded-2xl border border-medical-100 bg-gradient-to-br from-medical-50/80 to-white p-4 shadow-sm sm:grid-cols-2" onSubmit={saveRecord}>
            <div className="sm:col-span-2 flex items-center justify-between gap-3">
              <h3 className="text-sm font-semibold text-slate-800">{editingRecord ? 'Edit patient record' : 'Add a patient record'}</h3>
              {editingRecord && <button type="button" onClick={resetRecordForm} className="inline-flex items-center gap-1 text-xs font-semibold text-slate-500 hover:text-slate-800"><X className="h-3.5 w-3.5" />Cancel edit</button>}
            </div>
            <select required value={recordDraft.patient_id} disabled={Boolean(editingRecord) || recordSaving} onChange={(event) => setRecordDraft({ ...recordDraft, patient_id: event.target.value })} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm disabled:bg-slate-100">
              <option value="">Select an assigned patient</option>
              {assignedPatients.map((appointment) => {
                const patientId = appointment.customer_id || appointment.patient_id;
                return <option key={patientId} value={patientId}>{appointment.patient_name || appointment.customer_name} · {patientId}</option>;
              })}
            </select>
            <select value={recordDraft.type} disabled={Boolean(editingRecord) || recordSaving} onChange={(event) => setRecordDraft({ ...recordDraft, type: event.target.value })} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm disabled:bg-slate-100"><option value="report">Health report</option><option value="medicine">Prescription / medicine</option></select>
            {recordDraft.type === 'report' ? <>
              <input required value={recordDraft.title} disabled={recordSaving} onChange={(event) => setRecordDraft({ ...recordDraft, title: event.target.value })} placeholder="Report title (e.g. Complete blood count)" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" />
              <input required value={recordDraft.report_type} disabled={recordSaving} onChange={(event) => setRecordDraft({ ...recordDraft, report_type: event.target.value })} placeholder="Report type" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" />
              <input type="date" value={recordDraft.report_date} disabled={recordSaving} onChange={(event) => setRecordDraft({ ...recordDraft, report_date: event.target.value })} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" aria-label="Report date" />
              <textarea value={recordDraft.indication} disabled={recordSaving} onChange={(event) => setRecordDraft({ ...recordDraft, indication: event.target.value })} placeholder="Clinical indication / reason for test" className="min-h-16 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm sm:col-span-2" />
              <textarea required value={recordDraft.findings} disabled={recordSaving} onChange={(event) => setRecordDraft({ ...recordDraft, findings: event.target.value })} placeholder="Findings and measured values (include units and reference ranges when available)" className="min-h-20 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm sm:col-span-2" />
              <textarea value={recordDraft.impression} disabled={recordSaving} onChange={(event) => setRecordDraft({ ...recordDraft, impression: event.target.value })} placeholder="Clinical impression / interpretation" className="min-h-16 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm sm:col-span-2" />
              <textarea value={recordDraft.recommendations} disabled={recordSaving} onChange={(event) => setRecordDraft({ ...recordDraft, recommendations: event.target.value })} placeholder="Recommendations and follow-up" className="min-h-16 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm sm:col-span-2" />
            </> : <>
              <input required value={recordDraft.medicine} disabled={recordSaving} onChange={(event) => setRecordDraft({ ...recordDraft, medicine: event.target.value })} placeholder="Medicine name" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" />
              <input required value={recordDraft.strength} disabled={recordSaving} onChange={(event) => setRecordDraft({ ...recordDraft, strength: event.target.value })} placeholder="Strength (e.g. 250 mg)" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" />
              <input required value={recordDraft.dosage} disabled={recordSaving} onChange={(event) => setRecordDraft({ ...recordDraft, dosage: event.target.value })} placeholder="Dose (e.g. 1 tablet)" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" />
              <input required value={recordDraft.route} disabled={recordSaving} onChange={(event) => setRecordDraft({ ...recordDraft, route: event.target.value })} placeholder="Route (e.g. oral)" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" />
              <input required value={recordDraft.frequency} disabled={recordSaving} onChange={(event) => setRecordDraft({ ...recordDraft, frequency: event.target.value })} placeholder="Frequency (e.g. twice daily)" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" />
              <input required value={recordDraft.duration} disabled={recordSaving} onChange={(event) => setRecordDraft({ ...recordDraft, duration: event.target.value })} placeholder="Duration (e.g. 5 days)" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" />
              <input required value={recordDraft.quantity} disabled={recordSaving} onChange={(event) => setRecordDraft({ ...recordDraft, quantity: event.target.value })} placeholder="Total quantity to dispense" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" />
              <input type="number" min="0" value={recordDraft.refills} disabled={recordSaving} onChange={(event) => setRecordDraft({ ...recordDraft, refills: event.target.value })} placeholder="Refills" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" />
              <input value={recordDraft.diagnosis} disabled={recordSaving} onChange={(event) => setRecordDraft({ ...recordDraft, diagnosis: event.target.value })} placeholder="Diagnosis / indication" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" />
              <input type="date" value={recordDraft.issued_date} disabled={recordSaving} onChange={(event) => setRecordDraft({ ...recordDraft, issued_date: event.target.value })} aria-label="Prescription date" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" />
              <textarea required value={recordDraft.instructions} disabled={recordSaving} onChange={(event) => setRecordDraft({ ...recordDraft, instructions: event.target.value })} placeholder="Patient instructions (timing, food instructions, precautions)" className="min-h-16 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm sm:col-span-2" />
            </>}
            <div className="flex flex-wrap items-center gap-3 sm:col-span-2">
              <button disabled={!recordDraft.patient_id || recordSaving} className="inline-flex items-center gap-2 rounded-lg bg-medical-700 px-4 py-2 text-sm font-semibold text-white hover:bg-medical-800 disabled:opacity-50"><Save className="h-4 w-4" />{recordSaving ? 'Saving…' : editingRecord ? 'Save changes' : 'Add to patient portal'}</button>
              {recordNotice && <p role="status" className="text-xs text-slate-600">{recordNotice}</p>}
            </div>
          </form>

          <div className="max-h-[34rem] space-y-3 overflow-y-auto p-4 pt-0">
            {patientRecords.length === 0 ? <p className="px-5 py-8 text-center text-sm text-slate-500">No records for your assigned patients yet. Add the first report or prescription above.</p> : patientRecords.map((item) => {
              const isReport = item.recordType === 'report';
              const isEditing = editingRecord?.record_id === item.record_id;
              return <article key={item.record_id} className={`rounded-2xl border p-4 transition ${isEditing ? 'border-medical-200 bg-medical-50/60 shadow-sm' : 'border-slate-100 bg-white hover:border-slate-200 hover:bg-slate-50/60'}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 items-start gap-3">
                    <span className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${isReport ? 'bg-sky-50 text-sky-700' : 'bg-violet-50 text-violet-700'}`}>{isReport ? <FileText className="h-4 w-4" /> : <Pill className="h-4 w-4" />}</span>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2"><p className="font-semibold text-slate-900">{item.title || item.medicine || 'Clinical record'}</p><span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600">{isReport ? 'Report' : 'Prescription'}</span>{String(item.record_id).startsWith('demo_') && <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-800">Demo sample</span>}</div>
                      <p className="mt-1 text-xs text-slate-500">{item.patient_name || item.patient_id} · {item.report_date ? prettyDate(item.report_date) : prettyDate((item.created_at || '').slice(0, 10))}</p>
                      {(item.strength || item.dosage || item.route || item.frequency || item.duration || item.quantity) && <p className="mt-2 text-xs font-medium text-medical-800">{[item.strength, item.dosage, item.route, item.frequency, item.duration, item.quantity && `Qty ${item.quantity}`].filter(Boolean).join(' · ')}</p>}
                      {(item.findings || item.impression || item.recommendations || item.instructions || item.details) && <p className="mt-2 whitespace-pre-line text-sm leading-5 text-slate-600">{[item.findings || item.details, item.impression && `Impression: ${item.impression}`, item.recommendations && `Follow-up: ${item.recommendations}`, item.instructions && `Instructions: ${item.instructions}`].filter(Boolean).join('\n')}</p>}
                    </div>
                  </div>
                  <button type="button" onClick={() => isEditing ? resetRecordForm() : beginRecordEdit(item)} className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-xs font-semibold text-slate-600 hover:border-medical-300 hover:text-medical-700"><Pencil className="h-3.5 w-3.5" />{isEditing ? 'Editing' : 'Edit'}</button>
                </div>
              </article>;
            })}
          </div>
        </div>
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center gap-3 border-b border-slate-100 px-5 py-4"><span className="grid h-10 w-10 place-items-center rounded-xl bg-rose-50 text-rose-700"><ShieldAlert className="h-5 w-5" /></span><div><h2 className="font-bold text-slate-900">Medical concerns</h2><p className="mt-0.5 text-xs text-slate-500">Cases that need your review</p></div><span className="ml-auto rounded-full bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-700">{openConcernCount} open</span></div>
          <div className="space-y-3 p-4">
          {clinicalTickets.length === 0 ? <p className="rounded-xl bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">No medical concerns are waiting for review.</p> : clinicalTickets.map((ticket) => (
            <article key={ticket.ticket_id} className="rounded-2xl border border-rose-100 bg-gradient-to-br from-rose-50/60 to-white p-4">
              <div className="flex items-start justify-between gap-3"><p className="font-semibold text-slate-900">{ticket.title}</p><span className="shrink-0 rounded-full bg-rose-100 px-2 py-1 text-[10px] font-bold uppercase text-rose-800">{ticket.severity || 'Review'}</span></div>
              <p className="mt-1 text-sm font-medium text-slate-700"><span className="text-slate-500">Patient:</span> {ticket.customer_name || 'Name unavailable'}</p>
              <p className="text-xs text-slate-500">Ticket: {ticket.ticket_id}</p>
              <p className="mt-1 text-sm text-slate-700">{ticket.description}</p>
              <div className="mt-2 flex items-center gap-3">
                <span className="text-xs text-slate-500">{ticket.status}</span>
              </div>
              {ticket.status !== 'RESOLVED' && ticket.status !== 'CLOSED' && <form className="mt-2 flex flex-col sm:flex-row gap-2" onSubmit={async (event) => {
                event.preventDefault();
                const reply = ticketReplies[ticket.ticket_id]?.trim();
                if (!reply) return;
                setSavingTicket(ticket.ticket_id);
                setTicketFeedback({ ...ticketFeedback, [ticket.ticket_id]: '' });
                try {
                  await api.put(`/api/tickets/${ticket.ticket_id}/status`, { status: 'RESOLVED', resolution_notes: reply });
                  setTicketReplies({ ...ticketReplies, [ticket.ticket_id]: '' });
                  setTicketFeedback({ ...ticketFeedback, [ticket.ticket_id]: 'Response saved and request marked resolved.' });
                  await loadSchedule({ silent: true });
                } catch (err) {
                  setTicketFeedback({ ...ticketFeedback, [ticket.ticket_id]: err.response?.data?.detail || 'The response could not be saved. Please try again.' });
                } finally {
                  setSavingTicket('');
                }
              }}>
                <textarea required value={ticketReplies[ticket.ticket_id] || ''} onChange={(e) => setTicketReplies({ ...ticketReplies, [ticket.ticket_id]: e.target.value })} placeholder="Write a response for the patient…" className="flex-1 min-h-16 rounded-lg border border-slate-200 px-3 py-2 text-xs" />
                <button disabled={savingTicket === ticket.ticket_id} className="self-end rounded-lg bg-medical-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">{savingTicket === ticket.ticket_id ? 'Saving…' : 'Send response & resolve'}</button>
              </form>}
              {ticketFeedback[ticket.ticket_id] && <p role="status" className="mt-2 text-xs text-slate-600">{ticketFeedback[ticket.ticket_id]}</p>}
              {ticket.resolution_notes && <p className="mt-1 text-xs text-emerald-700">Doctor response: {ticket.resolution_notes}</p>}
            </article>
          ))}
          </div>
        </div>
      </section>}

      {activePanel === 'schedule' && <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center gap-3 border-b border-slate-100 px-5 py-4">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-sky-50 text-sky-700"><CalendarDays className="h-5 w-5" /></span>
          <div className="flex-1"><h2 className="font-bold text-slate-900">Patient appointments</h2><p className="mt-1 text-xs text-slate-500">Only appointments assigned to your doctor account are shown.</p></div>
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">{appointments.length}</span>
        </div>

        {error && <p className="m-5 p-3 rounded-lg bg-rose-50 border border-rose-200 text-sm text-rose-800">{error}</p>}
        {loading ? (
          <p className="p-8 text-center text-sm text-slate-500">Loading your schedule…</p>
        ) : appointments.length === 0 ? (
          <div className="p-10 text-center">
            <CalendarDays className="w-9 h-9 mx-auto text-slate-300" />
            <p className="mt-3 text-sm font-semibold text-slate-700">No appointments in your schedule yet</p>
            <p className="mt-1 text-xs text-slate-500">New chatbot bookings for you will appear here.</p>
          </div>
        ) : (
          <div className="space-y-3 p-4 sm:p-5">
            {appointments.map((appointment) => (
              <article key={appointment.id} className="grid grid-cols-1 gap-4 rounded-2xl border border-slate-100 bg-gradient-to-r from-white to-sky-50/40 p-4 transition hover:border-sky-100 hover:shadow-sm sm:p-5 md:grid-cols-[1fr_auto]">
                <div className="space-y-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs text-slate-500">{appointment.id}</span>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${statusStyle[appointment.status] || 'bg-slate-100 text-slate-700'}`}>{appointment.status || 'SCHEDULED'}</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <UserRound className="w-4 h-4 mt-0.5 text-medical-600" />
                    <div>
                      <p className="font-bold text-slate-900">{appointment.patient_name || appointment.customer_name || 'Patient'}</p>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-x-5 gap-y-2 text-xs text-slate-600">
                    <span className="inline-flex items-center gap-1.5"><CalendarDays className="w-3.5 h-3.5 text-slate-400" />{prettyDate(appointment.date)}</span>
                    <span className="inline-flex items-center gap-1.5"><Clock3 className="w-3.5 h-3.5 text-slate-400" />{appointment.time_slot || appointment.start_time || 'Time not set'}</span>
                    <span className="inline-flex items-center gap-1.5"><MapPin className="w-3.5 h-3.5 text-slate-400" />{appointment.location || 'Location not set'}</span>
                  </div>
                </div>
                <div className="md:text-right text-xs text-slate-500 self-start">
                  <p>{appointment.department || appointment.specialization || 'Appointment'}</p>
                  {appointment.phone && <p className="mt-1">{appointment.phone}</p>}
                  {appointment.amount != null && <p className="mt-1 font-semibold text-slate-700">Fee: ${appointment.amount}</p>}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>}
    </main>
  );
};
