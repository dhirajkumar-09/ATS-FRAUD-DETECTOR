// All TypeScript types mirroring backend API response schemas

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  email: string;
  organization: string;
  is_admin: boolean;
}

export interface UserOut {
  id: number;
  email: string;
  full_name: string | null;
  organization: string;
  is_admin: boolean;
}

export interface OrgSettingsOut {
  organization: string;
  near_white_threshold: number | null;
  hidden_font_size_pt: number | null;
  candidate_transparency_enabled: boolean;
}

export interface OrgSettingsIn {
  near_white_threshold: number | null;
  hidden_font_size_pt: number | null;
  candidate_transparency_enabled?: boolean | null;
}

// ── Scan Types ─────────────────────────────────────────────────────────────────

export type TrustLabel = 'TRUSTED' | 'SUSPICIOUS' | 'HIGH RISK' | 'FRAUD' | string;

export interface FraudSignal {
  signal_type: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  description: string;
  page?: number | null;
  detail?: string | null;
}

export interface Narrative {
  verdict_title: string;
  recommendation: string;
  summary: string;
  key_factors: string[];
  limitations_disclaimer: string;
}

export interface AIParagraphBreakdown {
  paragraph_index: number;
  page: number;
  text_snippet: string;
  ai_score: number;
  confidence: string;
  contributing_factors: string[];
}

// Normalised ScanResult — what the frontend always works with
export interface ScanResult {
  scan_id: string | number;
  share_token?: string | null;
  filename: string;
  trust_score: number;          // 0-1
  trust_label: TrustLabel;
  fraud_signals: FraudSignal[];
  fraud_summary: string;        // human-readable summary text
  ai_content_score: number;     // 0-1
  true_match_score: number | null; // 0-1 or null
  narrative: Narrative;
  paragraph_ai_breakdown?: AIParagraphBreakdown[];
  created_at?: string;
}

// ── Raw backend response shapes ───────────────────────────────────────────────

// What POST /scan actually returns
export interface RawPostScanResponse {
  scan_id: number;
  share_token?: string | null;
  filename: string;
  trust_score: { score: number; label: string; emoji?: string };
  fraud_summary: {
    total: number;
    high: number;
    medium: number;
    low: number;
    signals: RawSignal[];
  };
  ai_content: { 
    score: number; 
    clean_word_count?: number; 
    flagged_word_count?: number;
    paragraph_ai_breakdown?: AIParagraphBreakdown[];
  };
  true_match: { score: number } | null;
  narrative: Narrative;
}

// What GET /scan/{id} returns
export interface RawGetScanResponse {
  scan_id: number;
  share_token?: string | null;
  filename: string;
  trust_score: number;
  trust_label: string;
  ai_content_score: number;
  true_match_score: number | null;
  fraud_summary: {
    total: number;
    high: number;
    medium: number;
    low: number;
    signals: RawSignal[];
  };
  ai_content?: {
    paragraph_ai_breakdown?: AIParagraphBreakdown[];
  };
  signals: RawSignal[];
  narrative: Narrative;
  scanned_at?: string;
}

export interface RawBatchItem {
  scan_id: number;
  filename: string;
  trust_score: number;
  trust_label: string;
  ai_content_score: number;
  true_match_score: number | null;
  total_fraud_signals: number;
  high_fraud_signals: number;
  summary?: string;
}

export interface DuplicateMatch {
  scan_id_a: number;
  scan_id_b: number;
  similarity_score: number;
  shared_phrases: string[];
}

export interface RawBatchResponse {
  leaderboard: RawBatchItem[];
  total_submitted: number;
  total_processed: number;
  total_failed: number;
  errors: { filename: string; error: string }[];
  duplicate_matches?: DuplicateMatch[];
}

export interface RawSignal {
  signal_type: string;
  severity: string;   // lowercase from backend: "high" | "medium" | "low"
  page?: number | null;
  description: string;
  evidence_text?: string | null;
  bbox?: number[] | null;
}

// ── Inspect Types ─────────────────────────────────────────────────────────────

export interface TextSpan {
  text: string;
  page: number;
  is_flagged: boolean;
  signal_types: string[];
  x0?: number;
  y0?: number;
  x1?: number;
  y1?: number;
  font_size?: number;
  color_rgb?: [number, number, number] | null;
}

export interface InspectPage {
  page: number;
  spans: TextSpan[];
}

export interface InspectResult {
  scan_id: string | number;
  pages: InspectPage[];
}

// ── Health ────────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
}
