import React, { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  LineChart,
  Line,
  CartesianGrid,
} from 'recharts';
import { AlertTriangle, ArrowUpRight, Loader2 } from 'lucide-react';
import { useWorkflowCases } from '@/services/workflow';
import { useAnalyticsSummary } from '@/services/analytics';
import { useChartTheme } from '@/hooks/useChartTheme';
import StatusBadge from '@/components/StatusBadge';

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">
        {title}
      </h3>
      {children}
    </div>
  );
}

function KpiChip({ label, value, color }: { label: string; value: number; color: string }) {
  const map: Record<string, string> = {
    red: 'text-red-700 dark:text-red-400 bg-red-500/10',
    yellow: 'text-yellow-800 dark:text-yellow-400 bg-yellow-500/10',
    orange: 'text-orange-800 dark:text-orange-400 bg-orange-500/10',
    violet: 'text-violet-700 dark:text-violet-400 bg-violet-500/10',
  };
  return (
    <div className={`rounded-xl p-4 ${map[color] ?? map.red} border border-current/10`}>
      <p className="text-2xl font-bold tabular-nums">{value}</p>
      <p className="text-xs mt-0.5">{label}</p>
    </div>
  );
}

export default function RiskFraud() {
  const navigate = useNavigate();
  const ct = useChartTheme();

  const { data: allCases = [], isLoading: casesLoading } = useWorkflowCases({
    limit: '200',
  } as Record<string, string>);
  const { data: summary, isLoading: summaryLoading } = useAnalyticsSummary();

  const cases = useMemo(
    () => allCases.filter((c) => c.case_type === 'fraud' || c.case_type === 'risk'),
    [allCases]
  );

  const pending = useMemo(() => cases.filter((c) => c.status === 'pending_review').length, [cases]);
  const aiEvaluated = useMemo(() => cases.filter((c) => c.status === 'ai_evaluated').length, [cases]);
  const escalated = useMemo(() => cases.filter((c) => c.status === 'escalated').length, [cases]);

  const incidentTypeData = Object.entries(summary?.incident_type_distribution ?? {}).map(
    ([name, value]) => ({
      name: name.replace(/_/g, ' '),
      value,
    })
  );
  const severityData = Object.entries(summary?.incident_severity_distribution ?? {}).map(
    ([name, value]) => ({
      name: name.charAt(0).toUpperCase() + name.slice(1),
      value,
    })
  );
  const caseTrend = summary?.monthly_cases ?? [];
  const SEV_COLORS: Record<string, string> = {
    Low: ct.colors[1],
    Medium: ct.colors[2],
    High: ct.colors[4],
    Critical: ct.colors[4],
  };

  const loading = casesLoading || summaryLoading;

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Risk & Fraud</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {cases.length} active cases · {summary?.total_incidents ?? 0} total incidents
        </p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiChip label="Total Cases" value={cases.length} color="red" />
        <KpiChip label="Pending Review" value={pending} color="yellow" />
        <KpiChip label="AI Evaluated" value={aiEvaluated} color="violet" />
        <KpiChip label="Escalated" value={escalated} color="orange" />
      </div>

      {/* Charts */}
      {!loading && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <ChartCard title="Cases Over Time">
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={caseTrend} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <CartesianGrid stroke={ct.grid} strokeDasharray="3 3" />
                <XAxis
                  dataKey="month"
                  tick={{ fill: ct.muted, fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: ct.muted, fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: ct.tooltip.bg,
                    border: `1px solid ${ct.tooltip.border}`,
                    borderRadius: '8px',
                    color: ct.tooltip.text,
                    fontSize: 12,
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke={ct.colors[4]}
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Incident Type Breakdown">
            <ResponsiveContainer width="100%" height={160}>
              <BarChart
                data={incidentTypeData}
                layout="vertical"
                margin={{ top: 0, right: 4, left: 0, bottom: 0 }}
              >
                <XAxis type="number" tick={{ fill: ct.muted, fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fill: ct.muted, fontSize: 9 }}
                  axisLine={false}
                  tickLine={false}
                  width={80}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: ct.tooltip.bg,
                    border: `1px solid ${ct.tooltip.border}`,
                    borderRadius: '8px',
                    color: ct.tooltip.text,
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="value" fill={ct.colors[4]} radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Severity Distribution">
            <ResponsiveContainer width="100%" height={160}>
              <PieChart>
                <Pie
                  data={severityData}
                  cx="50%"
                  cy="50%"
                  innerRadius={38}
                  outerRadius={62}
                  dataKey="value"
                  isAnimationActive={false}
                >
                  {severityData.map((entry, i) => (
                    <Cell key={i} fill={SEV_COLORS[entry.name] ?? ct.colors[i % ct.colors.length]} />
                  ))}
                </Pie>
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 10, color: ct.muted }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: ct.tooltip.bg,
                    border: `1px solid ${ct.tooltip.border}`,
                    borderRadius: '8px',
                    color: ct.tooltip.text,
                    fontSize: 12,
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>
      )}

      {/* Case list */}
      <div className="bg-card border border-border rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-border flex items-center justify-between">
          <h2 className="text-sm font-semibold text-foreground">Investigation Queue</h2>
          {casesLoading && <Loader2 className="w-4 h-4 text-primary animate-spin" />}
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-border">
            <thead className="bg-muted/50">
              <tr>
                {['Case ID', 'Type', 'Status', 'Created', ''].map((h) => (
                  <th key={h} className="px-5 py-3.5 text-left text-xs font-semibold text-muted-foreground tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {cases.map((c) => (
                <tr key={c.id} className="hover:bg-muted/30 transition-colors group">
                  <td className="px-5 py-3.5 text-xs font-mono text-muted-foreground">{c.id.slice(0, 8)}</td>
                  <td className="px-5 py-3.5 text-sm text-foreground capitalize">{c.case_type}</td>
                  <td className="px-5 py-3.5">
                    <StatusBadge value={c.status} type="case" />
                  </td>
                  <td className="px-5 py-3.5 text-sm text-muted-foreground">
                    {new Date(c.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <button
                      onClick={() => navigate(`/cases/${c.id}`)}
                      className="inline-flex items-center text-xs font-semibold text-primary hover:text-primary/80 transition-colors"
                    >
                      Investigate
                      <ArrowUpRight className="w-3 h-3 ml-1 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
                    </button>
                  </td>
                </tr>
              ))}
              {!casesLoading && cases.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-5 py-10 text-center text-sm text-muted-foreground">
                    No risk or fraud cases found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
