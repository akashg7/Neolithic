/**
 * AgentContext — owns the conversation, the drawer, and "what screen is the
 * farmer looking at". Mounted once in `FarmerRoot`, inside NavigationContainer.
 *
 * ★ Screen awareness comes from `navigationRef`, not from each screen
 *   reporting in — no screen has to know the chatbot exists.
 * ★ All traffic goes through `sendChatMessage` (lib/agentClient.ts); this file
 *   never knows whether the answer is mocked.
 */
import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';

import { USE_FIXTURES } from '../config';
import { navigationRef } from '../navigation/navigationRef';
import { useT } from './i18n';
import { mandiRef } from './liveMarket';
import { staticMarketStore } from './staticMarketStore';
import { sendChatMessage, sendVoiceChatMessage, resetAgentSession } from './agentClient';
import { promptsFor } from './chatPrompts';
import { speakSmart } from './voice';
import type { AgentChatResponse, ChatMessage, ScreenContext, UiAction } from './agentTypes';

const TAB_FOR_SCREEN: Record<string, string> = {
  S4_Home: 'Home',
  S9_Verdict: 'Home',
  S10_CostBreakdown: 'Home',
  S13_CropLoan: 'Home',
  PricesIndex: 'Prices',
  S8_ModelCard: 'Prices',
  S15_MyLots: 'MyLots',
  S19_Quantity: 'MyLots',
  S22_PricePublish: 'MyLots',
  S31_DealsList: 'Deals',
  S37_Talks: 'Talks',
};

interface AgentContextValue {
  isOpen: boolean;
  open: () => void;
  close: () => void;
  messages: ChatMessage[];
  isThinking: boolean;
  screen: ScreenContext;
  starters: string[];
  send: (text: string) => Promise<void>;
  sendVoice: (audioUriOrBlob: unknown, transcribeFallback?: () => Promise<string>) => Promise<void>;
  retry: (id: string) => Promise<void>;
  reset: () => void;
  runUiAction: (action: Pick<UiAction, 'target_screen' | 'params'>) => void;
}

const EMPTY_SCREEN: ScreenContext = {
  current_screen: 'S4_Home',
  active_commodity_id: null,
  active_market_id: null,
  active_lot_id: null,
};

const Ctx = createContext<AgentContextValue | null>(null);

// ★ A session id is a conversation key, not a credential: the backend must
//   bind it to the JWT user and reject another user's id (Member 5). Still,
//   prefer a CSPRNG id where the runtime has one (web, modern Hermes).
const newSession = () => {
  const c = (globalThis as { crypto?: { randomUUID?: () => string } }).crypto;
  const id = c?.randomUUID ? c.randomUUID() : `${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
  return `sess_${id}`;
};
let seq = 0;
const mid = () => `m${Date.now().toString(36)}${seq++}`;

function readScreen(): ScreenContext {
  if (!navigationRef.isReady()) return EMPTY_SCREEN;
  const r = navigationRef.getCurrentRoute();
  if (!r) return EMPTY_SCREEN;
  // Home/Market keep crop and mandi in the market store, not in route params.
  const m = staticMarketStore.getState();
  const p = (r.params ?? {}) as Record<string, unknown>;
  const s = (k: string) => (typeof p[k] === 'string' ? (p[k] as string) : null);
  return {
    current_screen: r.name,
    active_commodity_id: s('commodity_id') ?? m.selectedCrop.name,
    active_market_id: s('market_id') ?? mandiRef(m.selectedMandi),
    active_lot_id: s('lot_id'),
  };
}

export function AgentProvider({ children }: { children: React.ReactNode }) {
  const { locale } = useT();
  const [isOpen, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isThinking, setThinking] = useState(false);
  const [screen, setScreen] = useState<ScreenContext>(EMPTY_SCREEN);
  const sessionRef = useRef(newSession());
  const epochRef = useRef(0);

  useEffect(() => {
    const sync = () => setScreen(prev => {
      const next = readScreen();
      return JSON.stringify(prev) === JSON.stringify(next) ? prev : next;
    });
    sync();
    // The container may not be mounted yet when this provider first renders.
    const poll: ReturnType<typeof setInterval> = setInterval(() => navigationRef.isReady() && (sync(), clearInterval(poll)), 250);
    const unsub = navigationRef.addListener('state', sync);
    const unsubMarket = staticMarketStore.subscribe(sync);
    return () => {
      clearInterval(poll);
      unsub();
      unsubMarket();
    };
  }, []);

  const ask = useCallback(
    async (text: string) => {
      const epoch = epochRef.current;
      setThinking(true);
      try {
        const response: AgentChatResponse = await sendChatMessage({
          session_id: sessionRef.current,
          message: text,
          locale,
          screen_context: readScreen(),
          include_audio: false,
        });
        if (epoch !== epochRef.current) return;
        setMessages(m => [...m, { id: mid(), role: 'assistant', response, at: Date.now() }]);
      } catch {
        if (epoch !== epochRef.current) return;
        setMessages(m => [...m, { id: mid(), role: 'error', text: '', retryText: text, at: Date.now() }]);
      } finally {
        if (epoch === epochRef.current) setThinking(false);
      }
    },
    [locale],
  );

  const send = useCallback(
    async (raw: string) => {
      const text = raw.trim();
      if (!text || isThinking) return;
      setMessages(m => [...m, { id: mid(), role: 'user', text, at: Date.now() }]);
      await ask(text);
    },
    [ask, isThinking],
  );

  const sendVoice = useCallback(
    async (audioUriOrBlob: unknown, transcribeFallback?: () => Promise<string>) => {
      if (isThinking) return;
      if (USE_FIXTURES && transcribeFallback) {
        const spoken = (await transcribeFallback()).trim();
        if (spoken) await send(spoken);
        return;
      }

      const epoch = epochRef.current;
      const fallbackLabel = locale === 'mr' ? 'आवाज संदेश' : locale === 'hi' ? 'आवाज़ संदेश' : 'Voice message';
      setThinking(true);
      try {
        let response = await sendVoiceChatMessage(audioUriOrBlob, {
          session_id: sessionRef.current,
          locale,
          screen_context: readScreen(),
          include_audio: true,
        });
        if (epoch !== epochRef.current) return;

        const rawTranscript = (response.transcript || '').trim();
        const isRealTranscript = rawTranscript.length > 0 && rawTranscript !== '<audio>';
        let finalTranscript = isRealTranscript ? rawTranscript : '';

        if (!isRealTranscript || response.error_code === 'LLM_UNAVAILABLE' || response.error_code === 'TRANSLATION_UNAVAILABLE') {
          if (isRealTranscript) {
            response = await sendChatMessage({
              session_id: sessionRef.current,
              message: rawTranscript,
              locale,
              screen_context: readScreen(),
              include_audio: false,
            });
            if (epoch !== epochRef.current) return;
          } else if (transcribeFallback) {
            try {
              const spoken = (await transcribeFallback()).trim();
              if (epoch !== epochRef.current) return;
              if (spoken) {
                finalTranscript = spoken;
                response = await sendChatMessage({
                  session_id: sessionRef.current,
                  message: spoken,
                  locale,
                  screen_context: readScreen(),
                  include_audio: false,
                });
                if (epoch !== epochRef.current) return;
              }
            } catch {
              /* keep original fallback response below */
            }
          }
        }

        setMessages(m => [
          ...m,
          { id: mid(), role: 'user', text: finalTranscript || fallbackLabel, at: Date.now() },
          { id: mid(), role: 'assistant', response, at: Date.now() },
        ]);
        if (response.audio_base64 && response.reply_text) {
          void speakSmart(response.reply_text, locale, response.audio_base64).catch(() => {});
        }
      } catch {
        if (epoch !== epochRef.current) return;
        if (transcribeFallback) {
          try {
            const spoken = (await transcribeFallback()).trim();
            if (spoken && epoch === epochRef.current) {
              setThinking(false);
              await send(spoken);
              return;
            }
          } catch {
            /* fall through to error bubble */
          }
        }
        setMessages(m => [...m, { id: mid(), role: 'error', text: '', retryText: '', at: Date.now() }]);
      } finally {
        if (epoch === epochRef.current) setThinking(false);
      }
    },
    [isThinking, locale, send],
  );

  const retry = useCallback(
    async (id: string) => {
      const failed = messages.find(m => m.id === id);
      if (!failed || failed.role !== 'error') return;
      setMessages(m => m.filter(x => x.id !== id));
      await ask(failed.retryText);
    },
    [ask, messages],
  );

  const reset = useCallback(() => {
    const prev = sessionRef.current;
    void resetAgentSession(prev);
    epochRef.current += 1;
    sessionRef.current = newSession();
    setMessages([]);
    setThinking(false);
  }, []);

  const runUiAction = useCallback((a: Pick<UiAction, 'target_screen' | 'params'>) => {
    setOpen(false);
    if (!navigationRef.isReady()) return;
    const tab = TAB_FOR_SCREEN[a.target_screen];
    try {
      if (tab) {
        navigationRef.navigate('FarmerTabs', {
          screen: tab,
          params: { screen: a.target_screen, params: a.params },
        });
      } else {
        navigationRef.navigate(a.target_screen, a.params as object | undefined);
      }
    } catch {
      /* unknown route: stay put rather than crash a farmer mid-sale */
    }
  }, []);

  const value = useMemo<AgentContextValue>(
    () => ({
      isOpen,
      open: () => setOpen(true),
      close: () => setOpen(false),
      messages,
      isThinking,
      screen,
      starters: promptsFor(screen.current_screen, locale),
      send,
      sendVoice,
      retry,
      reset,
      runUiAction,
    }),
    [isOpen, messages, isThinking, screen, locale, send, sendVoice, retry, reset, runUiAction],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAgent(): AgentContextValue {
  const v = useContext(Ctx);
  if (!v) throw new Error('useAgent must be used inside <AgentProvider>');
  return v;
}
