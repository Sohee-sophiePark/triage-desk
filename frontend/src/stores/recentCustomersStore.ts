import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface RecentCustomer {
  id: string;
  name: string;
  segment: string;
  lastViewed: string;
}

interface RecentCustomersState {
  recentCustomers: RecentCustomer[];
  addRecent: (customer: RecentCustomer) => void;
}

export const useRecentCustomersStore = create<RecentCustomersState>()(
  persist(
    (set) => ({
      recentCustomers: [],
      addRecent: (customer) =>
        set((s) => {
          const filtered = s.recentCustomers.filter((c) => c.id !== customer.id);
          return { recentCustomers: [customer, ...filtered].slice(0, 5) };
        }),
    }),
    { name: 'triage-desk-recent-customers' }
  )
);
