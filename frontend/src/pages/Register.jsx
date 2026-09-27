import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { User, Mail, Lock, Phone, ArrowRight } from 'lucide-react';
import { AuthPageLayout } from '../components/AuthPageLayout';

export const Register = () => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [phone, setPhone] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await register({ name, email, password, phone, role: 'customer' });
      navigate('/dashboard');
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Registration failed. Please check inputs.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthPageLayout>
      <div className="auth-panel-heading">
        <span className="auth-panel-kicker">PATIENT PORTAL</span>
        <h2>Create your account</h2>
        <p>Enter your details to get started.</p>
      </div>

        {error && (
          <div role="alert" className="auth-error">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          <div>
            <label htmlFor="register-name" className="auth-field-label">Full name</label>
            <div className="auth-input-wrap">
              <User aria-hidden="true" />
              <input
                id="register-name"
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Jane Doe"
                autoComplete="name"
                className="auth-input"
              />
            </div>
          </div>

          <div>
            <label htmlFor="register-email" className="auth-field-label">Email address</label>
            <div className="auth-input-wrap">
              <Mail aria-hidden="true" />
              <input
                id="register-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="jane.doe@example.com"
                autoComplete="email"
                className="auth-input"
              />
            </div>
          </div>

          <div>
            <label htmlFor="register-phone" className="auth-field-label">Phone number <span className="font-normal text-slate-400">(optional)</span></label>
            <div className="auth-input-wrap">
              <Phone aria-hidden="true" />
              <input
                id="register-phone"
                type="text"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+1 (555) 000-0000"
                autoComplete="tel"
                className="auth-input"
              />
            </div>
          </div>

          <div>
            <label htmlFor="register-password" className="auth-field-label">Password</label>
            <div className="auth-input-wrap">
              <Lock aria-hidden="true" />
              <input
                id="register-password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="new-password"
                className="auth-input"
              />
            </div>
          </div>

          <button type="submit" disabled={loading} className="auth-submit">
            <span>{loading ? 'Creating account…' : 'Create patient account'}</span>
            <ArrowRight aria-hidden="true" className="h-4 w-4" />
          </button>
        </form>

        <div className="auth-panel-footer">
          Already have an account?{' '}
          <Link to="/login">Sign in</Link>
        </div>
    </AuthPageLayout>
  );
};
