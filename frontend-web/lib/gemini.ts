import { GoogleGenerativeAI, GoogleGenerativeAIError } from '@google/generative-ai';
import type { ScanResult } from './types';

// ── API Key handling ──────────────────────────────────────────────────────────

const API_KEY = process.env.NEXT_PUBLIC_GEMINI_API_KEY ?? '';

/**
 * Validates the Gemini API key format.
 * Google AI Studio keys always start with "AIzaSy" and are 39 characters long.
 */
function validateApiKey(key: string): { valid: boolean; reason?: string } {
  if (!key || key.trim() === '') {
    return { valid: false, reason: 'Gemini API key is missing. Add NEXT_PUBLIC_GEMINI_API_KEY to .env.local' };
  }
  if (key === 'your_gemini_api_key_here' || key === 'REPLACE_WITH_YOUR_GEMINI_API_KEY') {
    return { valid: false, reason: 'Gemini API key is still set to a placeholder. Replace it with your real key from https://aistudio.google.com/app/apikey' };
  }
  if (key.length < 30) {
    return { valid: false, reason: 'Gemini API key appears too short. Verify it was copied correctly.' };
  }
  return { valid: true };
}

/**
 * Returns a user-friendly error message from a Gemini SDK or network error.
 */
function parseGeminiError(error: unknown): string {
  // GoogleGenerativeAIError has a structured message
  if (error instanceof GoogleGenerativeAIError) {
    const msg = error.message ?? '';
    if (msg.includes('API_KEY_INVALID') || msg.includes('API key not valid')) {
      return 'Gemini API key is invalid or has been revoked. Please generate a new key at https://aistudio.google.com/app/apikey';
    }
    if (msg.includes('PERMISSION_DENIED')) {
      return 'Gemini API key does not have permission to use this model. Check your Google AI Studio project settings.';
    }
    if (msg.includes('RESOURCE_EXHAUSTED') || msg.includes('quota')) {
      return 'Gemini API quota exceeded. Please check your usage limits at https://aistudio.google.com';
    }
    if (msg.includes('SAFETY') || msg.includes('safety')) {
      return 'Gemini blocked this request due to safety filters. Try rephrasing your input.';
    }
    if (msg.includes('MODEL_NOT_FOUND') || msg.includes('not found')) {
      return 'Gemini model not found. The selected model may not be available in your region or account tier.';
    }
    return `Gemini API error: ${msg}`;
  }

  // Network / fetch errors
  if (error instanceof TypeError && (error.message.includes('fetch') || error.message.includes('network'))) {
    return 'Network error: unable to reach Gemini API. Check your internet connection.';
  }

  // Generic Error
  if (error instanceof Error) {
    return error.message || 'An unexpected error occurred with the Gemini API.';
  }

  return 'An unknown error occurred. Please try again.';
}

/**
 * Creates a validated Gemini client. Throws a descriptive error if the key is missing or malformed.
 */
function getClient(): GoogleGenerativeAI {
  const { valid, reason } = validateApiKey(API_KEY);
  if (!valid) {
    throw new Error(reason);
  }
  return new GoogleGenerativeAI(API_KEY);
}

// ── Model name ────────────────────────────────────────────────────────────────
const GEMINI_MODEL = 'gemini-3.6-flash';

// ── System prompt ─────────────────────────────────────────────────────────────
const SYSTEM_PROMPT = `You are an expert forensic resume analyst and AI assistant for the ATS Fraud Detector platform.
You help recruiters understand scan results, interpret fraud signals, and make hiring decisions.
You have deep knowledge of:
- ATS (Applicant Tracking System) manipulation techniques
- Resume fraud patterns: hidden text, keyword stuffing, near-white text, font size manipulation
- Trust scoring methodology
- AI-generated content detection
- Job description matching

Be concise, professional, and data-driven. Use the scan data provided in context.
Format responses with clear sections. Use bullet points for lists.
Do NOT make up scan data — only reference what's provided.`;

// ── Build context string from a scan result ───────────────────────────────────
export function buildScanContext(result: ScanResult): string {
  const signals = result.fraud_signals
    .map((s) => `  • [${s.severity}] ${s.signal_type}: ${s.description}`)
    .join('\n') || '  • None detected';

  const trustPct = Math.round((result.trust_score ?? 0) * 100);
  const aiPct    = Math.round((result.ai_content_score ?? 0) * 100);
  const matchPct = result.true_match_score != null
    ? `${Math.round(result.true_match_score * 100)}%`
    : 'N/A (no JD provided)';

  return `
=== SCAN CONTEXT ===
File: ${result.filename}
Trust Score: ${trustPct}/100 (${result.trust_label})
AI Content Score: ${aiPct}%
Job Match Score: ${matchPct}

Fraud Signals (${result.fraud_signals.length} total):
${signals}

Verdict: ${result.narrative?.verdict_title ?? 'N/A'}
Summary: ${result.narrative?.summary ?? 'N/A'}
Recommendation: ${result.narrative?.recommendation ?? 'N/A'}

Key Factors:
${result.narrative?.key_factors?.map((f) => `  • ${f}`).join('\n') ?? '  • N/A'}
===================
`.trim();
}

// ── Chat session ──────────────────────────────────────────────────────────────
export interface ChatMessage {
  role: 'user' | 'model';
  text: string;
}

export async function sendChatMessage(
  messages: ChatMessage[],
  scanContext?: string,
): Promise<string> {
  const genAI = getClient();
  try {
    const model = genAI.getGenerativeModel({
      model: GEMINI_MODEL,
      systemInstruction: SYSTEM_PROMPT + (scanContext ? `\n\n${scanContext}` : ''),
    });

    // Gemini API requires the first message in history to be from the user.
    // The UI starts with a welcome message from the model, so we must remove it from history.
    let history = messages.slice(0, -1);
    if (history.length > 0 && history[0].role === 'model') {
      history = history.slice(1);
    }

    const chat = model.startChat({
      history: history.map((m) => ({
        role: m.role,
        parts: [{ text: m.text }],
      })),
    });

    const lastMessage = messages[messages.length - 1];
    const result = await chat.sendMessage(lastMessage.text);
    return result.response.text();
  } catch (error) {
    throw new Error(parseGeminiError(error));
  }
}

// ── One-shot report generation ────────────────────────────────────────────────
export async function generateEnhancedReport(result: ScanResult): Promise<string> {
  const genAI = getClient();
  try {
    const model = genAI.getGenerativeModel({ model: GEMINI_MODEL });

    const prompt = `${SYSTEM_PROMPT}

${buildScanContext(result)}

Generate a comprehensive forensic report for this resume scan. Structure it as follows:

## Executive Summary
## Trust Assessment
## Fraud Signal Analysis
## AI Content Analysis
## Job Fit Evaluation (if match score available)
## Hiring Recommendation
## Risk Mitigation Steps

Be thorough but concise. Use professional language suitable for a hiring team.`;

    const response = await model.generateContent(prompt);
    return response.response.text();
  } catch (error) {
    throw new Error(parseGeminiError(error));
  }
}

// ── Quick insight (short, for inline use) ─────────────────────────────────────
export async function getQuickInsight(result: ScanResult, question: string): Promise<string> {
  const genAI = getClient();
  try {
    const model = genAI.getGenerativeModel({
      model: GEMINI_MODEL,
      systemInstruction: SYSTEM_PROMPT,
    });

    const prompt = `${buildScanContext(result)}\n\nQuestion: ${question}`;
    const response = await model.generateContent(prompt);
    return response.response.text();
  } catch (error) {
    throw new Error(parseGeminiError(error));
  }
}

// ── Diagnostic connection test ─────────────────────────────────────────────────
/**
 * Tests the Gemini API connection. Returns { ok: true } on success, or
 * { ok: false, error: string } with a human-readable error message.
 *
 * Usage (run from frontend-web/ root):
 *   node -e "import('./lib/gemini.js').then(m => m.testGeminiConnection().then(console.log))"
 */
export async function testGeminiConnection(): Promise<{ ok: boolean; error?: string; model?: string }> {
  const { valid, reason } = validateApiKey(API_KEY);
  if (!valid) {
    return { ok: false, error: reason };
  }

  try {
    const genAI = new GoogleGenerativeAI(API_KEY);
    const model = genAI.getGenerativeModel({ model: GEMINI_MODEL });
    const response = await model.generateContent('Respond with exactly: "ATS Fraud Detector connection OK"');
    void response.response.text();
    return { ok: true, model: GEMINI_MODEL };
  } catch (error) {
    return { ok: false, error: parseGeminiError(error) };
  }
}

// ── Key status utility (for UI diagnostics) ───────────────────────────────────
export function getApiKeyStatus(): { configured: boolean; valid: boolean; reason?: string } {
  const { valid, reason } = validateApiKey(API_KEY);
  return {
    configured: !!API_KEY && API_KEY.trim() !== '',
    valid,
    reason,
  };
}
