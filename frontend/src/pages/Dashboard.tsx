import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AreaChart,
  Area,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import {
  Users,
  TrendingUp,
  DollarSign,
  AlertTriangle,
  Clock,
  ShieldAlert,
  Scale,
  BarChart2,
  ArrowUpRight,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { useAnalyticsSummary } from '@/services/analytics';
import { useChartTheme } from '@/hooks/useChartTheme';

function fmt(n: number): string {
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(1)}B`;
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

function fmtNum(n: number): string {
  return n.toLocaleString();
}

interface KpiCardProps {
  label: string;
  value: string;
  sub?: string;
  icon: React.ElementType;
  color: string;
  trend?: Array<{ month: string; v: number }>;
}

function KpiCard({ label, value, sub, icon: Icon, color, trend }: KpiCardProps) {
  const ct = useChartTheme();
  const colorMap: Record<string, string> = {
    blue: 'text-blue-600 dark:text-blue-400 bg-blue-500/10',
    emerald: 'text-emerald-600 dark:text-emerald-400 bg-emerald-500/10',
    amber: 'text-amber-600 dark:text-amber-400 bg-amber-500/10',
    red: 'text-red-600 dark:text-red-400 bg-red-500/10',
    violet: 'text-violet-600 dark:text-violet-400 bg-violet-500/10',
    orange: 'text-orange-600 dark:text-orange-400 bg-orange-500/10',
  };
  const strokeMap: Record<string, string> = {
    blue: '#3b82f6',
    emerald: '#10b981',
    amber: '#f59e0b',
    red: '#ef4444',
    violet: '#8b5cf6',
    orange: '#f97316',
  };
  const cls = colorMap[color] ?? colorMap.blue;
  const stroke = strokeMap[color] ?? strokeMap.blue;

  return (
    <div className="bg-card border border-border rounded-xl p-5 flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">{label}</p>
          <p className="text-2xl font-bold text-foreground tabular-nums mt-1">{value}</p>
          {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
        </div>
        <div className={`p-2.5 rounded-lg ${cls}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      {trend && trend.length > 1 && (
        <div className="h-10 -mx-1">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={trend} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={`grad-${color}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={stroke} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={stroke} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="v"
                stroke={stroke}
                strokeWidth={1.5}
                fill={`url(#grad-${color})`}
                dot={false}
                isAnimationActive={false}
              />
              <Tooltip
                content={() => null}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

interface SectionCardProps {
  title: string;
  description: string;
  icon: React.ElementType;
  href: string;
  stats: Array<{ label: string; value: string | number }>;
  color: string;
}

function SectionCard({ title, description, icon: Icon, href, stats, color }: SectionCardProps) {
  const navigate = useNavigate();
  const colorMap: Record<string, string> = {
    blue: 'text-blue-600 dark:text-blue-400 bg-blue-500/10 border-blue-500/20',
    red: 'text-red-600 dark:text-red-400 bg-red-500/10 border-red-500/20',
    violet: 'text-violet-600 dark:text-violet-400 bg-violet-500/10 border-violet-500/20',
    emerald: 'text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  };
  const cls = colorMap[color] ?? colorMap.blue;

  return (
    <button
      onClick={() => navigate(href)}
      className="bg-card border border-border rounded-xl p-6 text-left hover:border-primary/40 hover:shadow-md transition-all group w-full"
    >
      <div className="flex items-start justify-between mb-4">
        <div className={`p-3 rounded-lg border ${cls}`}>
          <Icon className="w-5 h-5" />
        </div>
        <ArrowUpRight className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
      </div>
      <h3 className="text-base font-semibold text-foreground mb-1">{title}</h3>
      <p className="text-xs text-muted-foreground mb-4 leading-relaxed">{description}</p>
      <div className="grid grid-cols-2 gap-3 pt-3 border-t border-border">
        {stats.map((s) => (
          <div key={s.label}>
            <p className="text-lg font-bold text-foreground tabular-nums">{s.value}</p>
            <p className="text-xs text-muted-foreground">{s.label}</p>
          </div>
        ))}
      </div>
    </button>
  );
}

export default function Dashboard() {
  const { data, isLoading, error } = useAnalyticsSummary();
  const ct = useChartTheme();

  if (isLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-8 w-8 text-primary animate-spin" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-6 flex items-center gap-3 text-destructive">
        <AlertCircle className="w-5 h-5 flex-shrink-0" />
        <p>Failed to load dashboard data.</p>
      </div>
    );
  }

  const aumTrend = data.monthly_aum.map((d) => ({ month: d.month, v: d.aum }));
  const txTrend = data.monthly_transaction_volume.slice(-6).map((d) => ({ month: d.month, v: d.volume }));
  const caseTrend = data.monthly_cases.map((d) => ({ month: d.month, v: d.count }));
  const totalCases = Object.values(data.cases_by_type).reduce((a, b) => a + b, 0);

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Overview</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Portfolio snapshot · {new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
        </p>
      </div>

      {/* Headline KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <KpiCard
          label="Total AUM"
          value={fmt(data.total_aum)}
          icon={TrendingUp}
          color="blue"
          trend={aumTrend}
        />
        <KpiCard
          label="Est. Revenue"
          value={fmt(data.estimated_revenue)}
          sub="fee-based"
          icon={DollarSign}
          color="emerald"
        />
        <KpiCard
          label="Clients"
          value={fmtNum(data.total_customers)}
          sub={`avg score ${data.avg_credit_score}`}
          icon={Users}
          color="violet"
        />
        <KpiCard
          label="Active Cases"
          value={fmtNum(totalCases)}
          icon={BarChart2}
          color="amber"
          trend={caseTrend}
        />
        <KpiCard
          label="Pending Review"
          value={fmtNum(data.pending_review_cases)}
          icon={Clock}
          color="orange"
        />
        <KpiCard
          label="Escalated"
          value={fmtNum(data.escalated_cases)}
          icon={AlertTriangle}
          color="red"
        />
      </div>

      {/* Section navigation cards */}
      <div>
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4">
          Operations
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          <SectionCard
            title="Customers"
            description="Client portfolio, AUM breakdown, credit health, and KYC pipeline."
            icon={Users}
            href="/customers"
            color="blue"
            stats={[
              { label: 'Total clients', value: fmtNum(data.total_customers) },
              { label: 'Total AUM', value: fmt(data.total_aum) },
            ]}
          />
          <SectionCard
            title="Risk & Fraud"
            description="Active fraud alerts, risk incidents, severity distribution, and investigation queue."
            icon={ShieldAlert}
            href="/risk-fraud"
            color="red"
            stats={[
              { label: 'Total incidents', value: fmtNum(data.total_incidents) },
              { label: 'Pending review', value: fmtNum(data.pending_review_cases) },
            ]}
          />
          <SectionCard
            title="Compliance"
            description="AML flags, regulatory review queue, SAR pipeline, and decision history."
            icon={Scale}
            href="/compliance"
            color="violet"
            stats={[
              { label: 'Compliance cases', value: fmtNum(data.cases_by_type?.compliance ?? 0) },
              { label: 'Escalated', value: fmtNum(data.escalated_cases) },
            ]}
          />
          <SectionCard
            title="Analytics"
            description="Cross-portfolio metrics, AI pipeline quality, and workflow throughput."
            icon={BarChart2}
            href="/analytics"
            color="emerald"
            stats={[
              { label: 'Total cases', value: fmtNum(totalCases) },
              { label: 'Transaction vol.', value: fmt(txTrend.reduce((a, d) => a + d.v, 0)) },
            ]}
          />
        </div>
      </div>
    </div>
  );
}
