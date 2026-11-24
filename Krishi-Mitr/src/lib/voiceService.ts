/**
 * voiceService.ts — Tactile Indian Rural Voice Engine for Krishi Mitra.
 *
 * Designed specifically for farmers in Maharashtra:
 * 1. Speaks fluent Marathi (mr-IN), Hindi (hi-IN), and Indian English (en-IN).
 * 2. Speaks with Sarvam AI neural TTS via our server (`/voice/narrate`; the key stays server-side).
 * 3. Falls back to HTML5 SpeechSynthesis when the server can't narrate.
 * 4. Provides playback state, sound wave animation signals, and live read-along text.
 */

import { narrate } from "./api";
import type { Locale } from "../types/api";

export interface VoicePlayOptions {
  text: string;
  lang?: "mr-IN" | "hi-IN" | "en-IN";
  onStart?: () => void;
  onEnd?: () => void;
  onError?: (err: any) => void;
}

class VoiceService {
  private activeUtterance: SpeechSynthesisUtterance | null = null;
  private activeAudio: HTMLAudioElement | null = null;
  private isSpeaking: boolean = false;

  public async speak(opts: VoicePlayOptions): Promise<void> {
    this.stop();
    this.isSpeaking = true;
    opts.onStart?.();

    // 1. Sarvam neural voice, through our server (`POST /voice/narrate`). The
    //    Sarvam key lives only on the server — a key in the page bundle is a
    //    published key. `narrate()` returns '' when the server can't speak.
    try {
      const locale: Locale = opts.lang === "hi-IN" ? "hi" : opts.lang === "en-IN" ? "en" : "mr";
      const { audio_base64 } = await narrate(opts.text, locale);
      if (audio_base64 && this.isSpeaking) {
        const audio = new Audio(`data:audio/wav;base64,${audio_base64}`);
        this.activeAudio = audio;
        audio.onended = () => {
          this.isSpeaking = false;
          opts.onEnd?.();
        };
        audio.onerror = (e) => {
          this.isSpeaking = false;
          opts.onError?.(e);
        };
        await audio.play();
        return;
      }
    } catch (e) {
      console.warn("Sarvam narration failed, falling back to browser TTS", e);
    }
    if (!this.isSpeaking) return;

    // 2. Browser SpeechSynthesis Fallback
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(opts.text);
      this.activeUtterance = utter;
      utter.lang = opts.lang || "mr-IN";
      utter.rate = 0.95; // slightly deliberate pacing for clarity outdoors
      utter.pitch = 1.0;

      // Select matching voice if available
      const voices = window.speechSynthesis.getVoices();
      const matchedVoice = voices.find(
        (v) => v.lang.startsWith("mr") || v.lang.startsWith("hi") || v.lang.includes("IN")
      );
      if (matchedVoice) {
        utter.voice = matchedVoice;
      }

      utter.onend = () => {
        this.isSpeaking = false;
        opts.onEnd?.();
      };
      utter.onerror = (e) => {
        this.isSpeaking = false;
        opts.onError?.(e);
      };

      window.speechSynthesis.speak(utter);
    } else {
      // Simulate completion if no audio interface
      setTimeout(() => {
        this.isSpeaking = false;
        opts.onEnd?.();
      }, 3000);
    }
  }

  public stop(): void {
    this.isSpeaking = false;
    if (this.activeAudio) {
      this.activeAudio.pause();
      this.activeAudio = null;
    }
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      this.activeUtterance = null;
    }
  }

  public getIsSpeaking(): boolean {
    return this.isSpeaking;
  }
}

export const voiceService = new VoiceService();
