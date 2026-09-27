import React from 'react';
import '../pages/LandingPage.css';
import './AuthPageLayout.css';

export function AuthPageLayout({ children }) {
  return (
    <main className="landing-page auth-page">
      <div className="landing-shell auth-shell">
        <section className="auth-layout">
          <section className="auth-panel">{children}</section>
        </section>
        <footer className="auth-footer"><span>METROHEALTH CARE</span><span>Appointments · Records · Support</span></footer>
      </div>
    </main>
  );
}
