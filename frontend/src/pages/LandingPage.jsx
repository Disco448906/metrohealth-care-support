import React from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  ArrowUpRight,
  CalendarDays,
  CheckCircle2,
  ClipboardCheck,
  FileText,
  HeartPulse,
  MessageCircle,
  CircleHelp,
  ShieldCheck,
  Stethoscope,
  UserRound,
} from 'lucide-react';
import './LandingPage.css';

const portalCards = [
  {
    eyebrow: 'FOR PATIENTS',
    title: 'Your care, in one place',
    description: 'Manage appointments, find your records, and keep up with support requests.',
    icon: UserRound,
    to: '/login',
    action: 'Patient sign in',
    theme: 'patient',
  },
  {
    eyebrow: 'FOR DOCTORS',
    title: 'A clearer view of your day',
    description: 'Review your schedule and access records for patients assigned to your care.',
    icon: Stethoscope,
    to: '/doctor-login',
    action: 'Doctor sign in',
    theme: 'doctor',
  },
  {
    eyebrow: 'FOR SUPPORT TEAMS',
    title: 'Keep every request moving',
    description: 'Review service requests, coordinate follow-up, and share clear updates.',
    icon: ShieldCheck,
    to: '/login',
    action: 'Staff sign in',
    theme: 'support',
  },
];

const careHighlights = [
  {
    icon: CalendarDays,
    title: 'Appointments',
    detail: 'See visits and manage changes',
  },
  {
    icon: FileText,
    title: 'Records & bills',
    detail: 'Find important details together',
  },
  {
    icon: MessageCircle,
    title: 'Support requests',
    detail: 'Follow updates from the team',
  },
];

export function LandingPage() {
  return (
    <main className="landing-page">
      <div className="landing-shell">
        <section className="landing-hero" aria-labelledby="landing-title">
          <div className="landing-copy">
            <div className="landing-eyebrow">
              <span className="landing-eyebrow-mark"><HeartPulse aria-hidden="true" /></span>
              <span>CARE SUPPORT, MADE SIMPLE</span>
            </div>

            <h1 id="landing-title">
              Feel more at ease about <span>what comes next.</span>
            </h1>

            <p className="landing-intro">
              A clear place to manage appointments, find hospital information, and stay up to date on your support requests.
            </p>

            <div className="landing-actions">
              <Link to="/register" className="landing-button landing-button-primary">
                Create a patient account <ArrowRight aria-hidden="true" />
              </Link>
              <Link to="/login" className="landing-button landing-button-secondary">
                Sign in <ArrowUpRight aria-hidden="true" />
              </Link>
            </div>

            <div className="landing-reassurance">
              <CheckCircle2 aria-hidden="true" />
              <span>One convenient home for your care support</span>
            </div>
          </div>

          <div className="landing-art" aria-label="Appointments, records, and support in one patient portal">
            <div className="landing-art-halo landing-art-halo-one" />
            <div className="landing-art-halo landing-art-halo-two" />
            <div className="landing-art-orbit landing-art-orbit-one" />
            <div className="landing-art-orbit landing-art-orbit-two" />

            <div className="landing-preview">
              <div className="landing-preview-topline">
                <div className="landing-preview-brand">
                  <span className="landing-preview-brand-icon"><HeartPulse aria-hidden="true" /></span>
                  <span>METROHEALTH <b>CARE</b></span>
                </div>
                <span className="landing-preview-status"><i /> YOUR PORTAL</span>
              </div>

              <div className="landing-preview-heading">
                <span className="landing-preview-kicker">A LITTLE MORE CLARITY</span>
                <h2>Your care, at a glance.</h2>
                <p>The essentials are easy to find when you need them.</p>
              </div>

              <div className="landing-preview-list">
                {careHighlights.map(({ icon: Icon, title, detail }, index) => (
                  <div className="landing-preview-row" key={title}>
                    <span className={`landing-preview-row-icon landing-preview-row-icon-${index + 1}`}>
                      <Icon aria-hidden="true" />
                    </span>
                    <span className="landing-preview-row-copy">
                      <b>{title}</b>
                      <small>{detail}</small>
                    </span>
                    <ArrowUpRight className="landing-preview-row-arrow" aria-hidden="true" />
                  </div>
                ))}
              </div>

              <div className="landing-preview-foot">
                <span className="landing-preview-foot-icon"><ShieldCheck aria-hidden="true" /></span>
                <span>Support that keeps you in the loop.</span>
              </div>
            </div>

            <div className="landing-float-card landing-float-card-top">
              <span className="landing-float-icon landing-float-icon-teal"><CalendarDays aria-hidden="true" /></span>
              <span><b>Appointments</b><small>Easy to keep track</small></span>
            </div>
            <div className="landing-float-card landing-float-card-bottom">
              <span className="landing-float-icon landing-float-icon-peach"><MessageCircle aria-hidden="true" /></span>
              <span><b>Here to help</b><small>Find your next step</small></span>
              <span className="landing-float-arrow"><ArrowRight aria-hidden="true" /></span>
            </div>
          </div>
        </section>

        <section className="landing-routing" aria-labelledby="routing-heading">
          <div className="landing-routing-heading">
            <p className="landing-section-kicker">START WITH THE CARE ASSISTANT</p>
            <h2 id="routing-heading">Answers in chat. Staff follow-through when needed.</h2>
            <p>The assistant handles supported questions and guided tasks. If a person needs to investigate or take action, it creates a request the support team can track.</p>
          </div>

          <div className="landing-routing-grid">
            <article className="landing-routing-card landing-routing-chat">
              <div className="landing-routing-card-heading">
                <span className="landing-routing-icon"><CircleHelp aria-hidden="true" /></span>
                <span className="landing-routing-label">CARE ASSISTANT</span>
              </div>
              <h3>Handled right in chat</h3>
              <ul className="landing-routing-list">
                <li>Hospital hours, location, contact details, refund policy, and how to access reports.</li>
                <li>Check appointment availability, book, reschedule, or cancel a visit.</li>
                <li>Look up your own appointments, reports, prescriptions, and bills when signed in.</li>
              </ul>
              <p className="landing-routing-footnote">If it can’t find a verified answer, it can create a staff follow-up request.</p>
            </article>

            <article className="landing-routing-card landing-routing-staff">
              <div className="landing-routing-card-heading">
                <span className="landing-routing-icon"><ClipboardCheck aria-hidden="true" /></span>
                <span className="landing-routing-label">ADMIN SUPPORT</span>
              </div>
              <h3>For requests that need review</h3>
              <div className="landing-routing-examples">
                <div><b>Billing & refunds</b><span>Incorrect charges or a missing refund</span></div>
                <div><b>Insurance</b><span>Claim questions or disputes</span></div>
                <div><b>Service & staff</b><span>Long waits or service concerns</span></div>
                <div><b>Accounts & appointments</b><span>Portal access or bookings needing staff follow-up</span></div>
                <div><b>Privacy & security</b><span>Concerns flagged for human review</span></div>
                <div><b>General information</b><span>Questions the assistant can’t verify</span></div>
              </div>
              <div className="landing-routing-process" aria-label="Admin request process">
                <span><i>1</i>Request created</span>
                <ArrowRight aria-hidden="true" />
                <span><i>2</i>Staff assigned</span>
                <ArrowRight aria-hidden="true" />
                <span><i>3</i>Update recorded</span>
              </div>
              <p className="landing-routing-footnote">Admins assign the request, update its status, and add a resolution note. You can follow progress in Support Requests. The app tracks refunds; it doesn’t process payments or issue them.</p>
            </article>
          </div>

          <p className="landing-safety-note"><ShieldCheck aria-hidden="true" /><span>Medical concerns are routed for clinical review. The assistant doesn’t diagnose or change treatment, and it doesn’t page clinicians. For emergencies, contact local emergency services.</span></p>
        </section>

        <section className="landing-portals" aria-labelledby="portal-heading">
          <div className="landing-section-heading">
            <div>
              <p className="landing-section-kicker">A WELCOME PLACE FOR EVERY ROLE</p>
              <h2 id="portal-heading">Choose your portal</h2>
              <p>Sign in to find the tools and updates for your role.</p>
            </div>
            <span className="landing-section-note"><ShieldCheck aria-hidden="true" /> Connected care, made clearer</span>
          </div>

          <div className="landing-portal-grid">
            {portalCards.map(({ eyebrow, title, description, icon: Icon, to, action, theme }) => (
              <article className={`landing-portal-card landing-portal-card-${theme}`} key={eyebrow}>
                <div className="landing-portal-card-top">
                  <span className="landing-portal-icon"><Icon aria-hidden="true" /></span>
                  <span className="landing-portal-eyebrow">{eyebrow}</span>
                </div>
                <h3>{title}</h3>
                <p>{description}</p>
                <Link to={to} className="landing-portal-link">
                  {action}<ArrowRight aria-hidden="true" />
                </Link>
              </article>
            ))}
          </div>

          <div className="landing-emergency-note">
            <span className="landing-emergency-mark"><HeartPulse aria-hidden="true" /></span>
            <p>This service helps with customer care and support requests. For medical emergencies, contact local emergency services.</p>
          </div>
        </section>
      </div>
    </main>
  );
}
