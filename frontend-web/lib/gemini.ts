import { GoogleGenerativeAI } from '@google/generative-ai';
import type { ScanResult } from '../types';

const API_KEY = process.env.NEXT_PUBLIC_GEMINI_API_KEY ?? '';

function getClient() {
  if (!API_KEY || API_KEY === 'your_gemini_api_key_here') {
    throw new Error('Gemini API key not configured. Add NEXT_PUBLIC_GEMINI_API_KEY to .env.local');
  }
  return new GoogleGenerativeAI(API_KEY);
}

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
  const model = genAI.getGenerativeModel({
    model: 'gemini-2.0-flash',
    systemInstruction: SYSTEM_PROMPT + (scanContext ? `\n\n${scanContext}` : ''),
  });

  const chat = model.startChat({
    history: messages.slice(0, -1).map((m) => ({
      role: m.role,
      parts: [{ text: m.text }],
    })),
  });

  const lastMessage = messages[messages.length - 1];
  const result = await chat.sendMessage(lastMessage.text);
  return result.response.text();
}

// ── One-shot report generation ────────────────────────────────────────────────
export async function generateEnhancedReport(result: ScanResult): Promise<string> {
  const genAI = getClient();
  const model = genAI.getGenerativeModel({ model: 'gemini-2.0-flash' });

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
}

// ── Quick insight (short, for inline use) ─────────────────────────────────────
export async function getQuickInsight(result: ScanResult, question: string): Promise<string> {
  const genAI = getClient();
  const model = genAI.getGenerativeModel({
    model: 'gemini-2.0-flash',
    systemInstruction: SYSTEM_PROMPT,
  });

  const prompt = `${buildScanContext(result)}\n\nQuestion: ${question}`;
  const response = await model.generateContent(prompt);
  return response.response.text();
}
