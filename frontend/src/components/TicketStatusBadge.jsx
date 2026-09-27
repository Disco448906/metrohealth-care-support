import React from 'react';

export const StatusBadge = ({ status }) => {
  const styles = {
    OPEN: "bg-amber-100 text-amber-800 border-amber-300",
    ASSIGNED: "bg-blue-100 text-blue-800 border-blue-300",
    IN_PROGRESS: "bg-indigo-100 text-indigo-800 border-indigo-300",
    RESOLVED: "bg-emerald-100 text-emerald-800 border-emerald-300",
    CLOSED: "bg-slate-100 text-slate-700 border-slate-300",
    AUTO_RESOLVED: "bg-sky-100 text-sky-800 border-sky-300",
    TICKET_CREATED: "bg-purple-100 text-purple-800 border-purple-300"
  };

  return (
    <span className={`px-2.5 py-1 text-xs font-semibold rounded-full border ${styles[status] || styles.OPEN}`}>
      {status ? status.replace('_', ' ') : 'OPEN'}
    </span>
  );
};

export const SeverityBadge = ({ severity }) => {
  const styles = {
    LOW: "bg-emerald-50 text-emerald-700 border-emerald-200",
    MEDIUM: "bg-amber-50 text-amber-700 border-amber-200",
    HIGH: "bg-orange-100 text-orange-800 border-orange-300 font-semibold",
    CRITICAL: "bg-rose-100 text-rose-800 border-rose-400 font-bold animate-pulse"
  };

  return (
    <span className={`px-2 py-0.5 text-xs rounded border ${styles[severity] || styles.LOW}`}>
      {severity || 'LOW'}
    </span>
  );
};

export const CategoryBadge = ({ category }) => {
  return (
    <span className="px-2 py-0.5 text-xs bg-slate-100 text-slate-700 font-medium rounded border border-slate-200 uppercase tracking-wider">
      {(category || 'GENERAL').replaceAll('_', ' ')}
    </span>
  );
};
