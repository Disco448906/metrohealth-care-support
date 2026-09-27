import { jsPDF } from 'jspdf';

const printable = (value) => String(value ?? 'Not supplied')
  .replaceAll('₹', 'INR ')
  .replace(/[–—]/g, '-')
  .replace(/[^\x20-\x7E\n]/g, '?')
  .trim() || 'Not supplied';

const safeFilename = (value) => printable(value).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'patient-document';

export function downloadPatientDocument(type, record) {
  const pdf = new jsPDF({ unit: 'mm', format: 'a4' });
  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();
  const left = 18;
  const right = pageWidth - 18;
  let y = 20;
  const title = type === 'report' ? 'HEALTH REPORT' : type === 'prescription' ? 'PRESCRIPTION' : 'HOSPITAL BILL';

  const footer = () => {
    const count = pdf.internal.getNumberOfPages();
    for (let page = 1; page <= count; page += 1) {
      pdf.setPage(page);
      pdf.setDrawColor(220, 228, 235);
      pdf.line(left, pageHeight - 15, right, pageHeight - 15);
      pdf.setFontSize(8); pdf.setTextColor(110, 125, 140);
      pdf.text('CONFIDENTIAL PATIENT DOCUMENT  |  Keep this document secure', left, pageHeight - 9);
      pdf.text(`Page ${page} of ${count}`, right, pageHeight - 9, { align: 'right' });
    }
  };
  const ensureSpace = (height = 18) => {
    if (y + height > pageHeight - 23) { pdf.addPage(); y = 20; }
  };
  const section = (heading) => {
    ensureSpace(16); y += 3;
    pdf.setFont('helvetica', 'bold'); pdf.setFontSize(10); pdf.setTextColor(17, 77, 102);
    pdf.text(printable(heading).toUpperCase(), left, y); y += 2;
    pdf.setDrawColor(215, 228, 235); pdf.line(left, y, right, y); y += 6;
  };
  const field = (label, value) => {
    const lines = pdf.splitTextToSize(printable(value), right - left - 43);
    const height = Math.max(6, lines.length * 4.5);
    ensureSpace(height + 2);
    pdf.setFont('helvetica', 'bold'); pdf.setFontSize(9); pdf.setTextColor(75, 90, 105);
    pdf.text(printable(label), left, y);
    pdf.setFont('helvetica', 'normal'); pdf.setTextColor(35, 47, 60);
    pdf.text(lines, left + 43, y);
    y += height;
  };

  pdf.setFillColor(16, 91, 119); pdf.roundedRect(left, y, right - left, 26, 2, 2, 'F');
  pdf.setTextColor(255, 255, 255); pdf.setFont('helvetica', 'bold'); pdf.setFontSize(12);
  pdf.text('METROHEALTH', left + 7, y + 9);
  pdf.setFontSize(9); pdf.setFont('helvetica', 'normal'); pdf.text('Patient Care Services', left + 7, y + 16);
  pdf.setFont('helvetica', 'bold'); pdf.setFontSize(11); pdf.text(title, right - 7, y + 14, { align: 'right' });
  y += 34;
  pdf.setFont('helvetica', 'bold'); pdf.setFontSize(17); pdf.setTextColor(24, 37, 51); pdf.text(printable(record.title || record.medicine || record.description || title), left, y); y += 8;
  pdf.setFont('helvetica', 'normal'); pdf.setFontSize(9); pdf.setTextColor(105, 118, 131);
  const documentId = record.record_id || record.bill_id || 'Not assigned';
  pdf.text(`Document ID: ${printable(documentId)}    Issued: ${printable(record.issued_date || record.report_date || record.service_date || record.created_at?.slice(0, 10))}`, left, y); y += 8;

  section('Patient and provider');
  field('Patient name', record.patient_name);
  field('Patient ID', record.patient_id);
  field('Attending clinician', record.doctor_name || record.provider_name);
  field('Department / service', record.specialty || record.department || record.report_type);

  if (type === 'report') {
    section('Clinical report');
    field('Report type', record.report_type || 'Clinical report');
    field('Clinical indication', record.indication);
    field('Findings', record.findings || record.details);
    field('Clinical impression', record.impression);
    field('Recommendations / follow-up', record.recommendations);
    field('Report date', record.report_date || record.created_at?.slice(0, 10));
  } else if (type === 'prescription') {
    section('Prescription details');
    field('Diagnosis / indication', record.diagnosis);
    field('Medication', record.medicine || record.title);
    field('Strength', record.strength);
    field('Dose', record.dosage);
    field('Route', record.route);
    field('Frequency', record.frequency);
    field('Duration', record.duration);
    field('Quantity', record.quantity);
    field('Refills', record.refills ?? 'Not supplied');
    field('Instructions to patient', record.instructions || record.details);
    field('Date prescribed', record.issued_date || record.created_at?.slice(0, 10));
  } else {
    section('Billing details');
    field('Bill number', record.bill_id);
    field('Service date', record.service_date || record.created_at?.slice(0, 10));
    field('Due date', record.due_date);
    field('Payment status', record.status);
    section('Itemized charges');
    let lines = record.line_items;
    if (typeof lines === 'string') { try { lines = JSON.parse(lines); } catch { lines = []; } }
    if (!Array.isArray(lines) || lines.length === 0) lines = [{ description: record.description, quantity: 1, unit_price: record.amount, total: record.amount }];
    lines.forEach((item, index) => {
      field(`Item ${index + 1}`, `${item.description || 'Service'} | Qty ${item.quantity ?? 1} | Unit ${record.currency || 'INR'} ${Number(item.unit_price ?? item.total ?? 0).toFixed(2)} | Total ${record.currency || 'INR'} ${Number(item.total ?? item.unit_price ?? 0).toFixed(2)}`);
    });
    field('Subtotal', `${record.currency || 'INR'} ${Number(record.subtotal ?? record.amount ?? 0).toFixed(2)}`);
    field('Tax', `${record.currency || 'INR'} ${Number(record.tax ?? 0).toFixed(2)}`);
    field('Total due', `${record.currency || 'INR'} ${Number(record.amount ?? 0).toFixed(2)}`);
    field('Payment method', record.payment_method);
  }

  ensureSpace(24); y += 8;
  pdf.setDrawColor(170, 184, 195); pdf.line(left, y, left + 65, y); y += 5;
  pdf.setFont('helvetica', 'normal'); pdf.setFontSize(8); pdf.setTextColor(100, 113, 126);
  pdf.text(type === 'prescription' ? 'Prescribing clinician' : 'Authorized hospital representative', left, y);
  y += 10;
  pdf.setFontSize(7.5);
  pdf.text('This document is generated from the patient portal record. Contact the hospital if any detail needs correction.', left, y);
  footer();
  pdf.save(`${safeFilename(record.patient_name)}-${safeFilename(record.title || record.medicine || record.description || type)}-${safeFilename(documentId)}.pdf`);
}
