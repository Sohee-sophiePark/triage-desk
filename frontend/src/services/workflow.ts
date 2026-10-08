import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from './api';
import type { WorkflowCase, AuditEvent } from '@/types';

export function useWorkflowCases(filters?: Record<string, string>) {
  return useQuery<WorkflowCase[]>({
    queryKey: ['workflow', 'cases', filters],
    queryFn: () =>
      api.get('/workflow/cases', { params: filters }).then((r) => r.data ?? []),
  });
}

export function useWorkflowCase(id: string) {
  return useQuery<WorkflowCase>({
    queryKey: ['workflow', 'case', id],
    queryFn: () =>
      api.get(`/workflow/cases/${id}`).then((r) => r.data),
    enabled: !!id,
  });
}

export function useCaseAudit(id: string) {
  return useQuery<AuditEvent[]>({
    queryKey: ['workflow', 'case', id, 'audit'],
    queryFn: () =>
      api.get(`/workflow/cases/${id}/audit`).then((r) => r.data.audit_trail ?? []),
    enabled: !!id,
  });
}

export function useDecideCase() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, decision, reasoning }: { id: string; decision: 'approve' | 'reject' | 'escalate'; reasoning: string }) =>
      api.post(`/workflow/cases/${id}/decide`, { decision, reasoning }),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: ['workflow', 'case', id] });
      qc.invalidateQueries({ queryKey: ['workflow', 'cases'] });
    },
  });
}

export function useEvaluateCase() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.post(`/workflow/cases/${id}/evaluate`, {}),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ['workflow', 'case', id] });
      qc.invalidateQueries({ queryKey: ['workflow', 'cases'] });
    },
  });
}
