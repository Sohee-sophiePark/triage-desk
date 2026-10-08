import React, { useMemo, useState } from 'react';
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
} from 'recharts';
import { Search, Loader2, AlertCircle } from 'lucide-react';
import { useCustomers } from '@/services/customers';
import { useAnalyticsSummary } from '@/services/analytics';
import { useRecentCustomersStore } from '@/stores/recentCustomersStore';
import { useChartTheme } from '@/hooks/useChartTheme';
import StatusBadge from '@/components/StatusBadge';
import type { Customer } from '@/types';

function fmt(n: number) {
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(1)}B`;
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

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

export default function Customers() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const ct = useChartTheme();
  const { recentCustomers } = useRecentCustomersStore();

  const { data: customers = [], isLoading: customersLoading } = useCustomers();
  const { data: summary, isLoading: summaryLoading } = useAnalyticsSummary();

  const filtered = useMemo(() => {
    if (!search) return customers;
    const q = search.toLowerCase();
    return customers.filter(
      (c: Customer) =>
        `${c.first_name} ${c.last_name}`.toLowerCase().includes(q) ||
        c.email.toLowerCase().includes(q) ||
        c.external_id.toLowerCase().includes(q)
    );
  }, [customers, search]);

  // Chart data from summary
  const creditChartData = summary?.credit_score_distribution ?? [];
  const segmentData = Object.entries(summary?.segment_distribution ?? {}).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    value,
  }));
  const kycData = Object.entries(summary?.kyc_status_distribution ?? {}).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1).replace(/_/g, ' '),
    value,
  }));
  const aumSegData = Object.entries(summary?.aum_by_segment ?? {}).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    value,
  }));

  const PIE_COLORS = ct.colors;

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Customers</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {summary ? `${summary.total_customers.toLocaleString()} clients · avg credit ${summary.avg_credit_score}` : 'Loading…'}
        </p>
      </div>

      {/* Charts row */}
      {!summaryLoading && summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {/* Credit score distribution */}
          <ChartCard title="Credit Score Distribution">
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={creditChartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <XAxis
                  dataKey="range"
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
                <Bar dataKey="count" fill={ct.colors[0]} radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          {/* Segment breakdown */}
          <ChartCard title="Client Segments">
            <ResponsiveContainer width="100%" height={160}>
              <PieChart>
                <Pie
                  data={segmentData}
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={65}
                  dataKey="value"
                  isAnimationActive={false}
                >
                  {segmentData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Legend
                  iconType="circle"
                  iconSize={8}
                  wrapperStyle={{ fontSize: 10, color: ct.muted }}
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
              </PieChart>
            </ResponsiveContainer>
          </ChartCard>

          {/* AUM by segment */}
          <ChartCard title="AUM by Segment">
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={aumSegData} margin={{ top: 0, right: 0, left: -10, bottom: 0 }}>
                <XAxis
                  dataKey="name"
                  tick={{ fill: ct.muted, fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tickFormatter={(v) => fmt(v)}
                  tick={{ fill: ct.muted, fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  formatter={(v) => fmt(Number(v))}
                  contentStyle={{
                    backgroundColor: ct.tooltip.bg,
                    border: `1px solid ${ct.tooltip.border}`,
                    borderRadius: '8px',
                    color: ct.tooltip.text,
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="value" fill={ct.colors[1]} radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          {/* KYC status */}
          <ChartCard title="KYC Status">
            <ResponsiveContainer width="100%" height={160}>
              <PieChart>
                <Pie
                  data={kycData}
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={65}
                  dataKey="value"
                  isAnimationActive={false}
                >
                  {kycData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Legend
                  iconType="circle"
                  iconSize={8}
                  wrapperStyle={{ fontSize: 10, color: ct.muted }}
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
              </PieChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>
      )}

      {/* Recently viewed */}
      {recentCustomers.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            Recently Viewed
          </h3>
          <div className="flex flex-wrap gap-2">
            {recentCustomers.map((rc) => (
              <button
                key={rc.id}
                onClick={() => navigate(`/customers/${rc.id}`)}
                className="flex items-center gap-2 bg-card border border-border rounded-lg px-3 py-2 hover:border-primary/50 hover:bg-muted transition-colors"
              >
                <div className="text-left">
                  <p className="text-sm font-medium text-foreground leading-tight">{rc.name}</p>
                  <p className="text-xs text-muted-foreground capitalize">{rc.segment}</p>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Search + list */}
      <div className="space-y-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search by name, email, or ID…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2.5 bg-card border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-colors"
          />
        </div>

        {customersLoading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="w-6 h-6 text-primary animate-spin" />
          </div>
        ) : (
          <div className="bg-card border border-border rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-border">
                <thead className="bg-muted/50">
                  <tr>
                    {['External ID', 'Name', 'Email', 'Credit Score', 'Segment', 'KYC', 'Risk Profile'].map((h) => (
                      <th key={h} className="px-5 py-3.5 text-left text-xs font-semibold text-muted-foreground tracking-wider">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filtered.map((c: Customer) => (
                    <tr
                      key={c.id}
                      onClick={() => navigate(`/customers/${c.id}`)}
                      className="hover:bg-muted/40 transition-colors cursor-pointer"
                    >
                      <td className="px-5 py-3.5 text-xs font-mono text-muted-foreground whitespace-nowrap">
                        {c.external_id}
                      </td>
                      <td className="px-5 py-3.5 text-sm font-medium text-foreground whitespace-nowrap">
                        {c.first_name} {c.last_name}
                      </td>
                      <td className="px-5 py-3.5 text-sm text-muted-foreground whitespace-nowrap">
                        {c.email}
                      </td>
                      <td className="px-5 py-3.5 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                            c.credit_score > 700
                              ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                              : c.credit_score > 600
                              ? 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-400'
                              : 'bg-red-500/10 text-red-600 dark:text-red-400'
                          }`}
                        >
                          {c.credit_score}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 text-sm text-foreground capitalize whitespace-nowrap">
                        {c.segment}
                      </td>
                      <td className="px-5 py-3.5 whitespace-nowrap">
                        <StatusBadge value={c.kyc_status} type="kyc" />
                      </td>
                      <td className="px-5 py-3.5 text-sm text-foreground capitalize whitespace-nowrap">
                        {c.risk_tolerance}
                      </td>
                    </tr>
                  ))}
                  {filtered.length === 0 && (
                    <tr>
                      <td colSpan={7} className="px-5 py-10 text-center text-sm text-muted-foreground">
                        {search ? 'No customers match your search.' : 'No customers found.'}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
