interface StatusBadgeProps {
  value: string;
  type?: 'case' | 'severity' | 'kyc' | 'generic';
  className?: string;
}

const CASE_STATUS: Record<string, string> = {
  created: 'bg-neutral-500/10 text-neutral-600 dark:text-neutral-400 border-neutral-500/20',
  ai_processing: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20',
  ai_evaluated: 'bg-violet-500/10 text-violet-600 dark:text-violet-400 border-violet-500/20',
  pending_review: 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-500/20',
  in_review: 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20',
  human_decided: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
  escalated: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20',
  closed: 'bg-neutral-700/10 text-neutral-600 dark:text-neutral-500 border-neutral-700/20',
};

const SEVERITY: Record<string, string> = {
  critical: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20',
  high: 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20',
  medium: 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-500/20',
  low: 'bg-neutral-500/10 text-neutral-600 dark:text-neutral-400 border-neutral-500/20',
};

const KYC: Record<string, string> = {
  verified: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
  pending: 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-500/20',
  expired: 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20',
  flagged: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20',
};

export default function StatusBadge({ value, type = 'generic', className = '' }: StatusBadgeProps) {
  const key = value?.toLowerCase().replace(/ /g, '_');
  let color = 'bg-neutral-500/10 text-neutral-400 border-neutral-500/20';

  if (type === 'case') color = CASE_STATUS[key] ?? color;
  else if (type === 'severity') color = SEVERITY[key] ?? color;
  else if (type === 'kyc') color = KYC[key] ?? color;

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border uppercase tracking-wide ${color} ${className}`}
    >
      {value?.replace(/_/g, ' ')}
    </span>
  );
}
