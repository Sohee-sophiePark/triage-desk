import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  GitBranch,
  ChevronRight,
  Activity,
  MessageSquare,
  CheckCircle2,
  XCircle,
  Loader2,
  AlertCircle,
  ShieldCheck,
  ShieldX,
  Brain,
  ArrowUpRight,
  Zap,
} from 'lucide-react';
import {
  useWorkflowCase,
  useCaseAudit,
  useDecideCase,
  useEvaluateCase,
} from '@/services/workflow';
import { DEMO } from '../demo';
import StatusBadge from '@/components/StatusBadge';

// ── Small helpers ───────────────────────────────────────────────────────────

function ScoreBar({ value, max = 100 }: { value: number; max?: number }) {
  const pct = Math.round((value / max) * 100);
  const color =
    pct >= 75 ? 'bg-emerald-500' : pct >= 40 ? 'bg-yellow-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-sm font-bold tabular-nums text-foreground w-10 text-right">
        {Math.round(value)}
      </span>
    </div>
  );
}

function SectionCard({ title, icon: Icon, children }: { title: string; icon: React.ElementType; children: React.ReactNode }) {
  return (
    <div className="bg-card border border-border rounded-xl p-6">
      <div className="flex items-center gap-3 mb-5">
        <Icon className="w-5 h-5 text-primary" />
        <h2 className="text-base font-semibold text-foreground">{title}</h2>
      </div>
      {children}
    </div>
  );
}

const SEVERITY_BADGE: Record<string, string> = {
  high: 'bg-red-500/10 text-red-700 dark:text-red-400',
  medium: 'bg-amber-500/10 text-amber-800 dark:text-amber-300',
  low: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
};

// ── Main component ──────────────────────────────────────────────────────────

export default function CaseDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [reasoning, setReasoning] = useState('');
  const [submitError, setSubmitError] = useState<string | null>(null);

  const { data: caseData, isLoading: caseLoading } = useWorkflowCase(id ?? '');
  const { data: auditTrail = [], isLoading: auditLoading } = useCaseAudit(id ?? '');
  const decide = useDecideCase();
  const evaluate = useEvaluateCase();

  const aiEval = caseData?.ai_evaluation;
  const risk = aiEval?.risk_assessment;
  const compliance = aiEval?.compliance_result;
  const evaluation = aiEval?.evaluation;

  const canDecide = !DEMO && (
    caseData?.status === 'pending_review' ||
    caseData?.status === 'in_review' ||
    caseData?.status === 'ai_evaluated');

  const canEvaluate =
    !DEMO && (caseData?.status === 'created' || caseData?.status === 'ai_processing');

  const handleDecision = async (outcome: 'approve' | 'reject' | 'escalate') => {
    if (!reasoning.trim()) {
      setSubmitError('Justification is required before submitting a decision.');
      return;
    }
    setSubmitError(null);
    try {
      await decide.mutateAsync({ id: id!, decision: outcome, reasoning });
      navigate(-1);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setSubmitError(detail || 'Failed to submit decision.');
    }
  };

  const handleEvaluate = async () => {
    try {
      await evaluate.mutateAsync(id!);
    } catch {
      // error visible in mutation state
    }
  };

  if (caseLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-8 w-8 text-primary animate-spin" />
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-6 flex items-center gap-3 text-destructive">
        <AlertCircle className="w-5 h-5 flex-shrink-0" />
        <p>Case not found.</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-12">

      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <button
            onClick={() => navigate(-1)}
            className="text-muted-foreground text-sm hover:text-foreground transition-colors mb-2 flex items-center"
          >
            <ChevronRight className="w-4 h-4 rotate-180 mr-1" />
            Back
          </button>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-bold text-foreground tracking-tight">
              Case <span className="text-muted-foreground font-mono">#{id?.slice(0, 8)}</span>
            </h1>
            <StatusBadge value={caseData.status} type="case" />
            {caseData.case_type && (
              <span className="text-xs font-semibold text-muted-foreground uppercase bg-muted px-2.5 py-0.5 rounded-full">
                {caseData.case_type}
              </span>
            )}
          </div>
        </div>

        <div className="flex gap-3">
          {canEvaluate && (
            <button
              onClick={handleEvaluate}
              disabled={evaluate.isPending}
              className="flex items-center gap-2 bg-primary hover:bg-primary/90 disabled:opacity-50 text-primary-foreground px-4 py-2 rounded-lg text-sm font-semibold transition-colors"
            >
              {evaluate.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Zap className="w-4 h-4" />
              )}
              Run AI Evaluation
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Left: AI output + audit trail */}
        <div className="lg:col-span-2 space-y-6">

          {/* AI Evaluation Results */}
          {aiEval && (
            <SectionCard title="AI Evaluation Results" icon={Brain}>
              {/* Scores row */}
              {evaluation && (
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div className="bg-muted/40 rounded-lg p-4 space-y-2">
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Confidence Score
                    </p>
                    <ScoreBar value={evaluation.confidence_score} />
                  </div>
                  <div className="bg-muted/40 rounded-lg p-4 space-y-2">
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Compliance Score
                    </p>
                    <ScoreBar value={evaluation.compliance_score} />
                  </div>
                </div>
              )}

              {/* Risk assessment */}
              {risk && (
                <div className="border border-border rounded-lg p-4 mb-4">
                  <div className="flex items-center justify-between mb-3">
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Risk Assessment
                    </p>
                    {aiEval.severity && (
                      <span className={`text-xs font-bold px-2 py-0.5 rounded-full uppercase ${SEVERITY_BADGE[aiEval.severity] ?? ''}`}>
                        {aiEval.severity} severity
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-foreground leading-relaxed mb-3">{risk.justification}</p>
                  {risk.evidence.length > 0 && (
                    <div className="space-y-1.5">
                      <p className="text-xs font-semibold text-muted-foreground">Rationale</p>
                      {risk.evidence.map((e, i) => (
                        <div key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                          <ArrowUpRight className="w-3 h-3 mt-0.5 flex-shrink-0 text-primary" />
                          {e}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Compliance result */}
              {compliance && (
                <div className="border border-border rounded-lg p-4 mb-4">
                  <div className="flex items-center gap-2 mb-2">
                    {compliance.passed ? (
                      <ShieldCheck className="w-4 h-4 text-emerald-700 dark:text-emerald-400" />
                    ) : (
                      <ShieldX className="w-4 h-4 text-red-700 dark:text-red-400" />
                    )}
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Compliance Check — {compliance.passed ? 'Passed' : 'Failed'}
                    </p>
                  </div>
                  <p className="text-sm text-foreground">{compliance.reason}</p>
                  {compliance.violations.length > 0 && (
                    <ul className="mt-2 space-y-1">
                      {compliance.violations.map((v, i) => (
                        <li key={i} className="text-xs text-red-700 dark:text-red-400 flex items-start gap-1.5">
                          <AlertCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                          {v}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              {/* Hallucination flags */}
              {evaluation && evaluation.hallucination_count > 0 && (
                <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4">
                  <p className="text-xs font-semibold text-yellow-800 dark:text-yellow-400 mb-2">
                    {evaluation.hallucination_count} Hallucination Flag{evaluation.hallucination_count > 1 ? 's' : ''} Detected
                  </p>
                  {evaluation.hallucination_flags.map((f, i) => (
                    <p key={i} className="text-xs text-yellow-800 dark:text-yellow-400">{f}</p>
                  ))}
                </div>
              )}

              {/* Intent + routing */}
              {aiEval.intent && (
                <div className="mt-4 flex items-center gap-2 flex-wrap">
                  <span className="text-xs text-muted-foreground">Intent:</span>
                  <span className="text-xs font-medium text-foreground bg-muted px-2 py-0.5 rounded">
                    {aiEval.intent}
                  </span>
                  {aiEval.routed_agents?.map((a) => (
                    <span key={a} className="text-xs font-medium text-primary bg-primary/10 px-2 py-0.5 rounded">
                      {a}
                    </span>
                  ))}
                </div>
              )}
            </SectionCard>
          )}

          {/* Agent run: code-computed flags, routing, evaluator verdict and per-node trace */}
          {aiEval?.trace && (
            <SectionCard title="Agent Run" icon={GitBranch}>
              <div className="flex flex-wrap gap-2 text-xs mb-4">
                <span className="px-2 py-1 rounded bg-muted">Severity: <b>{aiEval.severity}</b></span>
                {aiEval.brief && <span className="px-2 py-1 rounded bg-muted">Recommended: <b>{aiEval.brief.disposition.replace('_', ' ')}</b></span>}
                <span className="px-2 py-1 rounded bg-muted">Revisions: <b>{aiEval.revisions ?? 0}</b></span>
                {aiEval.flags?.map((f) => (
                  <span key={f.code} title={f.label} className="px-2 py-1 rounded bg-amber-500/10 text-amber-800 dark:text-amber-300">
                    {f.code} · {f.severity}
                  </span>
                ))}
              </div>
              {aiEval.verdict && (
                <p className="text-xs text-muted-foreground mb-4">
                  Evaluator: grounded {aiEval.verdict.grounded}/5 · complete {aiEval.verdict.complete}/5 ·
                  disposition {aiEval.verdict.disposition_justified}/5 · clear {aiEval.verdict.clear}/5
                </p>
              )}
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs">
                  <thead className="text-muted-foreground text-left">
                    <tr><th className="py-1 pr-3">Step</th><th className="pr-3">Kind</th><th className="pr-3">OK</th><th className="pr-3">ms</th><th className="pr-3">Model</th><th>Note</th></tr>
                  </thead>
                  <tbody>
                    {aiEval.trace.map((t, i) => (
                      <tr key={i} className="border-t border-border">
                        <td className="py-1 pr-3 font-medium text-foreground">{t.node}</td>
                        <td className="pr-3">{t.kind}</td>
                        <td className="pr-3">{t.ok ? '✓' : '✗'}</td>
                        <td className="pr-3 tabular-nums">{t.ms}</td>
                        <td className="pr-3">{t.model?.replace('gemini/', '') ?? (t.source ?? '—')}</td>
                        <td className="text-muted-foreground">{t.note}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </SectionCard>
          )}

          {/* Audit Trail */}
          <SectionCard title="Audit Trail" icon={Activity}>
            {auditLoading ? (
              <div className="flex justify-center py-12">
                <Loader2 className="w-6 h-6 text-primary animate-spin" />
              </div>
            ) : auditTrail.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-10">
                No audit events yet. Run AI evaluation to populate the trace.
              </p>
            ) : (
              <div className="relative space-y-6 before:absolute before:left-3 before:top-2 before:bottom-2 before:w-0.5 before:bg-border">
                {auditTrail.map((event, idx) => (
                  <div key={idx} className="relative pl-10">
                    <div className="absolute left-0 top-1 w-6 h-6 rounded-full border-2 border-background bg-primary" />
                    <div className="bg-muted/30 border border-border rounded-lg p-4 hover:border-primary/30 transition-colors">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                          {event.actor_id}
                        </span>
                        <span className="text-[10px] text-muted-foreground font-mono">
                          {new Date(event.created_at).toLocaleTimeString()}
                        </span>
                      </div>
                      <p className="text-sm text-foreground font-medium">{event.action}</p>
                      {event.changes && Object.keys(event.changes).length > 0 && (
                        <pre className="mt-2 text-[10px] text-muted-foreground bg-muted/50 rounded p-2 overflow-x-auto">
                          {JSON.stringify(event.changes, null, 2)}
                        </pre>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>
        </div>

        {/* Right: Human decision panel */}
        <div className="space-y-6">
          <div className="bg-card border border-border rounded-xl p-6 sticky top-6">
            <div className="flex items-center gap-3 mb-5">
              <MessageSquare className="w-5 h-5 text-primary" />
              <h2 className="text-base font-semibold text-foreground">Analyst Decision</h2>
            </div>

            {caseData.human_decision ? (
              <div className="space-y-3">
                <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-4">
                  <p className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 mb-1">Decision Recorded</p>
                  <p className="text-sm text-foreground capitalize">
                    {String(caseData.human_decision.decision ?? '')}
                  </p>
                </div>
                {caseData.human_decision.reasoning != null && (
                  <div className="bg-muted/40 rounded-lg p-4">
                    <p className="text-xs font-semibold text-muted-foreground mb-1">Reasoning</p>
                    <p className="text-sm text-foreground">{String(caseData.human_decision.reasoning)}</p>
                  </div>
                )}
              </div>
            ) : canDecide ? (
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground leading-relaxed">
                  Review the AI evidence above. Your decision is logged immutably.
                </p>

                <textarea
                  placeholder="Required justification for your decision…"
                  className="w-full bg-background border border-border rounded-lg p-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-colors min-h-[100px] resize-none"
                  value={reasoning}
                  onChange={(e) => { setReasoning(e.target.value); setSubmitError(null); }}
                  disabled={decide.isPending}
                />

                {submitError && (
                  <div className="flex items-start gap-2 text-destructive text-xs bg-destructive/10 border border-destructive/20 rounded-lg p-3">
                    <AlertCircle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                    {submitError}
                  </div>
                )}

                <button
                  onClick={() => handleDecision('approve')}
                  disabled={decide.isPending}
                  className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white py-2.5 rounded-lg font-semibold flex items-center justify-center gap-2 transition-colors text-sm"
                >
                  {decide.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                  Approve
                </button>

                <button
                  onClick={() => handleDecision('escalate')}
                  disabled={decide.isPending}
                  className="w-full bg-yellow-500/10 hover:bg-yellow-500/20 disabled:opacity-50 text-yellow-800 dark:text-yellow-400 border border-yellow-500/30 py-2.5 rounded-lg font-semibold flex items-center justify-center gap-2 transition-colors text-sm"
                >
                  <AlertCircle className="w-4 h-4" />
                  Escalate
                </button>

                <button
                  onClick={() => handleDecision('reject')}
                  disabled={decide.isPending}
                  className="w-full bg-muted hover:bg-red-500/10 hover:text-red-700 dark:hover:text-red-400 disabled:opacity-50 text-muted-foreground py-2.5 rounded-lg font-semibold flex items-center justify-center gap-2 transition-colors text-sm"
                >
                  <XCircle className="w-4 h-4" />
                  Reject
                </button>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-6">
                {DEMO
                  ? 'Read-only demo: a reviewer approves, rejects or escalates here in the live app.'
                  : canEvaluate
                  ? 'Run AI evaluation first to enable the decision panel.'
                  : 'This case has already been decided or is not yet ready for review.'}
              </p>
            )}
          </div>

          {/* Case metadata */}
          <div className="bg-card border border-border rounded-xl p-5 space-y-3">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Case Info</p>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Type</span>
                <span className="text-foreground capitalize font-medium">{caseData.case_type}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Created</span>
                <span className="text-foreground">{new Date(caseData.created_at).toLocaleDateString()}</span>
              </div>
              {caseData.confidence_score != null && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Confidence</span>
                  <span className="text-foreground font-medium tabular-nums">
                    {Math.round(caseData.confidence_score)}%
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
