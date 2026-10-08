import { useQuery } from '@tanstack/react-query';
import api from './api';
import type { Customer, Account, Transaction, Holding, RiskIncident } from '@/types';

export function useCustomers(page = 1, size = 50) {
  return useQuery<Customer[]>({
    queryKey: ['customers', page, size],
    queryFn: () =>
      api.get('/customers', { params: { page, size } }).then((r) => r.data.data ?? []),
  });
}

export function useCustomer(id: string) {
  return useQuery<Customer>({
    queryKey: ['customer', id],
    queryFn: () =>
      api.get(`/customers/${id}`).then((r) => r.data.data),
    enabled: !!id,
  });
}

export function useCustomerAccounts(id: string) {
  return useQuery<Account[]>({
    queryKey: ['customer', id, 'accounts'],
    queryFn: () =>
      api.get(`/customers/${id}/accounts`).then((r) => r.data.data ?? []),
    enabled: !!id,
  });
}

export function useCustomerTransactions(id: string, page = 1) {
  return useQuery<Transaction[]>({
    queryKey: ['customer', id, 'transactions', page],
    queryFn: () =>
      api.get(`/customers/${id}/transactions`, { params: { page, size: 20 } }).then((r) => r.data.data ?? []),
    enabled: !!id,
  });
}

export function useCustomerHoldings(id: string) {
  return useQuery<Holding[]>({
    queryKey: ['customer', id, 'holdings'],
    queryFn: () =>
      api.get(`/customers/${id}/holdings`).then((r) => r.data.data ?? []),
    enabled: !!id,
  });
}

export function useCustomerRiskIncidents(id: string) {
  return useQuery<RiskIncident[]>({
    queryKey: ['customer', id, 'risk-incidents'],
    queryFn: () =>
      api.get(`/customers/${id}/risk-incidents`).then((r) => r.data.data ?? []),
    enabled: !!id,
  });
}
