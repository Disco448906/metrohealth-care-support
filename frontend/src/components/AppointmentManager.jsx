import React, { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  CalendarDays, CalendarPlus, Check, ChevronDown, Clock3, MapPin,
  MessageCircle, RefreshCw, Search, X,
} from 'lucide-react';
import api from '../services/api';
import { SMSNotificationModal } from './SMSNotificationModal';

const ACTIVE_STATUSES = new Set(['CONFIRMED', 'RESCHEDULED']);

const appointmentTimestamp = (appointment) => {
  if (!appointment?.date) return 0;
  const slot = String(appointment.time_slot || appointment.start_time || '').match(/(\d{1,2}):(\d{2})\s*(AM|PM)/i);
  const date = new Date(`${appointment.date}T00:00:00`);
  if (Number.isNaN(date.getTime())) return 0;
  if (slot) {
    let hour = Number(slot[1]) % 12;
    if (slot[3].toUpperCase() === 'PM') hour += 12;
    date.setHours(hour, Number(slot[2]), 0, 0);
  }
  return date.getTime();
};

const displayDate = (value) => {
  if (!value) return 'Date not listed';
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
};

const localDateValue = (date) => {
  const offset = date.getTimezoneOffset();
  return new Date(date.getTime() - offset * 60_000).toISOString().slice(0, 10);
};

const escapeCalendarText = (value = '') => String(value).replace(/\\/g, '\\\\').replace(/\n/g, '\\n').replace(/,/g, '\\,').replace(/;/g, '\\;');

const downloadCalendarInvite = (appointment) => {
  const start = new Date(appointmentTimestamp(appointment));
  const end = new Date(start.getTime() + 30 * 60_000);
  const toCalendarDate = (date) => date.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
  const title = `MetroHealth visit with ${appointment.doctor_name || 'your doctor'}`;
  const lines = [
    'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//MetroHealth//Patient Portal//EN', 'BEGIN:VEVENT',
    `UID:${escapeCalendarText(appointment.id || appointment.appointment_id || `${start.getTime()}@metrohealth`)}`,
    `DTSTAMP:${toCalendarDate(new Date())}`, `DTSTART:${toCalendarDate(start)}`, `DTEND:${toCalendarDate(end)}`,
    `SUMMARY:${escapeCalendarText(title)}`,
    `LOCATION:${escapeCalendarText(appointment.location || 'MetroHealth')}`,
    `DESCRIPTION:${escapeCalendarText(`${appointment.department || 'Appointment'} · ${appointment.id || appointment.appointment_id || ''}`)}`,
    'END:VEVENT', 'END:VCALENDAR',
  ];
  const file = new Blob([lines.join('\r\n')], { type: 'text/calendar;charset=utf-8' });
  const url = URL.createObjectURL(file);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `metrohealth-visit-${appointment.date || 'appointment'}.ics`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
};

const StatusPill = ({ status }) => {
  const styles = {
    CONFIRMED: 'bg-emerald-50 text-emerald-700',
    RESCHEDULED: 'bg-sky-50 text-sky-700',
    COMPLETED: 'bg-slate-100 text-slate-600',
    CANCELLED: 'bg-rose-50 text-rose-700',
  };
  return <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${styles[status] || 'bg-amber-50 text-amber-800'}`}>{(status || 'SCHEDULED').replaceAll('_', ' ')}</span>;
};

export function AppointmentManager({ appointments, loading, onRefresh }) {
  const [filter, setFilter] = useState('upcoming');
  const [modal, setModal] = useState(null);
  const [selectedDate, setSelectedDate] = useState('');
  const [slots, setSlots] = useState([]);
  const [selectedSlot, setSelectedSlot] = useState('');
  const [slotMessage, setSlotMessage] = useState('');
  const [actionError, setActionError] = useState('');
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [notificationPreview, setNotificationPreview] = useState(null);
  const [expandedId, setExpandedId] = useState('');

  const now = Date.now();
  const sections = useMemo(() => {
    const ordered = [...appointments].sort((a, b) => appointmentTimestamp(a) - appointmentTimestamp(b));
    const upcoming = ordered.filter((appointment) => ACTIVE_STATUSES.has(appointment.status) && appointmentTimestamp(appointment) >= now);
    const history = ordered.filter((appointment) => !upcoming.includes(appointment)).reverse();
    return { upcoming, history, all: [...upcoming, ...history] };
  }, [appointments, now]);

  const visibleAppointments = sections[filter];
  const nextVisit = sections.upcoming[0];

  const openModal = (type, appointment) => {
    setActionError('');
    setNotice('');
    setSlots([]);
    setSelectedSlot('');
    setSlotMessage('');
    setSelectedDate('');
    setModal({ type, appointment });
  };

  const closeModal = () => {
    if (busy) return;
    setModal(null);
    setActionError('');
  };

  const findSlots = async () => {
    if (!selectedDate) return;
    const appointment = modal.appointment;
    setBusy(true);
    setActionError('');
    setSlots([]);
    setSelectedSlot('');
    try {
      const doctor = appointment.doctor_id || appointment.doctor_name;
      const { data } = await api.get('/api/appointments/available-slots', { params: { doctorId: doctor, date: selectedDate } });
      if (!data.success) {
        setSlotMessage(data.message || 'No appointment times could be loaded for this date.');
      } else if (!data.available_slots?.length) {
        setSlotMessage('There are no open times on this date. Try another day.');
      } else {
        setSlots(data.available_slots);
        setSlotMessage(data.message || 'Choose an available time.');
      }
    } catch (error) {
      setSlotMessage(error.response?.data?.detail || 'Could not check availability. Please try again.');
    } finally {
      setBusy(false);
    }
  };

  const confirmReschedule = async (event) => {
    event.preventDefault();
    if (!selectedSlot) return;
    setBusy(true);
    setActionError('');
    try {
      const id = modal.appointment.id || modal.appointment.appointment_id;
      const { data: updatedAppointment } = await api.put(`/api/appointments/${encodeURIComponent(id)}/reschedule`, { new_date: selectedDate, new_time_slot: selectedSlot });
      setModal(null);
      setNotice('Your appointment was rescheduled. Review the confirmation preview below.');
      setNotificationPreview(updatedAppointment);
      await onRefresh();
    } catch (error) {
      setActionError(error.response?.data?.detail || 'We could not reschedule this appointment. Please try again.');
    } finally {
      setBusy(false);
    }
  };

  const confirmCancellation = async () => {
    setBusy(true);
    setActionError('');
    try {
      const id = modal.appointment.id || modal.appointment.appointment_id;
      const { data: updatedAppointment } = await api.put(`/api/appointments/${encodeURIComponent(id)}/cancel`);
      setModal(null);
      setNotice(updatedAppointment.message || 'Your appointment was cancelled.');
      setNotificationPreview(updatedAppointment);
      await onRefresh();
    } catch (error) {
      setActionError(error.response?.data?.detail || 'We could not cancel this appointment. Please contact the patient desk.');
    } finally {
      setBusy(false);
    }
  };

  const today = localDateValue(new Date());
  const maxDate = localDateValue(new Date(Date.now() + 30 * 24 * 60 * 60_000));

  return (
    <section className="space-y-4">
      {nextVisit && (
        <article className="overflow-hidden rounded-2xl border border-medical-100 bg-gradient-to-br from-medical-50 via-white to-emerald-50 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4 p-5 sm:p-6">
            <div className="flex min-w-0 items-start gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-white text-medical-700 shadow-sm"><CalendarDays className="h-6 w-6" /></div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2"><span className="text-xs font-bold uppercase tracking-wider text-medical-700">Your next visit</span><StatusPill status={nextVisit.status} /></div>
                <h3 className="mt-1 truncate text-lg font-bold text-slate-900">{nextVisit.doctor_name || 'Doctor appointment'}</h3>
                <p className="mt-1 text-sm text-slate-600">{nextVisit.department || 'MetroHealth'} · {displayDate(nextVisit.date)} · {nextVisit.time_slot || nextVisit.start_time || 'Time not listed'}</p>
                {nextVisit.location && <p className="mt-1 inline-flex items-center gap-1 text-xs text-slate-500"><MapPin className="h-3.5 w-3.5" />{nextVisit.location}</p>}
              </div>
            </div>
            <button onClick={() => downloadCalendarInvite(nextVisit)} className="inline-flex shrink-0 items-center gap-2 rounded-xl border border-medical-200 bg-white px-3.5 py-2.5 text-sm font-semibold text-medical-800 shadow-sm transition hover:bg-medical-50"><CalendarPlus className="h-4 w-4" /> Add to calendar</button>
          </div>
        </article>
      )}

      {notice && <div role="status" className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800"><Check className="h-4 w-4 shrink-0" />{notice}<button onClick={() => setNotice('')} className="ml-auto rounded p-1 hover:bg-emerald-100" aria-label="Dismiss update"><X className="h-4 w-4" /></button></div>}

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-col gap-4 border-b border-slate-100 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="font-bold text-slate-900">Appointments <span className="ml-1 text-xs font-medium text-slate-400">{appointments.length}</span></h2>
            <p className="mt-0.5 text-xs text-slate-500">View and manage your hospital visits.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex rounded-xl bg-slate-100 p-1" aria-label="Filter appointments">
              {[['upcoming', 'Upcoming'], ['history', 'Past'], ['all', 'All']].map(([key, label]) => <button key={key} onClick={() => setFilter(key)} className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${filter === key ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-800'}`}>{label}{key === 'upcoming' && sections.upcoming.length > 0 ? ` · ${sections.upcoming.length}` : ''}</button>)}
            </div>
            <button onClick={onRefresh} disabled={loading} className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-60"><RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />Refresh</button>
          </div>
        </div>

        {loading ? <p className="px-5 py-8 text-center text-sm text-slate-500">Loading your appointments…</p> : visibleAppointments.length === 0 ? (
          <div className="px-5 py-10 text-center">
            <CalendarDays className="mx-auto h-9 w-9 text-slate-300" />
            <p className="mt-3 text-sm font-semibold text-slate-700">{filter === 'upcoming' ? 'No upcoming visits' : 'No appointments to show'}</p>
            <p className="mt-1 text-xs text-slate-500">Book or ask a question through the care assistant.</p>
            <Link to="/chat" className="mt-4 inline-flex items-center gap-2 rounded-lg bg-medical-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-medical-700"><MessageCircle className="h-3.5 w-3.5" />Open care assistant</Link>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {visibleAppointments.map((appointment) => {
              const id = appointment.id || appointment.appointment_id;
              const canManage = ACTIVE_STATUSES.has(appointment.status) && appointmentTimestamp(appointment) >= Date.now();
              const expanded = expandedId === id;
              return (
                <article key={id} className="px-5 py-4 transition hover:bg-slate-50/60">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2"><h3 className="font-semibold text-slate-900">{appointment.doctor_name || 'Doctor appointment'}</h3><StatusPill status={appointment.status} /></div>
                      <p className="mt-1 text-xs text-slate-500">{appointment.department || 'Department not listed'} · <span className="font-mono">{id}</span></p>
                      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                        <span className="inline-flex items-center gap-1"><CalendarDays className="h-3.5 w-3.5" />{displayDate(appointment.date)}</span>
                        <span className="inline-flex items-center gap-1"><Clock3 className="h-3.5 w-3.5" />{appointment.time_slot || appointment.start_time || 'Time not listed'}</span>
                        {appointment.location && <span className="inline-flex items-center gap-1"><MapPin className="h-3.5 w-3.5" />{appointment.location}</span>}
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {canManage && <>
                        <button onClick={() => openModal('reschedule', appointment)} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:border-medical-300 hover:text-medical-700">Reschedule</button>
                        <button onClick={() => openModal('cancel', appointment)} className="rounded-lg border border-rose-200 bg-white px-3 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-50">Cancel</button>
                      </>}
                      <button onClick={() => setExpandedId(expanded ? '' : id)} aria-expanded={expanded} className="inline-flex items-center gap-1 rounded-lg px-2 py-2 text-xs font-semibold text-slate-500 hover:bg-slate-100 hover:text-slate-800">Details<ChevronDown className={`h-3.5 w-3.5 transition ${expanded ? 'rotate-180' : ''}`} /></button>
                    </div>
                  </div>
                  {expanded && <div className="mt-4 grid gap-3 rounded-xl bg-slate-50 p-4 text-xs sm:grid-cols-3"><div><p className="text-slate-400">Appointment ID</p><p className="mt-1 font-mono font-semibold text-slate-700">{id}</p></div><div><p className="text-slate-400">Department</p><p className="mt-1 font-semibold text-slate-700">{appointment.department || appointment.specialization || 'Not listed'}</p></div><div><p className="text-slate-400">Location</p><p className="mt-1 font-semibold text-slate-700">{appointment.location || 'Not listed'}</p></div>{appointment.amount != null && <div><p className="text-slate-400">Appointment fee</p><p className="mt-1 font-semibold text-slate-700">{appointment.currency || '₹'}{appointment.amount}</p></div>}</div>}
                </article>
              );
            })}
          </div>
        )}
      </section>

      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4" onMouseDown={(event) => { if (event.target === event.currentTarget) closeModal(); }}>
          <section role="dialog" aria-modal="true" aria-labelledby="appointment-dialog-title" className="w-full max-w-lg overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-5 py-4">
              <div><p className="text-xs font-semibold uppercase tracking-wide text-medical-700">{modal.type === 'reschedule' ? 'Change your visit' : 'Appointment options'}</p><h2 id="appointment-dialog-title" className="mt-1 text-lg font-bold text-slate-900">{modal.type === 'reschedule' ? 'Reschedule appointment' : 'Cancel appointment?'}</h2><p className="mt-1 text-sm text-slate-500">{modal.appointment.doctor_name || 'Doctor appointment'} · {displayDate(modal.appointment.date)}</p></div>
              <button onClick={closeModal} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700" aria-label="Close"><X className="h-5 w-5" /></button>
            </div>

            {modal.type === 'reschedule' ? (
              <form onSubmit={confirmReschedule} className="space-y-4 p-5">
                <div className="rounded-xl border border-sky-100 bg-sky-50 px-4 py-3 text-xs leading-5 text-sky-900">Changes are available up to 30 days ahead, at least 24 hours before your current visit, and up to two times per appointment.</div>
                <label className="block text-sm font-medium text-slate-700">Choose a new date<input required type="date" min={today} max={maxDate} value={selectedDate} onChange={(event) => { setSelectedDate(event.target.value); setSlots([]); setSelectedSlot(''); setSlotMessage(''); setActionError(''); }} className="mt-1.5 block w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm focus:border-medical-400 focus:outline-none focus:ring-2 focus:ring-medical-100" /></label>
                <button type="button" onClick={findSlots} disabled={!selectedDate || busy} className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-medical-200 bg-medical-50 px-4 py-2.5 text-sm font-semibold text-medical-800 hover:bg-medical-100 disabled:cursor-not-allowed disabled:opacity-50"><Search className="h-4 w-4" />{busy ? 'Checking available times…' : 'Find available times'}</button>
                {slotMessage && <p role="status" className="text-xs text-slate-600">{slotMessage}</p>}
                {slots.length > 0 && <label className="block text-sm font-medium text-slate-700">Available time<select required value={selectedSlot} onChange={(event) => setSelectedSlot(event.target.value)} className="mt-1.5 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm focus:border-medical-400 focus:outline-none focus:ring-2 focus:ring-medical-100"><option value="">Select an open time</option>{slots.map((slot) => <option key={slot} value={slot}>{slot}</option>)}</select></label>}
                {actionError && <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs leading-5 text-rose-800">{actionError}</p>}
                <div className="flex justify-end gap-2 border-t border-slate-100 pt-4"><button type="button" onClick={closeModal} disabled={busy} className="rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-100">Keep current visit</button><button type="submit" disabled={!selectedSlot || busy} className="rounded-xl bg-medical-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-medical-700 disabled:cursor-not-allowed disabled:opacity-50">{busy ? 'Saving…' : 'Confirm new time'}</button></div>
              </form>
            ) : (
              <div className="space-y-4 p-5">
                <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900">Please cancel at least 24 hours before your visit. Requests made closer to the visit need patient desk approval. This demo does not process payments or refunds.</div>
                {actionError && <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs leading-5 text-rose-800">{actionError}</p>}
                <div className="flex justify-end gap-2 border-t border-slate-100 pt-4"><button onClick={closeModal} disabled={busy} className="rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-100">Keep appointment</button><button onClick={confirmCancellation} disabled={busy} className="rounded-xl bg-rose-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-rose-700 disabled:opacity-50">{busy ? 'Cancelling…' : 'Cancel appointment'}</button></div>
              </div>
            )}
          </section>
        </div>
      )}
      {notificationPreview && <SMSNotificationModal appointment={notificationPreview} onClose={() => setNotificationPreview(null)} />}
    </section>
  );
}
