import { create } from 'zustand';
import type { WorkflowCase } from '@/types';

interface WorkflowState {
  cases: WorkflowCase[];
  activeCaseId: string | null;
  setCases: (cases: WorkflowCase[]) => void;
  setActiveCaseId: (id: string | null) => void;
}

export const useWorkflowStore = create<WorkflowState>((set) => ({
  cases: [],
  activeCaseId: null,
  setCases: (cases) => set({ cases }),
  setActiveCaseId: (id) => set({ activeCaseId: id }),
}));
