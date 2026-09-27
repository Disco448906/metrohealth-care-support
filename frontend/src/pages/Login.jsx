import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Lock, Mail, ArrowRight, ShieldCheck, User, Stethoscope } from 'lucide-react';
import { AuthPageLayout } from '../components/AuthPageLayout';

const demoAccounts = {
  customer: { email: 'john.doe@example.com', password: 'Password123!', label: 'patient' },
  doctor: { email: 'doctor.ravi@metrohealth.org', password: 'Password123!', label: 'doctor' },
  admin: { email: 'admin@metrohealth.org', password: 'Password123!', label: 'staff' },
};

export const Login = ({ doctorMode = false }) => {
  const [selectedRole, setSelectedRole] = useState(doctorMode ? 'doctor' : 'customer');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const { login, logout } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const user = await login(email, password);
      if (user.role !== selectedRole) {
        logout();
        setError(`This account is not registered as a ${selectedRole === 'customer' ? 'patient' : selectedRole}. Please choose the correct sign-in option.`);
        return;
      }
      if (user.role === 'admin') {
        navigate('/admin');
      } else if (user.role === 'doctor') {
        navigate('/doctor');
      } else {
        navigate('/dashboard');
      }
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Invalid email or password credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = () => {
    const account = demoAccounts[selectedRole];
    setEmail(account.email);
    setPassword(account.password);
  };

  return (
    <AuthPageLayout>
      <div className="auth-panel-heading">
        <span className="auth-panel-kicker">SECURE PORTAL ACCESS</span>
        <h2>Sign in to MetroHealth</h2>
        <p>Choose your account type, then continue.</p>
      </div>

        <div className="auth-role-grid" role="group" aria-label="Choose account type">
          {[
            { role: 'customer', label: 'Patient', icon: User },
            { role: 'doctor', label: 'Doctor', icon: Stethoscope },
            { role: 'admin', label: 'Admin', icon: ShieldCheck },
          ].map(({ role, label, icon: Icon }) => (
            <button
              key={role}
              type="button"
              onClick={() => { setSelectedRole(role); setError(''); setEmail(''); setPassword(''); }}
              aria-pressed={selectedRole === role}
              className={`auth-role-button ${selectedRole === role ? 'is-selected' : ''}`}
            >
              <Icon aria-hidden="true" />{label}
            </button>
          ))}
        </div>

        {error && (
          <div role="alert" className="auth-error">
            {error}
          </div>
        )}

        <div className="auth-demo">
          <div>
            <strong>Trying the demo?</strong>
            <p>Fill in a sample {demoAccounts[selectedRole].label} account.</p>
          </div>
          <button type="button" onClick={handleQuickLogin}>
            Use demo account
          </button>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <div>
            <label htmlFor="login-email" className="auth-field-label">Email address</label>
            <div className="auth-input-wrap">
              <Mail aria-hidden="true" />
              <input
                id="login-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@example.com"
                autoComplete="email"
                className="auth-input"
              />
            </div>
          </div>

          <div>
            <label htmlFor="login-password" className="auth-field-label">Password</label>
            <div className="auth-input-wrap">
              <Lock aria-hidden="true" />
              <input
                id="login-password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
                className="auth-input"
              />
            </div>
          </div>

          <button type="submit" disabled={loading} className="auth-submit">
            <span>{loading ? 'Signing in…' : 'Sign in'}</span>
            <ArrowRight aria-hidden="true" className="h-4 w-4" />
          </button>
        </form>

        <div className="auth-panel-footer">
          {selectedRole === 'customer' ? (
            <>
              Don't have an account yet?{' '}
              <Link to="/register">Create account</Link>
            </>
          ) : selectedRole === 'doctor' ? 'Doctor account access' : 'Authorized staff access'}
        </div>
    </AuthPageLayout>
  );
};
