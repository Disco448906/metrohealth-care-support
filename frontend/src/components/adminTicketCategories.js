export const CLINICAL_TICKET_CATEGORIES = new Set([
  'patient_safety',
  'clinical_care',
  'medical_records',
]);

export const ADMIN_TICKET_CATEGORIES = [
  { key: 'billing', label: 'Billing & Payment', shortLabel: 'Billing', categories: ['billing', 'billing_payment', 'payment'] },
  { key: 'account', label: 'Account & Login', shortLabel: 'Account', categories: ['account', 'account_login', 'login'] },
  { key: 'insurance', label: 'Insurance & Documents', shortLabel: 'Insurance', categories: ['insurance', 'insurance_documents', 'documents'] },
  { key: 'service', label: 'Service Complaints', shortLabel: 'Service', categories: ['service', 'service_complaint', 'patient_experience'] },
  { key: 'other', label: 'General / Other', shortLabel: 'General / Other', categories: [] },
];

export function categoryKeyForTicket(ticket) {
  const category = String(ticket?.category || 'general').trim().toLowerCase();
  if (CLINICAL_TICKET_CATEGORIES.has(category)) return null;
  const match = ADMIN_TICKET_CATEGORIES.find((item) => item.categories.includes(category));
  return match?.key || 'other';
}

export function displayTicketStatus(status) {
  const normalized = String(status || 'OPEN').toUpperCase();
  if (['OPEN', 'ASSIGNED', 'NEW', 'TICKET_CREATED'].includes(normalized)) return 'NEW';
  if (normalized === 'IN_PROGRESS') return 'IN_PROGRESS';
  if (['RESOLVED', 'CLOSED', 'AUTO_RESOLVED'].includes(normalized)) return 'RESOLVED';
  if (normalized === 'ESCALATED') return 'ESCALATED';
  return 'NEW';
}

export function formatTicketDate(value) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(date);
}
