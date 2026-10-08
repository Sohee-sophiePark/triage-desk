export interface User {
  id: string;
  role: string;
  exp: number;
}

export interface Customer {
  id: string;
  external_id: string;
  first_name: string;
  last_name: string;
  email: string;
  credit_score: number;
  risk_tolerance: string;
  segment: string;
  kyc_status: string;
  income_bracket: string;
  created_at: string;
}

export interface Account {
  id: string;
  customer_id: string;
  account_number: string;
  account_type: string;
  balance: number;
  currency: string;
  status: string;
  opened_date: string;
}

export interface Transaction {
  id: string;
  account_id: string;
  amount: number;
  transaction_type: string;
  category: string;
  merchant: string;
  channel: string;
  status: string;
  risk_flag: boolean;
  timestamp: string;
  description: string;
}

export interface Holding {
  id: string;
  customer_id: string;
  product_type: string;
  quantity: number;
  current_value: number;
  acquisition_date: string;
}

export interface RiskIncident {
  id: string;
  customer_id: string;
  incident_type: string;
  severity: string;
  status: string;
  description: string;
  related_transaction_ids: string[];
  created_at: string;
  resolved_at: string | null;
}

export interface RiskAssessment {
  confidence: number;
  justification: string;
  evidence: string[];
}

export interface ComplianceResult {
  passed: boolean;
  reason: string;
  violations: string[];
}

export interface Evaluation {
  confidence_score: number;
  hallucination_flags: string[];
  hallucination_count: number;
  compliance_score: number;
  evaluated_at: string;
}

export interface AIEvaluation {
  intent?: string;
  routed_agents?: string[];
  risk_assessment?: RiskAssessment;
  compliance_result?: ComplianceResult;
  evaluation?: Evaluation;
  severity?: string;
  flags?: { code: string; severity: string; label: string }[];
  revisions?: number;
  review_reason?: string;
  brief?: { disposition: string; cited_flags: string[] } | null;
  verdict?: { grounded: number; complete: number; disposition_justified: number; clear: number; passed: boolean } | null;
  trace?: { node: string; kind: string; ms: number; ok: boolean; note: string; source?: string | null; model?: string | null }[];
}

export interface WorkflowCase {
  id: string;
  case_type: string;
  status: string;
  confidence_score: number | null;
  created_at: string;
  updated_at: string;
  ai_evaluation: AIEvaluation | null;
  human_decision: Record<string, unknown> | null;
  assigned_to: string | null;
}

export interface AuditEvent {
  action: string;
  actor_id: string;
  changes: Record<string, unknown>;
  created_at: string;
}

export interface PaginatedMeta {
  page: number;
  size: number;
  count: number;
}

export interface APIResponse<T> {
  status: string;
  data: T;
  meta: Record<string, unknown>;
}
