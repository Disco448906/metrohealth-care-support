import React from 'react';
import { X, Smartphone, Printer } from 'lucide-react';

export const SMSNotificationModal = ({ appointment, onClose }) => {
  if (!appointment) return null;

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white rounded-3xl shadow-2xl max-w-lg w-full overflow-hidden border border-slate-200 animate-in fade-in zoom-in duration-200">
        
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Smartphone className="w-5 h-5 text-emerald-400" />
            <h3 className="font-bold text-sm">Appointment confirmation preview</h3>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-white rounded-full">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          
          {/* Visual Phone SMS Card */}
          <div className="bg-slate-100 rounded-2xl p-4 border border-slate-300 shadow-inner space-y-3">
            <div className="flex justify-between items-center text-[11px] text-slate-500 border-b border-slate-200/80 pb-2">
              <span className="font-bold text-slate-700">Message preview · {appointment.phone || 'phone not listed'}</span>
              <span>Not sent</span>
            </div>

            <div className="bg-white p-4 rounded-xl text-xs font-mono text-slate-800 leading-relaxed border border-slate-200 shadow-sm whitespace-pre-wrap">
              {appointment.sms_text || (
                `METROHEALTH APPOINTMENT NOTICE\n\nDear ${appointment.customer_name}, appointment ${appointment.id} with ${appointment.doctor_name} on ${appointment.date} at ${appointment.time_slot} is ${appointment.status || 'CONFIRMED'}.\n\nPayment status: ${appointment.payment_status || 'PENDING'} (this demo does not process payments).`
              )}
            </div>
            <p className="text-[11px] leading-5 text-slate-500">SMS delivery is not connected in this capstone. You can print this confirmation for the demo.</p>
          </div>

          {/* Digital Appointment Slip */}
          <div className="bg-medical-50/60 rounded-2xl p-5 border border-medical-200 space-y-4 text-xs">
            <div className="flex justify-between items-start">
              <div>
                <span className="text-[10px] font-bold text-medical-800 uppercase tracking-wider block">Appointment summary</span>
                <h4 className="text-base font-extrabold text-slate-900">{appointment.doctor_name}</h4>
                <p className="text-slate-600 font-medium">{appointment.department}</p>
              </div>
              <span className="font-mono font-bold text-xs bg-white text-medical-700 px-2.5 py-1 rounded-lg border border-medical-300">
                {appointment.id}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 pt-2 border-t border-medical-200/60 text-slate-700">
              <div className="space-y-1">
                <span className="text-[10px] text-slate-400 block uppercase">Date & Time</span>
                <span className="font-bold block">{appointment.date}</span>
                <span className="text-slate-600 block">{appointment.time_slot}</span>
              </div>
              <div className="space-y-1">
                <span className="text-[10px] text-slate-400 block uppercase">Location</span>
                <span className="font-bold block">{appointment.location}</span>
                <span className="text-slate-600 block">Consultation fee: ${Number(appointment.amount ?? 150).toFixed(2)}</span>
              </div>
            </div>

            <div className="flex items-center justify-between text-[11px] pt-2 border-t border-medical-200/60 font-semibold">
              <span className="text-slate-600">Payment status: {appointment.payment_status || 'PENDING'}</span>
              <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded">{appointment.status || 'CONFIRMED'}</span>
            </div>
          </div>

        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-between items-center rounded-b-3xl">
          <button
            onClick={handlePrint}
            className="px-4 py-2 bg-white border border-slate-300 text-slate-700 hover:bg-slate-100 rounded-xl text-xs font-semibold flex items-center space-x-1.5 transition-colors shadow-sm"
          >
            <Printer className="w-4 h-4" />
            <span>Print Appointment Letter</span>
          </button>
          
          <button
            onClick={onClose}
            className="px-5 py-2 bg-medical-600 text-white hover:bg-medical-700 rounded-xl text-xs font-bold transition-colors shadow-sm"
          >
            Done
          </button>
        </div>

      </div>
    </div>
  );
};
