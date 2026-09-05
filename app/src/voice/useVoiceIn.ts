/**
 * Mandi-Setu Voice Module — useVoiceIn Hook (Track B: B6)
 * React hook for recording farmer speech, executing ASR with fallback ladder,
 * auto-stopping after 10 seconds, and triggering structured field extraction.
 */

import { useState, useRef, useCallback } from 'react';
import { VOICE_CONFIG } from './config';
import { recognizeWithFallback } from './fallbackASR';
import { parseLotCreationSpeech } from './lotCreationParser';
import type { ParsedLotFields, ParsedRegistrationField, RegistrationField } from './types';

export interface UseVoiceInReturn {
  isListening: boolean;
  isProcessing: boolean;
  error: string | null;
  startListening: (
    mode: 'lot_creation' | 'registration_field',
    fieldName?: RegistrationField
  ) => Promise<void>;
  stopListening: () => Promise<void>;
  cancel: () => void;
}

export function useVoiceIn(
  onResult: (fields: ParsedLotFields | ParsedRegistrationField) => void,
  onError?: (error: Error) => void
): UseVoiceInReturn {
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<any>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const autoStopTimeoutRef = useRef<any>(null);
  const currentModeRef = useRef<{ mode: 'lot_creation' | 'registration_field'; fieldName?: RegistrationField }>({
    mode: 'lot_creation',
  });

  const clearTimers = () => {
    if (autoStopTimeoutRef.current) {
      clearTimeout(autoStopTimeoutRef.current);
      autoStopTimeoutRef.current = null;
    }
  };

  const cancel = useCallback(() => {
    clearTimers();
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try {
        mediaRecorderRef.current.stop();
      } catch {
        // ignore
      }
    }
    setIsListening(false);
    setIsProcessing(false);
  }, []);

  const processAudioData = async (audioBlob: Blob) => {
    setIsProcessing(true);
    setError(null);

    try {
      // 1. Recognize speech with fallback ladder
      const asrResult = await recognizeWithFallback(audioBlob);

      // 2. Parse based on requested mode
      if (currentModeRef.current.mode === 'lot_creation') {
        const parsedLot = parseLotCreationSpeech(asrResult.raw_transcript, asrResult.confidence);
        onResult(parsedLot);
      } else if (currentModeRef.current.mode === 'registration_field' && currentModeRef.current.fieldName) {
        const fieldName = currentModeRef.current.fieldName;
        const regResult: ParsedRegistrationField = {
          field_name: fieldName,
          raw_value: asrResult.raw_transcript.trim(),
          confidence: asrResult.confidence,
        };
        onResult(regResult);
      }
    } catch (err: any) {
      console.warn('useVoiceIn transcription failed:', err);
      const errMsg = err?.message || 'Voice input unavailable';
      setError(errMsg);
      if (onError) onError(err);
    } finally {
      setIsProcessing(false);
    }
  };

  const stopListening = useCallback(async (): Promise<void> => {
    clearTimers();
    setIsListening(false);

    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
  }, []);

  const startListening = useCallback(
    async (
      mode: 'lot_creation' | 'registration_field',
      fieldName?: RegistrationField
    ): Promise<void> => {
      cancel();
      setError(null);
      currentModeRef.current = { mode, fieldName };
      audioChunksRef.current = [];

      try {
        // Browser / Web MediaRecorder API
        if (typeof navigator !== 'undefined' && navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          const recorder = new MediaRecorder(stream);
          mediaRecorderRef.current = recorder;

          recorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
              audioChunksRef.current.push(event.data);
            }
          };

          recorder.onstop = async () => {
            stream.getTracks().forEach((t) => t.stop());
            const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
            await processAudioData(audioBlob);
          };

          recorder.start();
          setIsListening(true);

          // Invariant: Max recording length 10 seconds auto-stop
          autoStopTimeoutRef.current = setTimeout(() => {
            console.log('useVoiceIn: max 10s recording limit reached, stopping.');
            stopListening();
          }, VOICE_CONFIG.maxRecordingSeconds * 1000);
        } else {
          // Simulation / React Native fallback for headless or mobile tests
          setIsListening(true);
          autoStopTimeoutRef.current = setTimeout(() => {
            setIsListening(false);
          }, 1000);
        }
      } catch (err: any) {
        console.warn('Microphone access denied or unavailable:', err);
        setError('Microphone access denied. Please type manually.');
        setIsListening(false);
        if (onError) onError(err);
      }
    },
    [cancel, stopListening]
  );

  return {
    isListening,
    isProcessing,
    error,
    startListening,
    stopListening,
    cancel,
  };
}
