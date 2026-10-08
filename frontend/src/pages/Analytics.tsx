import React, { useMemo } from 'react';
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
import { Loader2 } from 'lucide-react';
import { useWorkflowCases } from '@/services/workflow';
import { useAnalyticsSummary } from '@/services/analytics';
import { useChartTheme } from '@/hooks/useChartTheme';
import StatusBadge from '@/components/StatusBadge';

const CASE_TYPES = ['fraud', 'risk', 'compliance'];

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
    blue: 'text-blue-700 dark:text-blue-400 bg-blue-500/10',
    yellow: 'text-yellow-800 dark:text-yellow-400 bg-yellow-500/10',
    violet: 'text-violet-700 dark:text-violet-400 bg-violet-500/10',
    emerald: 'text-emerald-700 dark:text-emerald-400 bg-emerald-500/10',
    red: 'text-red-700 dark:text-red-400 bg-red-500/10',
  };
  return (
    <div className={`rounded-xl p-4 ${map[color] ?? map.blue} border border-current/10`}>
      <p className="text-2xl font-bold tabular-nums">{value}</p>
      <p className="text-xs mt-0.5">{label}</p>
    </div>
  );
}

export default function Analytics() {
  const ct = useChartTheme();
  const { data: cases = [], isLoading: casesLoading } = useWorkflowCases(
    { limit: '200' } as Record<string, string>
  );
  const { data: summary, isLoading: summaryLoading } = useAnalyticsSummary();

  const metrics = useMemo(() => {
    const total = cases.length;
    const pending = cases.filter((c) => c.status === 'pending_review').length;
    const aiEvaluated = cases.filter((c) => c.status === 'ai_evaluated').length;
    const humanDecided = cases.filter((c) => c.status === 'human_decided').length;
    const escalated = cases.filter((c) => c.status === 'escalated').length;

    const typeData = CASE_TYPES.map((type) => ({
      name: type.charAt(0).toUpperCase() + type.slice(1),
      value: cases.filter((c) => c.case_type === type).length,
    }));

    const statusData = Object.entries(
      cases.reduce<Record<string, number>>((acc, c) => {
        acc[c.status] = (acc[c.status] ?? 0) + 1;
        return acc;
      }, {})
    ).map(([name, value]) => ({ name: name.replace(/_/g, ' '), value }));

    const recent = [...cases]
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 20);

    return { total, pending, aiEvaluated, humanDecided, escalated, typeData, statusData, recent };
  }, [cases]);

  const caseTrend = summary?.monthly_cases ?? [];
  const loading = casesLoading || summaryLoading;

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Analytics</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Workflow metrics across {metrics.total} cases
        </p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <KpiChip label="Total Cases" value={metrics.total} color="blue" />
        <KpiChip label="Pending Review" value={metrics.pending} color="yellow" />
        <KpiChip label="AI Evaluated" value={metrics.aiEvaluated} color="violet" />
        <KpiChip label="Human Decided" value={metrics.humanDecided} color="emerald" />
        <KpiChip label="Escalated" value={metrics.escalated} color="red" />
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
                  stroke={ct.colors[0]}
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Case Type Breakdown">
            <ResponsiveContainer width="100%" height={160}>
              <BarChart
                data={metrics.typeData}
                layout="vertical"
                margin={{ top: 0, right: 4, left: 0, bottom: 0 }}
              >
                <XAxis type="number" tick={{ fill: ct.muted, fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fill: ct.muted, fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  width={75}
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
                <Bar dataKey="value" fill={ct.colors[0]} radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Status Distribution">
            <ResponsiveContainer width="100%" height={160}>
              <PieChart>
                <Pie
                  data={metrics.statusData}
                  cx="50%"
                  cy="50%"
                  innerRadius={38}
                  outerRadius={62}
                  dataKey="value"
                  isAnimationActive={false}
                >
                  {metrics.statusData.map((_, i) => (
                    <Cell key={i} fill={ct.colors[i % ct.colors.length]} />
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

      {/* Recent Activity */}
      <div className="bg-card border border-border rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-border flex items-center justify-between">
          <h2 className="text-sm font-semibold text-foreground">Recent Activity</h2>
          {casesLoading && <Loader2 className="w-4 h-4 text-primary animate-spin" />}
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-border">
            <thead className="bg-muted/50">
              <tr>
                {['Case ID', 'Type', 'Status', 'Created'].map((h) => (
                  <th
                    key={h}
                    className="px-5 py-3.5 text-left text-xs font-semibold text-muted-foreground tracking-wider"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {metrics.recent.map((c) => (
                <tr key={c.id} className="hover:bg-muted/30 transition-colors">
                  <td className="px-5 py-3.5 text-xs font-mono text-muted-foreground">
                    {c.id.slice(0, 8)}
                  </td>
                  <td className="px-5 py-3.5 text-sm capitalize text-foreground">{c.case_type}</td>
                  <td className="px-5 py-3.5">
                    <StatusBadge value={c.status} type="case" />
                  </td>
                  <td className="px-5 py-3.5 text-sm text-muted-foreground">
                    {new Date(c.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
              {!casesLoading && metrics.recent.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-5 py-10 text-center text-sm text-muted-foreground">
                    No cases found.
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
