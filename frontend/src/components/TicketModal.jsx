import React, { useEffect, useMemo, useState } from 'react';
import { StatusBadge, SeverityBadge, CategoryBadge } from './TicketStatusBadge';
import { X, CheckCircle2, AlertTriangle, Calendar, Sparkles } from 'lucide-react';
import api from '../services/api';

const categoriesWithRecords = ['billing', 'appointment'];

export const TicketModal = ({ ticket, onClose, onUpdate }) => {
  const [notes, setNotes] = useState('');
  const [action, setAction] = useState('');
  const [bills, setBills] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [selectedBill, setSelectedBill] = useState('');
  const [selectedAppointment, setSelectedAppointment] = useState('');
  const [billDescription, setBillDescription] = useState('');
  const [billAmount, setBillAmount] = useState('');
  const [billStatus, setBillStatus] = useState('');
  const [appointmentAction, setAppointmentAction] = useState('reschedule');
  const [newDate, setNewDate] = useState('');
  const [slots, setSlots] = useState([]);
  const [newTime, setNewTime] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [actionApplied, setActionApplied] = useState(false);

  const category = String(ticket?.category || 'general').toLowerCase();
  const patientId = String(ticket?.customer_id || ticket?.patient_id || '');
  const patientBills = useMemo(() => bills.filter((b) => String(b.patient_id) === patientId), [bills, patientId]);
  const patientAppointments = useMemo(() => appointments.filter((a) => String(a.customer_id || a.patient_id) === patientId), [appointments, patientId]);
  const currentBill = patientBills.find((b) => b.bill_id === selectedBill);
  const currentAppointment = patientAppointments.find((a) => String(a.id || a.appointment_id) === selectedAppointment);
  const activity = Array.isArray(ticket?.activity) ? ticket.activity.slice(-8).reverse() : [];

  useEffect(() => {
    if (!ticket) return;
    if (category === 'billing') api.get('/api/records/admin/bills').then((r) => setBills(r.data || [])).catch(() => setMessage('Could not load patient bills.'));
    if (category === 'appointment') api.get('/api/appointments').then((r) => setAppointments(r.data || [])).catch(() => setMessage('Could not load patient appointments.'));
  }, [ticket?.ticket_id, category]);

  useEffect(() => {
    if (!currentBill) return;
    setBillDescription(currentBill.description || '');
    setBillAmount(String(currentBill.amount ?? ''));
    setBillStatus(currentBill.status || 'UNPAID');
  }, [selectedBill]);

  useEffect(() => {
    if (!currentAppointment || !newDate || appointmentAction !== 'reschedule') return;
    const doctor = currentAppointment.doctor_id || currentAppointment.doctor_name;
    api.get('/api/appointments/available-slots', { params: { doctorId: doctor, date: newDate } })
      .then((r) => setSlots((r.data?.available_slots || r.data?.slots || []).map((s) => typeof s === 'string' ? s : s.time_slot || s.start_time || s.label).filter(Boolean)))
      .catch(() => setSlots([]));
  }, [currentAppointment, newDate, appointmentAction]);

  if (!ticket) return null;

  const recordAction = async () => {
    if (!notes.trim()) throw new Error('Add a clear resolution note before finishing this complaint.');
    if (category === 'billing') {
      if (!currentBill) throw new Error('Select the bill this complaint is about.');
      const amount = Number(billAmount);
      if (!billDescription.trim() || !Number.isFinite(amount) || amount <= 0) throw new Error('Enter a valid bill description and positive amount.');
      await api.put(`/api/records/admin/bills/${selectedBill}`, { description: billDescription.trim(), amount });
      if (billStatus !== currentBill.status) await api.put(`/api/records/admin/bills/${selectedBill}/status`, { status: billStatus });
      return `Bill ${selectedBill} corrected: ${billDescription.trim()}, ${currentBill.currency || '₹'}${amount.toFixed(2)}, status ${billStatus}.`;
    } else if (category === 'appointment') {
      if (!currentAppointment) throw new Error('Select the appointment this complaint is about.');
      const id = String(currentAppointment.id || currentAppointment.appointment_id);
      if (appointmentAction === 'cancel') {
        await api.put(`/api/appointments/${id}/cancel`);
        return `Appointment ${id} cancelled. Any refund still follows the recorded billing process.`;
      } else {
        if (!newDate || !newTime) throw new Error('Choose an available date and time slot.');
        await api.put(`/api/appointments/${id}/reschedule`, { new_date: newDate, new_time_slot: newTime });
        return `Appointment ${id} rescheduled to ${newDate} at ${newTime}.`;
      }
    } else if (!action.trim()) {
      throw new Error('Describe the action taken to address this complaint.');
    } else return action.trim();
    return '';
  };

  const resolve = async () => {
    setLoading(true); setMessage('');
    let appliedInThisAttempt = false;
    try {
      const completedAction = actionApplied ? action : await recordAction();
      if (!actionApplied) { setActionApplied(true); appliedInThisAttempt = true; }
      setAction(completedAction);
      const outcome = [completedAction, notes.trim()].filter(Boolean).join('\n');
      await api.put(`/api/tickets/${ticket.ticket_id}/status`, { status: 'RESOLVED', resolution_notes: outcome });
      setMessage('Complaint resolved and recorded.');
      onUpdate?.();
    } catch (err) {
      setMessage(actionApplied || appliedInThisAttempt
        ? `The action was applied, but the ticket could not be closed: ${err.response?.data?.detail || err.message || 'unknown error'}. Retry Resolve complaint to finish recording it.`
        : err.response?.data?.detail || err.message || 'Could not resolve this complaint.');
      onUpdate?.();
    } finally { setLoading(false); }
  };

  const saveProgress = async () => {
    setLoading(true); setMessage('');
    try {
      const outcome = [action.trim() && `Action taken: ${action.trim()}`, notes.trim()].filter(Boolean).join('\n');
      await api.put(`/api/tickets/${ticket.ticket_id}/status`, { status: 'IN_PROGRESS', resolution_notes: outcome });
      setMessage('Investigation update saved.'); onUpdate?.();
    } catch (err) { setMessage(err.response?.data?.detail || 'Could not save this update.'); }
    finally { setLoading(false); }
  };

  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4 overflow-y-auto">
    <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto border border-slate-200">
      <div className="px-6 py-4 border-b flex items-center justify-between bg-slate-50"><div className="flex items-center gap-3"><b className="font-mono">{ticket.ticket_id}</b><StatusBadge status={ticket.status}/><SeverityBadge severity={ticket.severity}/></div><button onClick={onClose} className="p-1 text-slate-500"><X className="w-5 h-5"/></button></div>
      <div className="p-6 space-y-5">
        {message && <div className={`p-3 rounded-lg text-sm ${message.includes('resolved') || message.includes('saved') ? 'bg-emerald-50 text-emerald-800' : 'bg-amber-50 text-amber-900'}`}>{message}</div>}
        {ticket.severity === 'CRITICAL' && <div className="bg-rose-50 border border-rose-300 rounded-xl p-4 flex gap-3"><AlertTriangle className="w-5 h-5 text-rose-600 shrink-0"/><p className="text-sm text-rose-900">Critical complaint: record the immediate action and keep the appropriate response team informed.</p></div>}
        <div><div className="flex items-center gap-2 text-xs text-slate-500 mb-1"><CategoryBadge category={category}/><span>•</span><Calendar className="w-3.5 h-3.5"/><span>{new Date(ticket.created_at).toLocaleString()}</span></div><h3 className="text-xl font-bold">{ticket.title}</h3><p className="mt-3 text-sm text-slate-700 bg-slate-50 p-4 rounded-xl">{ticket.description}</p></div>
        <div className="text-sm text-slate-600"><b>Patient:</b> {ticket.customer_name} <span className="text-slate-400">({patientId})</span></div>
        {ticket.ai_summary && <div className="bg-sky-50 rounded-xl p-4 text-sm text-sky-900"><div className="flex gap-2 font-semibold mb-1"><Sparkles className="w-4 h-4"/> Triage summary</div>{ticket.ai_summary}</div>}
        <div><h4 className="mb-2 text-xs font-semibold uppercase text-slate-400">Request history</h4>{activity.length ? <ol className="space-y-2">{activity.map((item, i) => <li key={i} className="border-l-2 border-slate-200 pl-3 text-xs"><b>{item.action || item.status || 'Update'}</b> · {item.actor || 'Team'}{item.note && <p className="whitespace-pre-line text-slate-600">{item.note}</p>}</li>)}</ol> : <p className="text-xs text-slate-500">No earlier updates.</p>}</div>
        {category === 'billing' && <section className="rounded-xl border p-4 space-y-3"><h4 className="font-semibold">Fix the patient bill</h4><select className="w-full border rounded-lg p-2 text-sm" value={selectedBill} onChange={(e) => setSelectedBill(e.target.value)}><option value="">Select a bill for this patient</option>{patientBills.map((b) => <option key={b.bill_id} value={b.bill_id}>{b.description} · {b.currency}{b.amount} · {b.status}</option>)}</select>{selectedBill && <div className="grid sm:grid-cols-2 gap-3"><label className="text-xs">Correct description<input className="mt-1 w-full border rounded-lg p-2 text-sm" value={billDescription} onChange={(e) => setBillDescription(e.target.value)}/></label><label className="text-xs">Correct amount<input type="number" min="0.01" step="0.01" className="mt-1 w-full border rounded-lg p-2 text-sm" value={billAmount} onChange={(e) => setBillAmount(e.target.value)}/></label><label className="text-xs">Bill status<select className="mt-1 w-full border rounded-lg p-2 text-sm" value={billStatus} onChange={(e) => setBillStatus(e.target.value)}>{['UNPAID','PENDING','PAID','OVERDUE','CANCELLED'].map((s)=><option key={s}>{s}</option>)}</select></label></div>}{!patientBills.length && <p className="text-sm text-amber-800">No bill exists for this patient. This complaint cannot be resolved as a bill correction until a bill is created or linked.</p>}</section>}
        {category === 'appointment' && <section className="rounded-xl border p-4 space-y-3"><h4 className="font-semibold">Fix the appointment</h4><select className="w-full border rounded-lg p-2 text-sm" value={selectedAppointment} onChange={(e) => setSelectedAppointment(e.target.value)}><option value="">Select an appointment for this patient</option>{patientAppointments.map((a)=><option key={a.id || a.appointment_id} value={a.id || a.appointment_id}>{a.date} {a.time_slot} · {a.doctor_name} · {a.status}</option>)}</select>{selectedAppointment && <><select className="w-full border rounded-lg p-2 text-sm" value={appointmentAction} onChange={(e)=>setAppointmentAction(e.target.value)}><option value="reschedule">Reschedule appointment</option><option value="cancel">Cancel appointment</option></select>{appointmentAction === 'reschedule' && <div className="grid sm:grid-cols-2 gap-3"><label className="text-xs">New date<input type="date" className="mt-1 w-full border rounded-lg p-2 text-sm" value={newDate} onChange={(e)=>setNewDate(e.target.value)}/></label><label className="text-xs">Available time<select className="mt-1 w-full border rounded-lg p-2 text-sm" value={newTime} onChange={(e)=>setNewTime(e.target.value)}><option value="">Choose a slot</option>{slots.map((s)=><option key={s}>{s}</option>)}</select></label></div>}</>}{!patientAppointments.length && <p className="text-sm text-amber-800">No appointment is linked to this patient.</p>}</section>}
        {!categoriesWithRecords.includes(category) && <label className="block text-xs font-semibold text-slate-600">Action taken<input className="mt-1 w-full border rounded-lg p-3 text-sm" value={action} onChange={(e)=>setAction(e.target.value)} placeholder="Describe the action actually completed"/></label>}
        <label className="block text-xs font-semibold text-slate-600">Resolution note for the patient and audit history<textarea rows={3} className="mt-1 w-full border rounded-xl p-3 text-sm" value={notes} onChange={(e)=>setNotes(e.target.value)} placeholder="What was investigated, what changed, and what should the patient know?"/></label>
      </div>
      <div className="px-6 py-4 bg-slate-50 border-t flex justify-between rounded-b-2xl"><button onClick={onClose} className="px-4 py-2 text-sm text-slate-600">Close</button><div className="flex gap-2"><button disabled={loading} onClick={saveProgress} className="px-4 py-2 text-sm border rounded-lg disabled:opacity-50">Save investigation</button><button disabled={loading} onClick={resolve} className="px-5 py-2 text-sm text-white bg-medical-600 rounded-lg flex items-center gap-2 disabled:opacity-50"><CheckCircle2 className="w-4 h-4"/>{loading ? 'Applying…' : 'Resolve complaint'}</button></div></div>
    </div>
  </div>;
};
