import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ChevronRight, Loader2, AlertCircle, User, CreditCard, ArrowLeftRight, BarChart2, ShieldAlert } from 'lucide-react';
import {
  useCustomer,
  useCustomerAccounts,
  useCustomerTransactions,
  useCustomerHoldings,
  useCustomerRiskIncidents,
} from '@/services/customers';
import StatusBadge from '@/components/StatusBadge';
import { useRecentCustomersStore } from '@/stores/recentCustomersStore';

type Tab = 'overview' | 'accounts' | 'transactions' | 'holdings' | 'risk';

const TABS: { id: Tab; label: string; icon: React.ElementType }[] = [
  { id: 'overview', label: 'Overview', icon: User },
  { id: 'accounts', label: 'Accounts', icon: CreditCard },
  { id: 'transactions', label: 'Transactions', icon: ArrowLeftRight },
  { id: 'holdings', label: 'Holdings', icon: BarChart2 },
  { id: 'risk', label: 'Risk', icon: ShieldAlert },
];

export default function CustomerDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [txPage, setTxPage] = useState(1);

  const { data: customer, isLoading: loadingCustomer, error: customerError } = useCustomer(id!);
  const { data: accounts = [], isLoading: loadingAccounts } = useCustomerAccounts(id!);
  const { data: transactions = [], isLoading: loadingTx } = useCustomerTransactions(id!, txPage);
  const { data: holdings = [], isLoading: loadingHoldings } = useCustomerHoldings(id!);
  const { data: incidents = [], isLoading: loadingIncidents } = useCustomerRiskIncidents(id!);
  const { addRecent } = useRecentCustomersStore();

  useEffect(() => {
    if (customer) {
      addRecent({
        id: customer.id,
        name: `${customer.first_name} ${customer.last_name}`,
        segment: customer.segment,
        lastViewed: new Date().toISOString(),
      });
    }
  }, [customer, addRecent]);

  if (loadingCustomer) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-8 w-8 text-primary animate-spin" />
      </div>
    );
  }

  if (customerError || !customer) {
    return (
      <div className="bg-red-900/20 border border-red-900/50 rounded-lg p-6 text-red-500">
        <div className="flex items-center gap-2 mb-2">
          <AlertCircle className="w-5 h-5" />
          <h3 className="text-lg font-medium">Customer Not Found</h3>
        </div>
        <p className="text-sm">Could not load customer data. Check that the ID is valid.</p>
      </div>
    );
  }

  const creditColor =
    customer.credit_score > 700
      ? 'text-emerald-400'
      : customer.credit_score > 600
      ? 'text-yellow-400'
      : 'text-red-400';

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      {/* Header */}
      <div>
        <button
          onClick={() => navigate('/customers')}
          className="text-muted-foreground text-sm hover:text-foreground transition-colors mb-2 flex items-center"
        >
          <ChevronRight className="w-4 h-4 rotate-180 mr-1" /> Back to Customers
        </button>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground tracking-tight">
              {customer.first_name} {customer.last_name}
            </h1>
            <p className="text-sm text-muted-foreground font-mono mt-1">{customer.external_id}</p>
          </div>
          <div className="flex gap-2">
            <StatusBadge value={customer.kyc_status} type="kyc" />
            <StatusBadge value={customer.segment} />
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-border">
        <nav className="flex gap-1">
          {TABS.map(({ id: tabId, label, icon: Icon }) => (
            <button
              key={tabId}
              onClick={() => setActiveTab(tabId)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tabId
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-card border border-border rounded-xl p-6 space-y-4">
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Profile</h2>
            <dl className="space-y-3">
              <Row label="Email" value={customer.email} />
              <Row label="Segment" value={capitalize(customer.segment)} />
              <Row label="Income Bracket" value={capitalize(customer.income_bracket)} />
              <Row label="Risk Tolerance" value={capitalize(customer.risk_tolerance)} />
              <Row label="Member Since" value={new Date(customer.created_at).toLocaleDateString()} />
            </dl>
          </div>
          <div className="bg-card border border-border rounded-xl p-6 space-y-4">
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Credit & Risk</h2>
            <div className="flex items-center justify-center py-6">
              <div className="text-center">
                <p className={`text-6xl font-bold tabular-nums ${creditColor}`}>{customer.credit_score}</p>
                <p className="text-sm text-muted-foreground mt-2">Credit Score</p>
              </div>
            </div>
            <dl className="space-y-3">
              <Row label="KYC Status" value={<StatusBadge value={customer.kyc_status} type="kyc" />} />
            </dl>
          </div>
        </div>
      )}

      {activeTab === 'accounts' && (
        <TabSection loading={loadingAccounts} empty={accounts.length === 0} emptyMsg="No accounts found.">
          <table className="min-w-full divide-y divide-border">
            <thead className="bg-muted/50">
              <tr>
                <Th>Account Number</Th>
                <Th>Type</Th>
                <Th>Balance</Th>
                <Th>Currency</Th>
                <Th>Status</Th>
                <Th>Opened</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {accounts.map((acc) => (
                <tr key={acc.id} className="hover:bg-muted/30 transition-colors">
                  <Td mono>{acc.account_number}</Td>
                  <Td>{capitalize(acc.account_type)}</Td>
                  <Td>
                    <span className="font-mono text-emerald-400">
                      {acc.currency} {Number(acc.balance).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </span>
                  </Td>
                  <Td>{acc.currency}</Td>
                  <Td><StatusBadge value={acc.status} /></Td>
                  <Td>{new Date(acc.opened_date).toLocaleDateString()}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </TabSection>
      )}

      {activeTab === 'transactions' && (
        <TabSection loading={loadingTx} empty={transactions.length === 0} emptyMsg="No transactions found.">
          <table className="min-w-full divide-y divide-border">
            <thead className="bg-muted/50">
              <tr>
                <Th>Timestamp</Th>
                <Th>Amount</Th>
                <Th>Merchant</Th>
                <Th>Category</Th>
                <Th>Channel</Th>
                <Th>Risk</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {transactions.map((tx) => (
                <tr key={tx.id} className="hover:bg-muted/30 transition-colors">
                  <Td mono>{new Date(tx.timestamp).toLocaleString()}</Td>
                  <Td>
                    <span className={`font-mono ${tx.transaction_type === 'credit' || tx.transaction_type === 'deposit' ? 'text-emerald-400' : 'text-foreground'}`}>
                      {tx.transaction_type === 'credit' || tx.transaction_type === 'deposit' ? '+' : '-'}
                      {Number(tx.amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </span>
                  </Td>
                  <Td>{tx.merchant || '—'}</Td>
                  <Td>{tx.category}</Td>
                  <Td>{capitalize(tx.channel)}</Td>
                  <Td>
                    {tx.risk_flag ? (
                      <span className="inline-flex items-center gap-1 text-red-400 text-xs">
                        <ShieldAlert className="w-3.5 h-3.5" /> Flagged
                      </span>
                    ) : (
                      <span className="text-muted-foreground text-xs">—</span>
                    )}
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex items-center justify-between px-6 py-4 border-t border-border">
            <button
              onClick={() => setTxPage((p) => Math.max(1, p - 1))}
              disabled={txPage === 1}
              className="text-sm text-muted-foreground hover:text-foreground disabled:opacity-40 transition-colors"
            >
              Previous
            </button>
            <span className="text-sm text-muted-foreground">Page {txPage}</span>
            <button
              onClick={() => setTxPage((p) => p + 1)}
              disabled={transactions.length < 20}
              className="text-sm text-muted-foreground hover:text-foreground disabled:opacity-40 transition-colors"
            >
              Next
            </button>
          </div>
        </TabSection>
      )}

      {activeTab === 'holdings' && (
        <TabSection loading={loadingHoldings} empty={holdings.length === 0} emptyMsg="No holdings found.">
          <table className="min-w-full divide-y divide-border">
            <thead className="bg-muted/50">
              <tr>
                <Th>Product Type</Th>
                <Th>Current Value</Th>
                <Th>Quantity</Th>
                <Th>Acquired</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {holdings.map((h) => (
                <tr key={h.id} className="hover:bg-muted/30 transition-colors">
                  <Td>{capitalize(h.product_type)}</Td>
                  <Td>
                    <span className="font-mono text-emerald-400">
                      {Number(h.current_value).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </span>
                  </Td>
                  <Td mono>{Number(h.quantity).toFixed(4)}</Td>
                  <Td>{new Date(h.acquisition_date).toLocaleDateString()}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </TabSection>
      )}

      {activeTab === 'risk' && (
        <TabSection loading={loadingIncidents} empty={incidents.length === 0} emptyMsg="No risk incidents found.">
          <div className="divide-y divide-border">
            {incidents.map((inc) => (
              <div key={inc.id} className="p-6 hover:bg-muted/20 transition-colors">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <StatusBadge value={inc.severity} type="severity" />
                    <span className="text-sm font-medium text-foreground capitalize">
                      {inc.incident_type.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge value={inc.status} />
                    <span className="text-xs text-muted-foreground">{new Date(inc.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground">{inc.description}</p>
                {inc.resolved_at && (
                  <p className="text-xs text-muted-foreground mt-2">
                    Resolved: {new Date(inc.resolved_at).toLocaleDateString()}
                  </p>
                )}
              </div>
            ))}
          </div>
        </TabSection>
      )}
    </div>
  );
}

function capitalize(s: string) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, ' ') : '—';
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between items-center">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="text-sm text-foreground text-right">{value}</dd>
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="px-6 py-4 text-left text-xs font-semibold text-muted-foreground tracking-wider">{children}</th>
  );
}

function Td({ children, mono }: { children: React.ReactNode; mono?: boolean }) {
  return (
    <td className={`px-6 py-4 whitespace-nowrap text-sm ${mono ? 'font-mono text-foreground' : 'text-foreground'}`}>
      {children}
    </td>
  );
}

function TabSection({
  loading,
  empty,
  emptyMsg,
  children,
}: {
  loading: boolean;
  empty: boolean;
  emptyMsg: string;
  children: React.ReactNode;
}) {
  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="w-6 h-6 text-primary animate-spin" />
      </div>
    );
  }
  if (empty) {
    return <p className="text-center text-muted-foreground py-16 text-sm">{emptyMsg}</p>;
  }
  return (
    <div className="bg-card border border-border rounded-xl overflow-hidden">
      {children}
    </div>
  );
}
