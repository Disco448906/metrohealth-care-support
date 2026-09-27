import React, { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardList,
  CreditCard,
  FileCheck2,
  FileText,
  KeyRound,
  LockKeyhole,
  MessageCircle,
  RefreshCw,
  ShieldCheck,
  UserRound,
  Wallet,
  X,
} from 'lucide-react';
import api from '../services/api';
import { ADMIN_TICKET_CATEGORIES, categoryKeyForTicket, displayTicketStatus, formatTicketDate } from './adminTicketCategories';

const BILL_STATUSES = ['UNPAID', 'PENDING', 'PAID', 'OVERDUE', 'CANCELLED'];
const REFUND_STATUSES = ['NOT_REQUESTED', 'UNDER_REVIEW', 'APPROVED', 'PROCESSING_EXTERNALLY', 'COMPLETED_EXTERNALLY'];
const DOCUMENT_STATUSES = ['REQUESTED', 'RECEIVED', 'VERIFIED', 'MISSING', 'REJECTED'];
const WORKFLOW_STATUSES = ['NEW', 'IN_PROGRESS', 'RESOLVED', 'ESCALATED'];

const prettyStatus = (status) => String(status || '').replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
const money = (bill) => `${bill?.currency || '₹'}${Number(bill?.amount || 0).toLocaleString()}`;

function TextField({ label, value, onChange, type = 'text', placeholder = '' }) {
  return (
    <label className="grid gap-1.5 text-xs font-semibold text-slate-600">
      {label}
      <input
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal text-slate-800 outline-none transition focus:border-medical-500 focus:ring-2 focus:ring-medical-100"
      />
    </label>
  );
}

function SelectField({ label, value, onChange, options, placeholder }) {
  return (
    <label className="grid gap-1.5 text-xs font-semibold text-slate-600">
      {label}
      <select value={value} onChange={onChange} className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal text-slate-800 outline-none focus:border-medical-500 focus:ring-2 focus:ring-medical-100">
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((option) => {
          const key = typeof option === 'string' ? option : option.value;
          const labelText = typeof option === 'string' ? prettyStatus(option) : option.label;
          return <option key={key} value={key}>{labelText}</option>;
        })}
      </select>
    </label>
  );
}

function Notice({ message, error = false }) {
  if (!message) return null;
  return <p role={error ? 'alert' : 'status'} className={`mt-3 rounded-xl px-3 py-2.5 text-xs ${error ? 'border border-rose-200 bg-rose-50 text-rose-800' : 'border border-emerald-200 bg-emerald-50 text-emerald-800'}`}>{message}</p>;
}

function ActionButton({ children, onClick, disabled, tone = 'primary', type = 'button' }) {
  const tones = {
    primary: 'bg-medical-700 text-white hover:bg-medical-800',
    secondary: 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
    danger: 'border border-amber-200 bg-amber-50 text-amber-900 hover:bg-amber-100',
  };
  return (
    <button type={type} onClick={onClick} disabled={disabled} className={`inline-flex items-center justify-center gap-2 rounded-xl px-3.5 py-2.5 text-xs font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${tones[tone]}`}>
      {children}
    </button>
  );
}

function useTicketWorkflow(ticket, onUpdated) {
  const [actionTaken, setActionTaken] = useState('');
  const [patientResponse, setPatientResponse] = useState('');
  const [status, setStatus] = useState(displayTicketStatus(ticket.status));
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [noticeIsError, setNoticeIsError] = useState(false);

  useEffect(() => setStatus(displayTicketStatus(ticket.status)), [ticket.status]);

  const record = async ({ action, nextStatus = 'IN_PROGRESS', response = patientResponse }) => {
    setNotice('');
    setNoticeIsError(false);
    setBusy(true);
    try {
      const result = await api.post(`/api/tickets/${ticket.ticket_id}/admin-update`, {
        status: nextStatus,
        action_taken: action || '',
        patient_response: response || '',
      });
      setStatus(displayTicketStatus(result.data?.status || nextStatus));
      setActionTaken('');
      setPatientResponse('');
      setNotice('Ticket history and patient update saved.');
      await onUpdated?.();
      return result.data;
    } catch (error) {
      const detail = error.response?.data?.detail || error.message || 'Ticket history could not be saved.';
      setNotice(detail);
      setNoticeIsError(true);
      throw error;
    } finally {
      setBusy(false);
    }
  };

  const runDomainAction = async (label, operation, afterSuccess) => {
    setNotice('');
    setNoticeIsError(false);
    setBusy(true);
    let domainSaved = false;
    try {
      const result = await operation();
      domainSaved = true;
      await api.post(`/api/tickets/${ticket.ticket_id}/admin-update`, {
        status: 'IN_PROGRESS',
        action_taken: label,
        patient_response: patientResponse || '',
      });
      setStatus('IN_PROGRESS');
      setPatientResponse('');
      afterSuccess?.(result);
      setNotice('Action saved and added to the ticket history.');
      await onUpdated?.();
      return result;
    } catch (error) {
      const detail = error.response?.data?.detail || error.message || 'The action could not be saved.';
      setNotice(domainSaved ? `The account or record was updated, but the ticket history could not be saved: ${detail}` : detail);
      setNoticeIsError(true);
      throw error;
    } finally {
      setBusy(false);
    }
  };

  const saveWorkflow = async (statusOverride) => {
    const nextStatus = statusOverride || status;
    try {
      await record({ action: actionTaken.trim(), nextStatus, response: patientResponse.trim() });
    } catch { /* Notice is shown inline. */ }
  };

  return {
    actionTaken, setActionTaken,
    patientResponse, setPatientResponse,
    status, setStatus,
    busy, notice, noticeIsError, setNotice, setNoticeIsError,
    record, runDomainAction, saveWorkflow,
  };
}

function WorkflowFields({ workflow, label = 'Action taken / notes', responseLabel = 'Response to patient' }) {
  return (
    <section className="mt-5 rounded-2xl border border-slate-200 bg-slate-50/70 p-4 sm:p-5">
      <div className="flex items-center gap-2">
        <MessageCircle className="h-4 w-4 text-medical-700" aria-hidden="true" />
        <h3 className="text-sm font-bold text-slate-800">Patient update & ticket status</h3>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <label className="grid gap-1.5 text-xs font-semibold text-slate-600">
          {label}
          <textarea value={workflow.actionTaken} onChange={(event) => workflow.setActionTaken(event.target.value)} rows={3} maxLength={2000} placeholder="Describe what was done or the next step." className="w-full resize-y rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal text-slate-800 outline-none focus:border-medical-500 focus:ring-2 focus:ring-medical-100" />
        </label>
        <label className="grid gap-1.5 text-xs font-semibold text-slate-600">
          {responseLabel}
          <textarea value={workflow.patientResponse} onChange={(event) => workflow.setPatientResponse(event.target.value)} rows={3} maxLength={2000} placeholder="Write an update the patient can see in Support Requests." className="w-full resize-y rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal text-slate-800 outline-none focus:border-medical-500 focus:ring-2 focus:ring-medical-100" />
        </label>
      </div>
      <div className="mt-3 flex flex-wrap items-end justify-between gap-3">
        <SelectField label="Status" value={workflow.status} onChange={(event) => workflow.setStatus(event.target.value)} options={WORKFLOW_STATUSES} />
        <ActionButton onClick={() => workflow.saveWorkflow()} disabled={workflow.busy}>
          {workflow.busy ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
          Save update
        </ActionButton>
      </div>
      {workflow.status === 'RESOLVED' && <p className="mt-2 text-[11px] text-amber-800">Record the action taken before resolving this ticket.</p>}
      <Notice message={workflow.notice} error={workflow.noticeIsError} />
    </section>
  );
}

function SimpleTicketUpdate({ ticket, onUpdated }) {
  const workflow = useTicketWorkflow(ticket, onUpdated);

  const saveUpdate = async (event) => {
    event.preventDefault();
    const note = workflow.actionTaken.trim();
    if (!note) {
      workflow.setNotice('Add a short update before saving.');
      workflow.setNoticeIsError(true);
      return;
    }
    try {
      await workflow.record({ action: note, nextStatus: workflow.status, response: note });
    } catch { /* The error is shown below the form. */ }
  };

  return (
    <form onSubmit={saveUpdate} className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5">
      <h3 className="text-sm font-bold text-slate-900">Update this ticket</h3>
      <p className="mt-1 text-xs text-slate-500">Add one short update. It will appear in the ticket history and the patient’s request history.</p>
      <label className="mt-4 grid gap-1.5 text-xs font-semibold text-slate-600">
        Update
        <textarea required value={workflow.actionTaken} onChange={(event) => workflow.setActionTaken(event.target.value)} rows={3} maxLength={2000} placeholder="Write what happened or what the patient should know…" className="w-full resize-y rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal text-slate-800 outline-none focus:border-medical-500 focus:ring-2 focus:ring-medical-100" />
      </label>
      <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <SelectField label="Status" value={workflow.status} onChange={(event) => workflow.setStatus(event.target.value)} options={WORKFLOW_STATUSES} />
        <ActionButton type="submit" disabled={workflow.busy}>
          {workflow.busy ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
          Save update
        </ActionButton>
      </div>
      <Notice message={workflow.notice} error={workflow.noticeIsError} />
    </form>
  );
}

function BillingResolution({ ticket, onUpdated, showWorkflowFields = true }) {
  const workflow = useTicketWorkflow(ticket, onUpdated);
  const [bills, setBills] = useState([]);
  const [selectedBillId, setSelectedBillId] = useState('');
  const [loading, setLoading] = useState(true);
  const [description, setDescription] = useState('');
  const [amount, setAmount] = useState('');
  const [paymentStatus, setPaymentStatus] = useState('');
  const [refundStatus, setRefundStatus] = useState('NOT_REQUESTED');
  const [refundNote, setRefundNote] = useState('');
  const [loadError, setLoadError] = useState('');

  const patientBills = useMemo(() => bills.filter((bill) => String(bill.patient_id) === String(ticket.customer_id)), [bills, ticket.customer_id]);
  const selectedBill = patientBills.find((bill) => bill.bill_id === selectedBillId) || patientBills[0];

  useEffect(() => {
    let alive = true;
    api.get('/api/records/admin/bills')
      .then((result) => { if (alive) setBills(result.data || []); })
      .catch((error) => { if (alive) setLoadError(error.response?.data?.detail || 'Billing records could not be loaded.'); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [ticket.ticket_id]);

  useEffect(() => {
    if (!selectedBill) return;
    setSelectedBillId(selectedBill.bill_id);
    setDescription(selectedBill.description || '');
    setAmount(String(selectedBill.amount ?? ''));
    setPaymentStatus(selectedBill.status || 'UNPAID');
    setRefundStatus(selectedBill.refund_status || 'NOT_REQUESTED');
    setRefundNote(selectedBill.refund_note || '');
  }, [selectedBill?.bill_id]);

  const applyBillUpdate = (updated) => setBills((current) => current.map((bill) => bill.bill_id === updated.bill_id ? updated : bill));

  const saveBilling = () => workflow.runDomainAction('Billing details or payment status updated', async () => {
    if (!selectedBill) throw new Error('Select a patient bill first.');
    const newAmount = Number(amount);
    if (!description.trim() || !Number.isFinite(newAmount) || newAmount <= 0) throw new Error('Enter a bill description and a positive amount.');
    const edited = await api.put(`/api/records/admin/bills/${selectedBill.bill_id}`, { description: description.trim(), amount: newAmount });
    let updated = edited.data;
    if (paymentStatus !== selectedBill.status) {
      const statusResponse = await api.put(`/api/records/admin/bills/${selectedBill.bill_id}/status`, { status: paymentStatus });
      updated = statusResponse.data;
    }
    return updated;
  }, applyBillUpdate);

  const saveRefund = () => workflow.runDomainAction(`Refund workflow set to ${prettyStatus(refundStatus)}`, async () => {
    if (!selectedBill) throw new Error('Select the bill this request concerns.');
    const response = await api.put(`/api/records/admin/bills/${selectedBill.bill_id}/refund`, { refund_status: refundStatus, refund_note: refundNote.trim() });
    return response.data;
  }, applyBillUpdate);

  return (
    <div>
      <div className="flex items-center gap-2"><CreditCard className="h-4 w-4 text-medical-700" /><h3 className="text-sm font-bold text-slate-800">Billing & payment tools</h3></div>
      <p className="mt-1 text-xs text-slate-500">Check the patient’s recorded bill, correct billing details, and update the payment or refund workflow.</p>
      {loading ? <p className="mt-4 rounded-xl bg-slate-50 p-4 text-sm text-slate-500">Loading billing records…</p> : loadError ? <Notice message={loadError} error /> : patientBills.length === 0 ? <p className="mt-4 rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-500">No bill is linked to this patient account yet. Review the ticket details and respond to the patient.</p> : (
        <div className="mt-4 grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
          <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
            <SelectField label="Patient bill" value={selectedBillId} onChange={(event) => setSelectedBillId(event.target.value)} options={patientBills.map((bill) => ({ value: bill.bill_id, label: `${bill.bill_id} · ${money(bill)}` }))} />
            {selectedBill && <div className="mt-4 space-y-2 text-xs text-slate-600">
              <p><span className="font-semibold text-slate-500">Patient:</span> {selectedBill.patient_name || ticket.customer_name}</p>
              <p><span className="font-semibold text-slate-500">Payment method:</span> {selectedBill.payment_method || 'Not recorded'}</p>
              <p><span className="font-semibold text-slate-500">Due date:</span> {selectedBill.due_date || 'Not listed'}</p>
              <p><span className="font-semibold text-slate-500">Current payment status:</span> {prettyStatus(selectedBill.status || 'UNPAID')}</p>
              <p><span className="font-semibold text-slate-500">Recorded refund status:</span> {prettyStatus(selectedBill.refund_status || 'NOT_REQUESTED')}</p>
            </div>}
          </div>
          {selectedBill && <div className="space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-white p-4">
              <h4 className="text-xs font-bold uppercase tracking-wide text-slate-500">Correct bill / payment record</h4>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <TextField label="Billing description" value={description} onChange={(event) => setDescription(event.target.value)} />
                <TextField label={`Amount (${selectedBill.currency || '₹'})`} type="number" value={amount} onChange={(event) => setAmount(event.target.value)} />
                <SelectField label="Payment status" value={paymentStatus} onChange={(event) => setPaymentStatus(event.target.value)} options={BILL_STATUSES} />
              </div>
              <div className="mt-3"><ActionButton onClick={saveBilling} disabled={workflow.busy}><Wallet className="h-3.5 w-3.5" />Save billing details</ActionButton></div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-4">
              <h4 className="text-xs font-bold uppercase tracking-wide text-slate-500">Refund workflow</h4>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <SelectField label="Refund status" value={refundStatus} onChange={(event) => setRefundStatus(event.target.value)} options={REFUND_STATUSES} />
                <TextField label="Refund reference / admin note" value={refundNote} onChange={(event) => setRefundNote(event.target.value)} placeholder="Add the review outcome or external reference" />
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-3"><ActionButton onClick={saveRefund} disabled={workflow.busy}><RefreshCw className="h-3.5 w-3.5" />Record refund status</ActionButton><span className="text-[10px] text-slate-500">This demo records workflow status; it does not move money.</span></div>
            </div>
          </div>}
        </div>
      )}
      {showWorkflowFields ? <WorkflowFields workflow={workflow} label="Billing action / notes" /> : <Notice message={workflow.notice} error={workflow.noticeIsError} />}
    </div>
  );
}

function AccountResolution({ ticket, onUpdated, showWorkflowFields = true }) {
  const workflow = useTicketWorkflow(ticket, onUpdated);
  const [account, setAccount] = useState(null);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  const updateAccount = (next) => {
    setAccount(next);
    setName(next.name || '');
    setEmail(next.email || '');
    setPhone(next.phone || '');
  };

  useEffect(() => {
    let alive = true;
    api.get(`/api/admin/tickets/${ticket.ticket_id}/account`)
      .then((result) => { if (alive) updateAccount(result.data); })
      .catch((error) => { if (alive) setLoadError(error.response?.data?.detail || 'Patient account details could not be loaded.'); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [ticket.ticket_id]);

  const saveDetails = () => workflow.runDomainAction('Patient account contact details corrected', async () => {
    const result = await api.put(`/api/admin/tickets/${ticket.ticket_id}/account`, { name: name.trim(), email: email.trim(), phone: phone.trim() });
    return result.data;
  }, updateAccount);

  const unlock = () => workflow.runDomainAction('Patient account unlocked', async () => {
    const result = await api.post(`/api/admin/tickets/${ticket.ticket_id}/account/unlock`);
    return result.data;
  }, updateAccount);

  const resetPassword = () => workflow.runDomainAction('Password reset request recorded', async () => {
    const result = await api.post(`/api/admin/tickets/${ticket.ticket_id}/account/password-reset`);
    return result.data;
  }, updateAccount);

  return (
    <div>
      <div className="flex items-center gap-2"><KeyRound className="h-4 w-4 text-medical-700" /><h3 className="text-sm font-bold text-slate-800">Account & login tools</h3></div>
      <p className="mt-1 text-xs text-slate-500">Correct patient contact details, unlock a locked account, or record a password reset request.</p>
      {loading ? <p className="mt-4 rounded-xl bg-slate-50 p-4 text-sm text-slate-500">Loading patient account…</p> : loadError ? <Notice message={loadError} error /> : account && <div className="mt-4 grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <h4 className="text-xs font-bold uppercase tracking-wide text-slate-500">Patient account details</h4>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <TextField label="Patient name" value={name} onChange={(event) => setName(event.target.value)} />
            <TextField label="Email address" type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
            <TextField label="Phone number" value={phone} onChange={(event) => setPhone(event.target.value)} />
          </div>
          <div className="mt-3"><ActionButton onClick={saveDetails} disabled={workflow.busy}><UserRound className="h-3.5 w-3.5" />Save account details</ActionButton></div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
          <h4 className="text-xs font-bold uppercase tracking-wide text-slate-500">Login access</h4>
          <div className="mt-3 flex items-start gap-3 rounded-xl bg-white p-3">
            <LockKeyhole className="mt-0.5 h-4 w-4 shrink-0 text-slate-500" />
            <div><p className="text-xs font-semibold text-slate-700">Account status</p><p className={`mt-1 text-xs ${account.account_locked ? 'text-rose-700' : 'text-emerald-700'}`}>{account.account_locked ? 'Locked' : 'Active'}</p></div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <ActionButton onClick={unlock} disabled={workflow.busy || !account.account_locked} tone="secondary"><ShieldCheck className="h-3.5 w-3.5" />Unlock account</ActionButton>
            <ActionButton onClick={resetPassword} disabled={workflow.busy}><KeyRound className="h-3.5 w-3.5" />Initiate reset</ActionButton>
          </div>
          {account.password_reset_required && <p className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] text-amber-900">Password reset request recorded{account.password_reset_requested_at ? ` · ${formatTicketDate(account.password_reset_requested_at)}` : ''}. Email delivery is not configured in this demo.</p>}
        </div>
      </div>}
      {showWorkflowFields ? <WorkflowFields workflow={workflow} label="Account action / notes" /> : <Notice message={workflow.notice} error={workflow.noticeIsError} />}
    </div>
  );
}

function InsuranceResolution({ ticket, onUpdated, showWorkflowFields = true }) {
  const workflow = useTicketWorkflow(ticket, onUpdated);
  const [insurance, setInsurance] = useState({ provider_name: '', member_id: '', group_number: '' });
  const [documents, setDocuments] = useState([]);
  const [documentName, setDocumentName] = useState('');
  const [requestNote, setRequestNote] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    let alive = true;
    api.get(`/api/admin/tickets/${ticket.ticket_id}/insurance`)
      .then((result) => {
        if (!alive) return;
        setInsurance({ provider_name: '', member_id: '', group_number: '', ...(result.data?.insurance || {}) });
        setDocuments(result.data?.documents || []);
      })
      .catch((error) => { if (alive) setLoadError(error.response?.data?.detail || 'Insurance records could not be loaded.'); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [ticket.ticket_id]);

  const updateInsuranceField = (field, value) => setInsurance((current) => ({ ...current, [field]: value }));
  const saveInsurance = () => workflow.runDomainAction('Patient insurance information updated', async () => {
    const result = await api.put(`/api/admin/tickets/${ticket.ticket_id}/insurance`, insurance);
    return result.data;
  }, (result) => setInsurance((current) => ({ ...current, ...result })));

  const requestDocument = () => workflow.runDomainAction(`Requested missing document: ${documentName.trim()}`, async () => {
    if (!documentName.trim()) throw new Error('Enter the name of the missing document.');
    const result = await api.post(`/api/admin/tickets/${ticket.ticket_id}/documents`, { document_name: documentName.trim(), request_note: requestNote.trim() });
    return result.data;
  }, (result) => {
    setDocuments((current) => [result, ...current]);
    setDocumentName('');
    setRequestNote('');
  });

  const updateDocumentStatus = (document, status, note = '') => workflow.runDomainAction(`Document “${document.document_name}” marked ${prettyStatus(status)}`, async () => {
    const result = await api.put(`/api/admin/tickets/${ticket.ticket_id}/documents/${document.document_id}`, { status, note });
    return result.data;
  }, (result) => setDocuments((current) => current.map((item) => item.document_id === result.document_id ? result : item)));

  return (
    <div>
      <div className="flex items-center gap-2"><FileCheck2 className="h-4 w-4 text-medical-700" /><h3 className="text-sm font-bold text-slate-800">Insurance & document tools</h3></div>
      <p className="mt-1 text-xs text-slate-500">Update insurance details, request missing documents, and track verification status.</p>
      {loading ? <p className="mt-4 rounded-xl bg-slate-50 p-4 text-sm text-slate-500">Loading insurance records…</p> : loadError ? <Notice message={loadError} error /> : <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <h4 className="text-xs font-bold uppercase tracking-wide text-slate-500">Insurance information</h4>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <TextField label="Insurance provider" value={insurance.provider_name || ''} onChange={(event) => updateInsuranceField('provider_name', event.target.value)} />
            <TextField label="Member ID" value={insurance.member_id || ''} onChange={(event) => updateInsuranceField('member_id', event.target.value)} />
            <TextField label="Group number" value={insurance.group_number || ''} onChange={(event) => updateInsuranceField('group_number', event.target.value)} />
          </div>
          <div className="mt-3"><ActionButton onClick={saveInsurance} disabled={workflow.busy}><ShieldCheck className="h-3.5 w-3.5" />Save insurance details</ActionButton></div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <h4 className="text-xs font-bold uppercase tracking-wide text-slate-500">Request a missing document</h4>
          <div className="mt-3 grid gap-3">
            <TextField label="Document name" value={documentName} onChange={(event) => setDocumentName(event.target.value)} placeholder="For example, insurance card" />
            <TextField label="Request note" value={requestNote} onChange={(event) => setRequestNote(event.target.value)} placeholder="What the patient should provide" />
          </div>
          <div className="mt-3"><ActionButton onClick={requestDocument} disabled={workflow.busy}><FileText className="h-3.5 w-3.5" />Create document request</ActionButton></div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4 xl:col-span-2">
          <div className="flex items-center justify-between gap-2"><h4 className="text-xs font-bold uppercase tracking-wide text-slate-500">Document status</h4><span className="text-[10px] text-slate-500">{documents.length} record{documents.length === 1 ? '' : 's'}</span></div>
          {documents.length === 0 ? <p className="mt-3 text-xs text-slate-500">No document requests or status records for this patient yet.</p> : <div className="mt-3 space-y-2">{documents.map((document) => (
            <DocumentRow key={document.document_id} document={document} busy={workflow.busy} onUpdate={updateDocumentStatus} />
          ))}</div>}
        </div>
      </div>}
      {showWorkflowFields ? <WorkflowFields workflow={workflow} label="Insurance action / notes" /> : <Notice message={workflow.notice} error={workflow.noticeIsError} />}
    </div>
  );
}

function DocumentRow({ document, busy, onUpdate }) {
  const [status, setStatus] = useState(document.status || 'REQUESTED');
  const [note, setNote] = useState(document.status_note || '');
  return (
    <div className="grid gap-2 rounded-xl border border-slate-200 bg-white p-3 sm:grid-cols-[1fr_180px_1fr_auto] sm:items-end">
      <div><p className="text-xs font-semibold text-slate-800">{document.document_name}</p><p className="mt-1 text-[10px] text-slate-500">{document.document_id} · {formatTicketDate(document.created_at)}</p></div>
      <SelectField label="Verification status" value={status} onChange={(event) => setStatus(event.target.value)} options={DOCUMENT_STATUSES} />
      <TextField label="Status note" value={note} onChange={(event) => setNote(event.target.value)} placeholder="Optional verification note" />
      <ActionButton disabled={busy} onClick={() => onUpdate(document, status, note)} tone="secondary">Update</ActionButton>
    </div>
  );
}

function ServiceResolution({ ticket, onUpdated, showWorkflowFields = true }) {
  const workflow = useTicketWorkflow(ticket, onUpdated);
  return (
    <div>
      <div className="flex items-center gap-2"><ClipboardList className="h-4 w-4 text-medical-700" /><h3 className="text-sm font-bold text-slate-800">Service complaint response</h3></div>
      <p className="mt-1 text-xs text-slate-500">Record the operational action taken and write a clear response the patient can see.</p>
      <div className="mt-4 rounded-2xl border border-emerald-100 bg-emerald-50/60 p-4 text-xs leading-5 text-emerald-950">
        Common follow-up: review the service event, coordinate with the relevant team, and record any agreed next step or remedy.
      </div>
      {showWorkflowFields ? <WorkflowFields workflow={workflow} label="Action taken" responseLabel="Admin response to patient" /> : <Notice message={workflow.notice} error={workflow.noticeIsError} />}
    </div>
  );
}

function GeneralResolution({ ticket, onUpdated, showWorkflowFields = true }) {
  const workflow = useTicketWorkflow(ticket, onUpdated);
  return (
    <div>
      <div className="flex items-center gap-2"><AlertTriangle className="h-4 w-4 text-medical-700" /><h3 className="text-sm font-bold text-slate-800">General / other support tools</h3></div>
      <p className="mt-1 text-xs text-slate-500">Use this category for non-clinical tickets outside billing, account, insurance, and service workflows.</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-4"><p className="text-xs font-semibold text-slate-700">Manual follow-up</p><p className="mt-1 text-[11px] leading-5 text-slate-500">Record the team contacted, next step, or reason for escalation in the action field below.</p></div>
        <div className="rounded-2xl border border-amber-200 bg-amber-50/70 p-4"><p className="text-xs font-semibold text-amber-950">Escalation</p><p className="mt-1 text-[11px] leading-5 text-amber-900">Choose Escalated when another support lead or department must take over.</p></div>
      </div>
      {showWorkflowFields ? <WorkflowFields workflow={workflow} label="Manual action / escalation reason" responseLabel="Response to patient" /> : <Notice message={workflow.notice} error={workflow.noticeIsError} />}
    </div>
  );
}

export function AdminTicketResolutionPanel({ ticket, onClose, onUpdated }) {
  const categoryKey = categoryKeyForTicket(ticket);
  const category = ADMIN_TICKET_CATEGORIES.find((item) => item.key === categoryKey) || ADMIN_TICKET_CATEGORIES.at(-1);
  const [showCategoryTools, setShowCategoryTools] = useState(false);

  useEffect(() => {
    const onKeyDown = (event) => { if (event.key === 'Escape') onClose?.(); };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose]);

  let Resolution = GeneralResolution;
  if (categoryKey === 'billing') Resolution = BillingResolution;
  if (categoryKey === 'account') Resolution = AccountResolution;
  if (categoryKey === 'insurance') Resolution = InsuranceResolution;
  if (categoryKey === 'service') Resolution = ServiceResolution;
  const hasCategoryTools = ['billing', 'account', 'insurance'].includes(categoryKey);
  const priority = String(ticket.priority || ticket.severity || 'MEDIUM').toUpperCase();

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/45 p-3 backdrop-blur-sm sm:p-6" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose?.(); }}>
      <section role="dialog" aria-modal="true" aria-labelledby="admin-ticket-dialog-title" className="my-2 w-full max-w-3xl overflow-hidden rounded-3xl border border-white/50 bg-white shadow-2xl sm:my-4">
        <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-5 py-4 sm:px-7 sm:py-5">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2"><span className="rounded-full bg-medical-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-medical-700">{category.shortLabel || category.label}</span><span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-600">{displayTicketStatus(ticket.status).replaceAll('_', ' ')}</span></div>
            <h2 id="admin-ticket-dialog-title" className="mt-2 text-lg font-bold tracking-tight text-slate-900 sm:text-xl">{ticket.title || 'Patient support request'}</h2>
            <p className="mt-1 text-xs text-slate-500">{ticket.ticket_id} · Opened {formatTicketDate(ticket.created_at)}</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close ticket details" className="rounded-xl p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"><X className="h-5 w-5" /></button>
        </div>

        <div className="space-y-4 bg-slate-50/75 p-4 sm:p-6">
          <section className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5">
            <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs">
              <span><span className="text-slate-500">Patient</span><span className="ml-2 font-semibold text-slate-800">{ticket.customer_name || 'Patient'}</span></span>
              <span><span className="text-slate-500">Priority</span><span className={`ml-2 font-semibold ${priority === 'HIGH' || priority === 'CRITICAL' ? 'text-rose-700' : 'text-slate-800'}`}>{prettyStatus(priority)}</span></span>
              {ticket.assigned_staff && <span><span className="text-slate-500">Assigned to</span><span className="ml-2 font-semibold text-slate-800">{ticket.assigned_staff}</span></span>}
            </div>
            <h3 className="mt-4 text-xs font-bold uppercase tracking-wide text-slate-500">Patient’s request</h3>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{ticket.description || 'No additional details were provided.'}</p>
            {ticket.ai_summary && <p className="mt-3 text-xs leading-5 text-slate-500">Summary: {ticket.ai_summary}</p>}
          </section>

          <SimpleTicketUpdate ticket={ticket} onUpdated={onUpdated} />

          {hasCategoryTools && <details onToggle={(event) => setShowCategoryTools(event.currentTarget.open)} className="rounded-2xl border border-slate-200 bg-white">
            <summary className="cursor-pointer list-none px-4 py-3 text-xs font-semibold text-slate-700 marker:hidden">
              More {category.label.toLowerCase()} tools <span className="ml-1 font-normal text-slate-400">(optional)</span>
            </summary>
            {showCategoryTools && <div className="border-t border-slate-100 p-4">
              <p className="mb-4 text-xs leading-5 text-slate-500">Use these tools only when you need to update a linked {category.shortLabel.toLowerCase()} record. Add a patient update in the form above.</p>
              <Resolution ticket={ticket} onUpdated={onUpdated} showWorkflowFields={false} />
            </div>}
          </details>}

          {Array.isArray(ticket.activity) && ticket.activity.length > 0 && <details className="rounded-2xl border border-slate-200 bg-white">
            <summary className="cursor-pointer list-none px-4 py-3 text-xs font-semibold text-slate-700 marker:hidden">Ticket history <span className="ml-1 font-normal text-slate-400">({ticket.activity.length})</span></summary>
            <ol className="space-y-3 border-t border-slate-100 px-4 py-4">{ticket.activity.slice(-5).reverse().map((item, index) => <li key={`${item.created_at}-${index}`} className="border-l-2 border-medical-100 pl-3"><p className="text-xs font-semibold text-slate-700">{item.action || 'Ticket update'}</p><p className="mt-0.5 text-[10px] text-slate-400">{formatTicketDate(item.created_at)} · {item.actor || 'Team'}</p>{item.internal_action && <p className="mt-1 whitespace-pre-wrap text-[10px] leading-4 text-slate-600"><span className="font-semibold">Admin action:</span> {item.internal_action}</p>}{(item.patient_response || item.note) && <p className="mt-1 whitespace-pre-wrap text-[10px] leading-4 text-slate-500"><span className="font-semibold">Patient update:</span> {item.patient_response || item.note}</p>}</li>)}</ol>
          </details>}
          </div>
        <div className="flex justify-end border-t border-slate-100 px-5 py-3 sm:px-7">
          <button type="button" onClick={onClose} className="inline-flex items-center gap-1 font-semibold text-medical-700 hover:text-medical-900">Close</button>
        </div>
      </section>
    </div>
  );
}

export default AdminTicketResolutionPanel;
