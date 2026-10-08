import { useState } from 'react';
import { Settings, Users, ClipboardList, ShieldCheck, Loader2, AlertCircle } from 'lucide-react';
import { useCaseAudit } from '@/services/workflow';
import StatusBadge from '@/components/StatusBadge';

const ROLES = [
  {
    name: 'admin',
    description: 'Full system access — user management, agent config, audit logs, all workflows',
    access: ['All routes', 'Agent configuration', 'User management', 'Audit logs'],
  },
  {
    name: 'risk_analyst',
    description: 'Risk and fraud workflow access, customer explorer, analytics',
    access: ['Dashboard', 'Cases (risk/fraud)', 'Customers', 'Analytics'],
  },
  {
    name: 'fraud_investigator',
    description: 'Fraud cases and evidence review, limited customer access',
    access: ['Dashboard', 'Cases (fraud)', 'Customers', 'Analytics'],
  },
  {
    name: 'compliance_officer',
    description: 'Compliance workflow, transaction monitoring, AML flags',
    access: ['Dashboard', 'Cases (compliance)', 'Customers'],
  },
];

export default function Admin() {
  const [caseIdInput, setCaseIdInput] = useState('');
  const [fetchCaseId, setFetchCaseId] = useState('');

  const { data: auditEvents = [], isLoading: loadingAudit, error: auditError } = useCaseAudit(fetchCaseId);

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-12">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Admin Panel</h1>
        <p className="text-sm text-neutral-500 mt-1">System configuration and audit access</p>
      </div>

      {/* System Info */}
      <section className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <Settings className="w-5 h-5 text-blue-400" />
          <h2 className="text-base font-semibold text-white">System Info</h2>
        </div>
        <dl className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Environment', value: 'Development' },
            { label: 'Backend', value: 'FastAPI 0.115.6' },
            { label: 'Frontend', value: 'React 18 + Vite' },
            { label: 'LLM Provider', value: 'Gemini (LiteLLM)' },
          ].map(({ label, value }) => (
            <div key={label} className="bg-neutral-800/50 rounded-lg p-4">
              <dt className="text-xs text-neutral-500 mb-1">{label}</dt>
              <dd className="text-sm font-medium text-white">{value}</dd>
            </div>
          ))}
        </dl>
      </section>

      {/* User Management (stub) */}
      <section className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <Users className="w-5 h-5 text-blue-400" />
          <h2 className="text-base font-semibold text-white">User Management</h2>
        </div>
        <div className="bg-neutral-800/30 border border-neutral-700/50 rounded-lg p-6 text-center">
          <p className="text-sm text-neutral-400">
            User management requires a <code className="text-blue-400">/users</code> backend endpoint.
          </p>
          <p className="text-xs text-neutral-600 mt-2">Planned for Phase 6.</p>
        </div>
      </section>

      {/* Audit Log Viewer */}
      <section className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <ClipboardList className="w-5 h-5 text-blue-400" />
          <h2 className="text-base font-semibold text-white">Audit Log Viewer</h2>
        </div>
        <div className="flex gap-3 mb-6">
          <input
            type="text"
            placeholder="Enter Case UUID…"
            value={caseIdInput}
            onChange={(e) => setCaseIdInput(e.target.value)}
            className="flex-1 bg-neutral-800 border border-neutral-700 rounded-lg px-4 py-2.5 text-sm text-white placeholder-neutral-600 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
          />
          <button
            onClick={() => setFetchCaseId(caseIdInput.trim())}
            disabled={!caseIdInput.trim()}
            className="bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white px-4 py-2.5 rounded-lg text-sm font-medium transition-colors"
          >
            Fetch Audit
          </button>
        </div>

        {loadingAudit && fetchCaseId && (
          <div className="flex justify-center py-8">
            <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
          </div>
        )}

        {auditError && fetchCaseId && (
          <div className="flex items-center gap-2 text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg p-4">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            Could not load audit events. Check the case ID.
          </div>
        )}

        {!loadingAudit && fetchCaseId && auditEvents.length === 0 && !auditError && (
          <p className="text-center text-sm text-neutral-500 py-8">No audit events found for this case.</p>
        )}

        {auditEvents.length > 0 && (
          <div className="divide-y divide-neutral-800 border border-neutral-800 rounded-lg overflow-hidden">
            {auditEvents.map((evt, i) => (
              <div key={i} className="p-4 hover:bg-neutral-800/20 transition-colors">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold text-neutral-400 uppercase tracking-widest">{evt.actor_id}</span>
                  <span className="text-xs text-neutral-600 font-mono">
                    {new Date(evt.created_at).toLocaleString()}
                  </span>
                </div>
                <p className="text-sm text-neutral-300">{evt.action}</p>
                {evt.changes && Object.keys(evt.changes).length > 0 && (
                  <pre className="mt-2 text-xs text-neutral-600 bg-neutral-950 rounded p-2 overflow-x-auto">
                    {JSON.stringify(evt.changes, null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* RBAC Role Reference */}
      <section className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <ShieldCheck className="w-5 h-5 text-blue-400" />
          <h2 className="text-base font-semibold text-white">RBAC Role Reference</h2>
        </div>
        <div className="space-y-3">
          {ROLES.map((role) => (
            <div key={role.name} className="bg-neutral-800/40 border border-neutral-700/40 rounded-lg p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <StatusBadge value={role.name} />
                    <p className="text-xs text-neutral-500">{role.description}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {role.access.map((a) => (
                      <span key={a} className="text-xs bg-neutral-700/50 text-neutral-400 px-2 py-0.5 rounded">
                        {a}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
