'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Bot, X, Send, Loader2, Sparkles, ChevronDown,
  Copy, Check, AlertCircle, MessageCircle
} from 'lucide-react';
import { sendChatMessage, buildScanContext, type ChatMessage } from '@/lib/gemini';
import type { ScanResult } from '@/lib/types';
import { cn } from '@/lib/utils';

interface Props {
  scanResult?: ScanResult | null;
}

const WELCOME = `Hi! I'm your AI forensic analyst.

I can help you:
• **Interpret** scan results and fraud signals
• **Explain** what each signal means
• **Suggest** next steps for your hiring decision
• **Answer** questions about the ATS Fraud Detector

${'' /* placeholder, replaced contextually */}`;

function MarkdownText({ text }: { text: string }) {
  // Very simple markdown: bold, bullet, code
  const lines = text.split('\n');
  return (
    <div className="space-y-1 text-sm leading-relaxed">
      {lines.map((line, i) => {
        if (line.startsWith('## ')) {
          return (
            <p key={i} className="font-bold text-[#3CB697] mt-3 mb-1 text-xs uppercase tracking-widest">
              {line.slice(3)}
            </p>
          );
        }
        if (line.startsWith('• ') || line.startsWith('- ')) {
          const content = line.slice(2);
          return (
            <p key={i} className="flex gap-2">
              <span className="text-[#3CB697] flex-shrink-0 mt-0.5">•</span>
              <span dangerouslySetInnerHTML={{ __html: boldify(content) }} />
            </p>
          );
        }
        if (line.trim() === '') return <div key={i} className="h-1" />;
        return (
          <p key={i} dangerouslySetInnerHTML={{ __html: boldify(line) }} />
        );
      })}
    </div>
  );
}

function boldify(text: string) {
  return text.replace(/\*\*(.+?)\*\*/g, '<strong class="text-[#E8E6DF] font-semibold">$1</strong>');
}

export default function AIAssistant({ scanResult }: Props) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'model', text: WELCOME },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Focus input when opened
  useEffect(() => {
    if (open && !minimized) {
      setTimeout(() => inputRef.current?.focus(), 300);
    }
  }, [open, minimized]);

  const scanContext = scanResult ? buildScanContext(scanResult) : undefined;

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: ChatMessage = { role: 'user', text };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput('');
    setLoading(true);
    setError(null);

    try {
      const reply = await sendChatMessage(newMessages, scanContext);
      setMessages((prev) => [...prev, { role: 'model', text: reply }]);
    } catch (e: unknown) {
      const msg = (e as Error).message ?? 'Failed to get response';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const copyLastResponse = () => {
    const last = [...messages].reverse().find((m) => m.role === 'model');
    if (last) {
      navigator.clipboard.writeText(last.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const quickPrompts = scanResult
    ? [
        'Explain the fraud signals found',
        'Should I proceed with this candidate?',
        'What does the trust score mean?',
        'Summarize the key risks',
      ]
    : [
        'How does trust scoring work?',
        'What is ATS manipulation?',
        'How is AI content detected?',
        'What signals indicate fraud?',
      ];

  return (
    <>
      {/* Floating bubble */}
      <motion.button
        onClick={() => setOpen((o) => !o)}
        whileHover={{ scale: 1.08 }}
        whileTap={{ scale: 0.95 }}
        className={cn(
          'fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full flex items-center justify-center',
          'bg-[#3CB697] text-[#0D0F14] shadow-[0_0_30px_rgba(60,182,151,0.4)]',
          'transition-all duration-200',
          open && 'rotate-12',
        )}
        aria-label="Open AI Assistant"
      >
        <AnimatePresence mode="wait">
          {open ? (
            <motion.div key="close" initial={{ rotate: -90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: 90, opacity: 0 }} transition={{ duration: 0.15 }}>
              <X size={22} />
            </motion.div>
          ) : (
            <motion.div key="bot" initial={{ rotate: 90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: -90, opacity: 0 }} transition={{ duration: 0.15 }}>
              <MessageCircle size={22} />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.button>

      {/* Chat panel */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 24, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.95 }}
            transition={{ type: 'spring', damping: 24, stiffness: 300 }}
            className="fixed bottom-24 right-6 z-50 w-[380px] max-w-[calc(100vw-2rem)] rounded-2xl overflow-hidden shadow-2xl"
            style={{
              background: '#171A22',
              border: '1px solid rgba(60,182,151,0.2)',
              boxShadow: '0 0 0 1px rgba(60,182,151,0.08), 0 24px 64px rgba(0,0,0,0.5), 0 0 60px rgba(60,182,151,0.06) inset',
            }}
          >
            {/* Header */}
            <div className="flex items-center gap-3 px-4 py-3 border-b border-[rgba(60,182,151,0.12)] bg-[#0D0F14]/60">
              <div className="w-7 h-7 rounded-lg bg-[#3CB697]/15 border border-[#3CB697]/25 flex items-center justify-center">
                <Bot size={14} className="text-[#3CB697]" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-[#E8E6DF]" style={{ fontFamily: 'var(--font-space-grotesk)' }}>
                  AI Forensic Analyst
                </p>
                <p className="text-[10px] text-[#3CB697] font-mono">
                  {scanResult ? `Analyzing: ${scanResult.filename}` : 'Powered by AI'}
                </p>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={copyLastResponse}
                  className="p-1.5 rounded-lg text-[#7A8099] hover:text-[#E8E6DF] hover:bg-[#1E2230] transition-colors"
                  title="Copy last response"
                >
                  {copied ? <Check size={13} className="text-[#3CB697]" /> : <Copy size={13} />}
                </button>
                <button
                  onClick={() => setMinimized((m) => !m)}
                  className="p-1.5 rounded-lg text-[#7A8099] hover:text-[#E8E6DF] hover:bg-[#1E2230] transition-colors"
                >
                  <ChevronDown size={13} className={minimized ? 'rotate-180' : ''} />
                </button>
              </div>
            </div>

            <AnimatePresence>
              {!minimized && (
                <motion.div
                  initial={{ height: 0 }}
                  animate={{ height: 'auto' }}
                  exit={{ height: 0 }}
                  className="overflow-hidden"
                >
                  {/* Messages */}
                  <div className="h-72 overflow-y-auto px-4 py-3 space-y-3">
                    {messages.map((msg, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={cn('flex gap-2', msg.role === 'user' ? 'justify-end' : 'justify-start')}
                      >
                        {msg.role === 'model' && (
                          <div className="w-6 h-6 rounded-full bg-[#3CB697]/15 border border-[#3CB697]/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                            <Bot size={12} className="text-[#3CB697]" />
                          </div>
                        )}
                        <div
                          className={cn(
                            'max-w-[85%] rounded-xl px-3 py-2',
                            msg.role === 'user'
                              ? 'bg-[#3CB697]/15 border border-[#3CB697]/20 text-[#E8E6DF]'
                              : 'bg-[#1E2230] text-[#E8E6DF]/80',
                          )}
                        >
                          {msg.role === 'model'
                            ? <MarkdownText text={msg.text} />
                            : <p className="text-sm">{msg.text}</p>
                          }
                        </div>
                      </motion.div>
                    ))}

                    {loading && (
                      <div className="flex gap-2 items-center">
                        <div className="w-6 h-6 rounded-full bg-[#3CB697]/15 border border-[#3CB697]/20 flex items-center justify-center">
                          <Sparkles size={10} className="text-[#3CB697]" />
                        </div>
                        <div className="bg-[#1E2230] rounded-xl px-3 py-2.5 flex items-center gap-2">
                          <Loader2 size={12} className="text-[#3CB697] animate-spin" />
                          <span className="text-xs text-[#7A8099]">Analyzing…</span>
                        </div>
                      </div>
                    )}

                    {error && (
                      <div className="flex gap-2 items-start">
                        <AlertCircle size={14} className="text-[#E05252] flex-shrink-0 mt-0.5" />
                        <p className="text-xs text-[#E05252] leading-relaxed">{error}</p>
                      </div>
                    )}

                    <div ref={bottomRef} />
                  </div>

                  {/* Quick prompts */}
                  <div className="px-4 pb-2 flex flex-wrap gap-1.5">
                    {quickPrompts.map((q) => (
                      <button
                        key={q}
                        onClick={() => { setInput(q); inputRef.current?.focus(); }}
                        className="text-[10px] px-2 py-1 rounded-full bg-[#0D0F14] border border-[rgba(60,182,151,0.15)] text-[#7A8099] hover:text-[#3CB697] hover:border-[#3CB697]/30 transition-colors"
                      >
                        {q}
                      </button>
                    ))}
                  </div>

                  {/* Input */}
                  <div className="px-3 pb-3">
                    <div className="flex items-end gap-2 bg-[#0D0F14] rounded-xl border border-[rgba(60,182,151,0.15)] focus-within:border-[#3CB697]/40 transition-colors px-3 py-2">
                      <textarea
                        ref={inputRef}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKey}
                        placeholder="Ask about this scan…"
                        rows={1}
                        style={{ resize: 'none' }}
                        className="flex-1 bg-transparent text-sm text-[#E8E6DF] placeholder:text-[#7A8099] outline-none min-h-[24px] max-h-[96px] overflow-y-auto"
                      />
                      <motion.button
                        onClick={send}
                        disabled={!input.trim() || loading}
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        className="p-1.5 rounded-lg bg-[#3CB697] text-[#0D0F14] disabled:opacity-40 disabled:cursor-not-allowed transition-opacity flex-shrink-0"
                        aria-label="Send message"
                      >
                        <Send size={13} />
                      </motion.button>
                    </div>
                    <p className="text-[10px] text-[#7A8099] mt-1.5 px-1">
                      Enter to send · Shift+Enter for new line
                    </p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
