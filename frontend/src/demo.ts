/** Public demo build (VITE_DEMO=1): no login, static API snapshots, read-only. */
export const DEMO = import.meta.env.VITE_DEMO === '1';

export const PERSONAS = [
  { role: 'admin', label: 'Ops Supervisor', home: '/' },
  { role: 'fraud_investigator', label: 'Fraud Investigator', home: '/risk-fraud' },
  { role: 'risk_analyst', label: 'Risk Analyst', home: '/risk-fraud' },
  { role: 'compliance_officer', label: 'Compliance Officer', home: '/compliance' },
];

export const roleLabel = (role?: string) => PERSONAS.find((p) => p.role === role)?.label ?? role ?? '';
