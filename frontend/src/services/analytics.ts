import { useQuery } from '@tanstack/react-query';
import api from './api';

export interface AnalyticsSummary {
  total_customers: number;
  total_aum: number;
  estimated_revenue: number;
  avg_credit_score: number;
  total_incidents: number;
  pending_review_cases: number;
  escalated_cases: number;
  credit_score_distribution: Array<{ range: string; count: number }>;
  segment_distribution: Record<string, number>;
  kyc_status_distribution: Record<string, number>;
  aum_by_segment: Record<string, number>;
  product_type_distribution: Record<string, number>;
  incident_type_distribution: Record<string, number>;
  incident_severity_distribution: Record<string, number>;
  cases_by_type: Record<string, number>;
  cases_by_status: Record<string, number>;
  monthly_transaction_volume: Array<{ month: string; volume: number }>;
  monthly_cases: Array<{ month: string; count: number }>;
  monthly_aum: Array<{ month: string; aum: number }>;
}

export function useAnalyticsSummary() {
  return useQuery<AnalyticsSummary>({
    queryKey: ['analytics', 'summary'],
    queryFn: () => api.get('/analytics/summary').then((r) => r.data.data),
    staleTime: 60_000,
  });
}
