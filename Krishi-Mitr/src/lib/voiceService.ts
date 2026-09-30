/**
 * voiceService.ts — Tactile Indian Rural Voice Engine for Krishi Mitra.
 *
 * Designed specifically for farmers in Maharashtra:
 * 1. Speaks fluent Marathi (mr-IN), Hindi (hi-IN), and Indian English (en-IN).
 * 2. Prepared for Sarvam AI Neural TTS (keys attached in .env / localStorage / window).
 * 3. Gracefully uses HTML5 SpeechSynthesis when running locally before key is pasted.
 * 4. Provides playback state, sound wave animation signals, and live read-along text.
 */

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

  public getApiKey(): string | null {
    if (typeof window !== "undefined") {
      const win = window as any;
      if (win.SARVAM_API_KEY) return win.SARVAM_API_KEY;
      try {
        const stored = localStorage.getItem("SARVAM_API_KEY");
        if (stored) return stored;
      } catch (e) {}
    }
    if (typeof process !== "undefined" && process.env) {
      return (
        process.env.REACT_APP_SARVAM_API_KEY ||
        process.env.EXPO_PUBLIC_SARVAM_API_KEY ||
        process.env.SARVAM_API_KEY ||
        null
      );
    }
    return null;
  }

  public async speak(opts: VoicePlayOptions): Promise<void> {
    this.stop();
    this.isSpeaking = true;
    opts.onStart?.();

    const apiKey = this.getApiKey();

    // 1. If Sarvam AI API Key is provided, call Sarvam Neural TTS
    if (apiKey) {
      try {
        const langCode = opts.lang === "hi-IN" ? "hi-IN" : opts.lang === "en-IN" ? "en-IN" : "mr-IN";
        const res = await fetch("https://api.sarvam.ai/text-to-speech", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "api-subscription-key": apiKey,
          },
          body: JSON.stringify({
            inputs: [opts.text],
            target_language_code: langCode,
            speaker: "bulbul:v1",
            pace: 1.0,
            speech_sample_rate: 22050,
            enable_preprocessing: true,
            model: "bulbul:v1",
          }),
        });

        if (res.ok) {
          const data = await res.json();
          const base64Audio = data.audios?.[0];
          if (base64Audio) {
            const audioSrc = `data:audio/wav;base64,${base64Audio}`;
            const audio = new Audio(audioSrc);
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
        }
      } catch (e) {
        console.warn("Sarvam API failed, falling back to browser TTS", e);
      }
    }

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
