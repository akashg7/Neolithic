/**
 * Mandi-Setu Voice Module — useVoiceOut Hook (Track A: Voice-OUT)
 * React hook for generating and playing Marathi voice messages.
 * Integrates audioCache so repeated invocations play instantly from local cache.
 */

import { useState, useCallback, useRef } from 'react';
import type { WindowRes, PledgeQuote, RefusalReason } from './types';
import { verdictSentence, pledgeSentence, refusalSentence, worstCaseSentence, fullVerdictSentence } from './textTemplates';
import { getOrGenerateAudio } from './audioCache';
import { synthesizeWithFallback } from './fallbackTTS';

export interface UseVoiceOutReturn {
  isPlaying: boolean;
  isLoading: boolean;
  error: string | null;
  speak: (text: string) => Promise<void>;
  speakTemplate: (
    type: 'verdict' | 'full_verdict' | 'pledge' | 'refusal' | 'worst_case',
    data: any,
    qtyKg?: number
  ) => Promise<void>;
  stop: () => void;
}

export function useVoiceOut(): UseVoiceOutReturn {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const currentAudioRef = useRef<any>(null);

  const stop = useCallback(() => {
    if (currentAudioRef.current) {
      try {
        if (typeof currentAudioRef.current.pause === 'function') {
          currentAudioRef.current.pause();
        }
        if (typeof currentAudioRef.current.unloadAsync === 'function') {
          currentAudioRef.current.unloadAsync();
        }
      } catch (err) {
        console.warn('Error stopping audio:', err);
      }
      currentAudioRef.current = null;
    }
    setIsPlaying(false);
    setIsLoading(false);
  }, []);

  const speak = useCallback(
    async (text: string): Promise<void> => {
      if (!text || text.trim().length === 0) return;

      stop();
      setIsLoading(true);
      setError(null);

      try {
        // 1. Get cached audio or synthesize with fallback
        const audioSource = await getOrGenerateAudio(text, (t) => synthesizeWithFallback(t));

        setIsLoading(false);
        setIsPlaying(true);

        // 2. Play audio based on runtime environment (Web / Mobile Expo / Mock)
        if (typeof window !== 'undefined' && typeof window.Audio !== 'undefined' && audioSource.uri) {
          const sound = new window.Audio(audioSource.uri);
          currentAudioRef.current = sound;
          sound.onended = () => {
            setIsPlaying(false);
            currentAudioRef.current = null;
          };
          sound.onerror = () => {
            setIsPlaying(false);
            setError('Playback error');
            currentAudioRef.current = null;
          };
          await sound.play().catch((playErr) => {
            console.warn('Audio play prevented or failed:', playErr);
            setIsPlaying(false);
          });
        } else {
          // In Node/non-browser testing environment, simulate play duration
          console.log(`[Audio Playback] Speaking: "${text}" (Source: ${audioSource.uri.substring(0, 40)}...)`);
          // Mark finished after brief delay in tests
          setTimeout(() => {
            setIsPlaying(false);
          }, 300);
        }
      } catch (err: any) {
        console.warn('useVoiceOut speak error:', err);
        setError(err?.message || 'Voice playback failed');
        setIsPlaying(false);
        setIsLoading(false);
      }
    },
    [stop]
  );

  const speakTemplate = useCallback(
    async (
      type: 'verdict' | 'full_verdict' | 'pledge' | 'refusal' | 'worst_case',
      data: any,
      qtyKg?: number
    ): Promise<void> => {
      let sentence = '';
      switch (type) {
        case 'verdict':
          sentence = verdictSentence(data as WindowRes, qtyKg);
          break;
        case 'full_verdict':
          sentence = fullVerdictSentence(data as WindowRes, qtyKg);
          break;
        case 'pledge':
          sentence = pledgeSentence(data as PledgeQuote);
          break;
        case 'refusal':
          sentence = refusalSentence(data as RefusalReason);
          break;
        case 'worst_case':
          sentence = worstCaseSentence(data as number, qtyKg);
          break;
      }
      if (sentence) {
        await speak(sentence);
      }
    },
    [speak]
  );

  return {
    isPlaying,
    isLoading,
    error,
    speak,
    speakTemplate,
    stop,
  };
}
