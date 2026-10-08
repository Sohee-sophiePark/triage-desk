import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { DEMO, PERSONAS } from '../demo';
import { ShieldAlert, Eye, EyeOff } from 'lucide-react';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { login, switchPersona } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      // Need to send as x-www-form-urlencoded because OAuth2PasswordRequestForm expects it
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const response = await api.post('/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      login(response.data.access_token);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'An unexpected error occurred.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-neutral-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex flex-col items-center">
          <ShieldAlert className="h-12 w-12 text-blue-500 mb-4" />
          <h2 className="text-center text-3xl font-extrabold text-white">
            Triage Desk
          </h2>
          <p className="mt-2 text-center text-sm text-neutral-400">
            Operations case management with AI triage
          </p>
        </div>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-neutral-900 py-8 px-4 shadow sm:rounded-lg sm:px-10 border border-neutral-800">
          {DEMO ? (
            <div className="space-y-3">
              <p className="text-sm text-neutral-300">Choose a persona. No sign-in needed in this demo.</p>
              {PERSONAS.map((p) => (
                <button
                  key={p.role}
                  onClick={() => { switchPersona(p.role); navigate(p.home); }}
                  className="w-full py-2 px-4 rounded-md text-sm font-medium text-white bg-blue-600 hover:bg-blue-500"
                >
                  {p.label}
                </button>
              ))}
            </div>
          ) : (
          <form className="space-y-6" onSubmit={handleLogin}>
            <div>
              <label className="block text-sm font-medium text-neutral-300">
                Email / Username
              </label>
              <div className="mt-1">
                <input
                  type="text"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="appearance-none block w-full px-3 py-2 border border-neutral-700 bg-neutral-800 rounded-md shadow-sm placeholder-neutral-500 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-white"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-300">
                Password
              </label>
              <div className="mt-1 relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="appearance-none block w-full px-3 py-2 pr-10 border border-neutral-700 bg-neutral-800 rounded-md shadow-sm placeholder-neutral-500 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-white"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute inset-y-0 right-0 flex items-center pr-3 text-neutral-500 hover:text-neutral-300 transition-colors"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {error && (
              <div className="text-red-500 text-sm bg-red-900/20 p-3 rounded-md border border-red-900/50">
                {error}
              </div>
            )}

            <div>
              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {loading ? 'Authenticating...' : 'Sign in'}
              </button>
            </div>
          </form>
          )}
        </div>
      </div>
    </div>
  );
};

export default Login;
