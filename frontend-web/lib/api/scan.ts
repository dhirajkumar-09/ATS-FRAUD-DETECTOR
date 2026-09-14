import apiClient from './client';
import type {
  ScanResult,
  FraudSignal,
  RawPostScanResponse,
  RawGetScanResponse,
  RawBatchResponse,
  RawSignal,
  InspectResult,
  InspectPage,
  TextSpan,
  ScanHistoryResponse,
} from '../types';

// ── Helpers ───────────────────────────────────────────────────────────────────

function normalizeSignal(raw: RawSignal): FraudSignal {
  return {
    signal_type: raw.signal_type,
    severity: (raw.severity?.toUpperCase() ?? 'LOW') as FraudSignal['severity'],
    description: raw.description,
    page: raw.page ?? null,
    detail: raw.evidence_text ?? null,
    risk_points: raw.risk_points ?? null,
    evidence_strength: raw.evidence_strength ?? null,
    confidence: raw.confidence ?? null,
    remediation: raw.remediation ?? null,
    evidence: raw.evidence ?? null,
  };
}

function buildBreakdownFromSignals(signals: FraudSignal[]): Record<string, number> {
  const breakdown: Record<string, number> = {
    hidden_text: 0,
    zero_width_chars: 0,
    homoglyph: 0,
    offpage: 0,
    font_anomaly: 0,
    metadata: 0,
    prompt_injection: 0,
  };
  const categoryMap: Record<string, string> = {
    hidden_text: 'hidden_text',
    zero_or_tiny_font: 'hidden_text',
    invisible_characters: 'zero_width_chars',
    zero_width_chars: 'zero_width_chars',
    homoglyph_substitution: 'homoglyph',
    homoglyph: 'homoglyph',
    offpage_text: 'offpage',
    offpage: 'offpage',
    layer_order_mismatch: 'font_anomaly',
    font_substitution: 'font_anomaly',
    font_anomaly: 'font_anomaly',
    image_only_page: 'font_anomaly',
    stripped_metadata: 'metadata',
    rapid_lifecycle: 'metadata',
    generic_producer: 'metadata',
    metadata: 'metadata',
    prompt_injection: 'prompt_injection',
    duplicate_template: 'prompt_injection',
  };
  for (const s of signals) {
    const cat = categoryMap[s.signal_type] ?? 'font_anomaly';
    if (cat in breakdown) {
      breakdown[cat] += Math.round(s.risk_points ?? 0);
    }
  }
  return breakdown;
}

// Transforms POST /scan response → normalised ScanResult
function transformPostScan(raw: RawPostScanResponse): ScanResult {
  const signals: FraudSignal[] = (raw.fraud_summary?.signals ?? []).map(normalizeSignal);

  // Build a simple text summary from signal counts
  const total = raw.fraud_summary?.total ?? 0;
  const high  = raw.fraud_summary?.high ?? 0;
  const fraudSummaryText =
    total === 0
      ? 'No fraud signals detected in this resume.'
      : `${total} signal${total > 1 ? 's' : ''} detected (${high} high severity).`;

  const trustScore = Math.round(raw.trust_score?.score ?? 0);
  const signalRisk = signals.reduce((sum, s) => sum + (s.risk_points ?? 0), 0);
  const forensicRiskScore = raw.trust_score?.forensic_risk_score != null
    ? Math.round(raw.trust_score.forensic_risk_score)
    : Math.round(signalRisk);

  const riskBreakdown = (raw.trust_score?.risk_breakdown && Object.keys(raw.trust_score.risk_breakdown).length > 0)
    ? raw.trust_score.risk_breakdown
    : buildBreakdownFromSignals(signals);

  return {
    scan_id:          raw.scan_id,
    share_token:      raw.share_token ?? null,
    filename:         raw.filename,
    trust_score:      trustScore,
    trust_label:      raw.trust_score?.label ?? 'UNKNOWN',
    forensic_risk_score: forensicRiskScore,
    risk_breakdown:   riskBreakdown,
    fraud_signals:    signals,
    fraud_summary:    fraudSummaryText,
    ai_content_score: raw.ai_content?.score ?? 0,
    true_match_score: raw.true_match?.score ?? null,
    narrative:        raw.narrative,
    paragraph_ai_breakdown: raw.ai_content?.paragraph_ai_breakdown,
  };
}

// Transforms GET /scan/{id} response → normalised ScanResult
function transformGetScan(raw: RawGetScanResponse): ScanResult {
  const signalSource = raw.signals?.length ? raw.signals : (raw.fraud_summary?.signals ?? []);
  const signals: FraudSignal[] = signalSource.map(normalizeSignal);

  const total = raw.fraud_summary?.total ?? signals.length;
  const high  = raw.fraud_summary?.high ?? signals.filter(s => s.severity === 'HIGH').length;
  const fraudSummaryText =
    total === 0
      ? 'No fraud signals detected in this resume.'
      : `${total} signal${total > 1 ? 's' : ''} detected (${high} high severity).`;

  const trustScore = Math.round(raw.trust_score ?? 0);
  const signalRisk = signals.reduce((sum, s) => sum + (s.risk_points ?? 0), 0);
  const rawRisk = raw.forensic_risk_score ?? (raw.trust_score && typeof raw.trust_score === 'object' ? (raw.trust_score as any).forensic_risk_score : null);
  const forensicRiskScore = rawRisk != null
    ? Math.round(rawRisk)
    : Math.round(signalRisk);

  const riskBreakdown = (raw.risk_breakdown && Object.keys(raw.risk_breakdown).length > 0)
    ? raw.risk_breakdown
    : buildBreakdownFromSignals(signals);

  return {
    scan_id:          raw.scan_id,
    filename:         raw.filename,
    trust_score:      trustScore,
    trust_label:      raw.trust_label ?? 'UNKNOWN',
    forensic_risk_score: forensicRiskScore,
    risk_breakdown:   riskBreakdown,
    fraud_signals:    signals,
    fraud_summary:    fraudSummaryText,
    ai_content_score: raw.ai_content_score ?? 0,
    true_match_score: raw.true_match_score ?? null,
    narrative:        raw.narrative,
    paragraph_ai_breakdown: raw.ai_content?.paragraph_ai_breakdown,
    created_at:       raw.scanned_at,
    share_token:      raw.share_token ?? null,
  };
}

// ── API calls ─────────────────────────────────────────────────────────────────

export async function scanSingle(
  file: File,
  jobDescription?: string,
): Promise<ScanResult> {
  const form = new FormData();
  form.append('file', file);
  if (jobDescription?.trim()) {
    form.append('job_description', jobDescription.trim());
  }
  const { data } = await apiClient.post<RawPostScanResponse>('/scan', form);
  return transformPostScan(data);
}

export async function getScan(scanId: string | number): Promise<ScanResult> {
  const { data } = await apiClient.get<RawGetScanResponse>(`/scan/${scanId}`);
  return transformGetScan(data);
}

export async function scanBatch(
  files: File[],
  jobDescription?: string,
): Promise<{ results: ScanResult[]; duplicates: import('../types').DuplicateMatch[] }> {
  const form = new FormData();
  files.forEach((f) => form.append('files', f));
  if (jobDescription?.trim()) {
    form.append('job_description', jobDescription.trim());
  }
  const { data } = await apiClient.post<RawBatchResponse>('/scan/batch', form);

  // Batch leaderboard items are simplified — convert to ScanResult shape
  const results = (data.leaderboard ?? []).map((item) => ({
    scan_id:          item.scan_id,
    filename:         item.filename,
    trust_score:      item.trust_score ?? 0,
    trust_label:      item.trust_label ?? 'UNKNOWN',
    forensic_risk_score: item.forensic_risk_score != null ? Math.round(item.forensic_risk_score) : 0,
    fraud_signals:    [],   // not included in batch summary
    fraud_summary:    `${item.total_fraud_signals ?? 0} signal(s), ${item.high_fraud_signals ?? 0} high severity.`,
    ai_content_score: item.ai_content_score ?? 0,
    true_match_score: item.true_match_score ?? null,
    narrative: {
      verdict_title:           item.trust_label ?? '',
      recommendation:          '',
      summary:                 item.summary ?? '',
      key_factors:             [],
      limitations_disclaimer:  '',
    },
  }));

  return { results, duplicates: data.duplicate_matches ?? [] };
}

// ── Inspect ───────────────────────────────────────────────────────────────────

interface RawInspectResponse {
  scan_id: number;
  flagged_spans: RawSpan[];
  sample_clean_spans: RawSpan[];  // backend uses this field name
  signals: unknown[];
}

interface RawSpan {
  text: string;
  page: number;
  bbox?: number[] | null;
  font_size?: number;
  color_rgb?: number[] | null;
  font_color?: number[] | null;
  signal_types?: string[];
  matching_signals?: Array<{ signal_type: string }>;
  is_flagged?: boolean;
}

export async function inspectScan(scanId: string | number): Promise<InspectResult> {
  const { data } = await apiClient.get<RawInspectResponse>(`/scan/${scanId}/inspect`);

  const allSpans: TextSpan[] = [
    ...(data.sample_clean_spans ?? []).map((s) => ({
      text:         s.text ?? '',
      page:         s.page ?? 1,
      is_flagged:   false,
      signal_types: [],
      font_size:    s.font_size,
      color_rgb:    (s.color_rgb ?? s.font_color) as [number, number, number] | null ?? null,
    })),
    ...(data.flagged_spans ?? []).map((s) => ({
      text:         s.text ?? '',
      page:         s.page ?? 1,
      is_flagged:   true,
      signal_types: s.matching_signals?.map((m) => m.signal_type) ?? s.signal_types ?? [],
      font_size:    s.font_size,
      color_rgb:    (s.color_rgb ?? s.font_color) as [number, number, number] | null ?? null,
    })),
  ];

  // Group by page
  const pageMap = new Map<number, TextSpan[]>();
  allSpans.forEach((span) => {
    if (!pageMap.has(span.page)) pageMap.set(span.page, []);
    pageMap.get(span.page)!.push(span);
  });

  const pages: InspectPage[] = Array.from(pageMap.entries())
    .sort(([a], [b]) => a - b)
    .map(([page, spans]) => ({ page, spans }));

  return { scan_id: data.scan_id, pages };
}

export function getBadgeUrl(scanId: string | number): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';
  return `${base}/scan/${scanId}/badge.svg`;
}

export async function createShareLink(scanId: number): Promise<string> {
  const { data } = await apiClient.post(`/scan/${scanId}/share-link`);
  return data.share_token;
}

export async function revokeShareLink(scanId: number): Promise<void> {
  await apiClient.delete(`/scan/${scanId}/share-link`);
}

export async function getPublicScanResult(token: string): Promise<unknown> {
  const { data } = await apiClient.get(`/scan/public/${token}`);
  return data;
}

export async function getScanHistory(params?: {
  limit?: number;
  offset?: number;
  trust_label?: string;
}): Promise<ScanHistoryResponse> {
  const { data } = await apiClient.get<ScanHistoryResponse>('/scan', { params });
  return data;
}


