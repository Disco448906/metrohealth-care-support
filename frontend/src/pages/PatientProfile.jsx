import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, CalendarDays, Mail, Phone, UserRound } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const initialsFor = (name = '') => name
  .trim()
  .split(/\s+/)
  .slice(0, 2)
  .map((part) => part[0]?.toUpperCase() || '')
  .join('') || 'P';

const formatMemberSince = (createdAt) => {
  if (!createdAt) return 'Not available';
  const date = new Date(createdAt);
  if (Number.isNaN(date.getTime())) return 'Not available';
  return new Intl.DateTimeFormat(undefined, { month: 'long', year: 'numeric' }).format(date);
};

function ProfileDetail({ icon: Icon, label, value }) {
  return (
    <div className="flex min-w-0 items-start gap-3 rounded-xl border border-slate-200 bg-slate-50/80 p-4">
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white text-medical-700 shadow-sm">
        <Icon className="h-5 w-5" aria-hidden="true" />
      </span>
      <div className="min-w-0 pt-0.5">
        <p className="text-xs font-medium text-slate-500">{label}</p>
        <p className="mt-1 break-words text-sm font-semibold text-slate-800">{value || 'Not provided'}</p>
      </div>
    </div>
  );
}

export function PatientProfile() {
  const { user } = useAuth();

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-7 sm:px-6 sm:py-10 lg:px-8">
      <Link
        to="/dashboard"
        className="inline-flex items-center gap-2 rounded-lg text-sm font-semibold text-slate-600 transition hover:text-medical-700"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Back to My care
      </Link>

      <section className="mt-5 overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm" aria-labelledby="profile-title">
        <div className="relative overflow-hidden bg-gradient-to-r from-medical-900 via-medical-800 to-teal-700 px-6 py-7 text-white sm:px-8 sm:py-9">
          <div className="pointer-events-none absolute -right-12 -top-24 h-64 w-64 rounded-full border border-white/10" />
          <div className="pointer-events-none absolute -right-2 -top-14 h-48 w-48 rounded-full border border-white/10" />
          <div className="relative flex flex-wrap items-center gap-4 sm:gap-5">
            <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl border border-white/20 bg-white/10 text-xl font-bold shadow-inner sm:h-[72px] sm:w-[72px]">
              {initialsFor(user?.name)}
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-white/70">Patient profile</p>
              <h1 id="profile-title" className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">{user?.name || 'Patient'}</h1>
              <p className="mt-1 text-sm text-white/75">Your basic account details</p>
            </div>
            <span className="ml-auto inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-semibold text-white/90">
              <UserRound className="h-3.5 w-3.5" aria-hidden="true" />
              Patient account
            </span>
          </div>
        </div>

        <div className="p-5 sm:p-8">
          <div className="mb-4">
            <h2 className="text-base font-bold text-slate-900">Account information</h2>
            <p className="mt-1 text-sm text-slate-500">These details belong to your signed-in patient account.</p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <ProfileDetail icon={UserRound} label="Patient ID" value={user?.id} />
            <ProfileDetail icon={Mail} label="Email address" value={user?.email} />
            <ProfileDetail icon={Phone} label="Phone number" value={user?.phone} />
            <ProfileDetail icon={CalendarDays} label="Member since" value={formatMemberSince(user?.created_at)} />
          </div>

          <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-5">
            <p className="text-xs text-slate-500">Need to update these details? Contact the hospital support team.</p>
            <Link to="/dashboard" className="inline-flex items-center gap-2 rounded-xl bg-medical-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-medical-800">
              Go to My care
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}

export default PatientProfile;
