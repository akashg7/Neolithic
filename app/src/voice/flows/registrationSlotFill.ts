/**
 * Mandi-Setu Voice Module — Registration Slot-Fill State Machine (Track B: B9)
 * Linear, one-field-at-a-time guided flow for farmer onboarding.
 * Product Rule: Re-asks ONCE if confidence is low, then falls back to manual typing.
 * Commitment Invariant: Only submits when farmer taps "हो, बरोबर आहे" on the summary screen.
 */

import { VOICE_CONFIG } from '../config';
import type { RegistrationField } from '../types';

export interface RegistrationStep {
  field: RegistrationField;
  prompt_mr: string;
  label_mr: string;
}

export const REGISTRATION_FLOW: readonly RegistrationStep[] = [
  { field: 'name', prompt_mr: 'तुमचे नाव काय आहे?', label_mr: 'शेतकऱ्याचे नाव' },
  { field: 'district', prompt_mr: 'तुम्ही कोणत्या जिल्ह्यात राहता?', label_mr: 'जिल्हा' },
  { field: 'village', prompt_mr: 'तुमच्या गावाचे नाव काय आहे?', label_mr: 'गाव' },
  { field: 'primary_commodity', prompt_mr: 'तुम्ही मुख्यतः कोणते पीक घेता?', label_mr: 'मुख्य पीक' },
];

export type SlotFillState =
  | 'IDLE'
  | 'PROMPTING'
  | 'LISTENING'
  | 'RE_ASKING'
  | 'MANUAL_INPUT'
  | 'SUMMARY'
  | 'CONFIRMED';

export interface RegistrationSlotData {
  value: string;
  confidence: number;
  label_mr: string;
  isManual: boolean;
}

export class RegistrationSlotFillMachine {
  private currentIndex = 0;
  private retriedCurrentField = false;
  private state: SlotFillState = 'IDLE';
  private data: Record<RegistrationField, RegistrationSlotData> = {
    name: { value: '', confidence: 0, label_mr: 'शेतकऱ्याचे नाव', isManual: false },
    district: { value: '', confidence: 0, label_mr: 'जिल्हा', isManual: false },
    village: { value: '', confidence: 0, label_mr: 'गाव', isManual: false },
    primary_commodity: { value: '', confidence: 0, label_mr: 'मुख्य पीक', isManual: false },
  };

  private onStateChange?: (state: SlotFillState, currentStep?: RegistrationStep) => void;
  private speakFn?: (prompt: string) => Promise<void>;

  constructor(options?: {
    speakFn?: (prompt: string) => Promise<void>;
    onStateChange?: (state: SlotFillState, currentStep?: RegistrationStep) => void;
  }) {
    this.speakFn = options?.speakFn;
    this.onStateChange = options?.onStateChange;
  }

  public getState(): SlotFillState {
    return this.state;
  }

  public getCurrentStep(): RegistrationStep | null {
    if (this.currentIndex < REGISTRATION_FLOW.length) {
      return REGISTRATION_FLOW[this.currentIndex];
    }
    return null;
  }

  public getSummaryData(): Record<RegistrationField, RegistrationSlotData> {
    return { ...this.data };
  }

  /**
   * Starts the registration flow at step 0
   */
  public async start(): Promise<void> {
    this.currentIndex = 0;
    this.retriedCurrentField = false;
    await this.promptCurrentStep();
  }

  private async promptCurrentStep(): Promise<void> {
    const step = this.getCurrentStep();
    if (!step) {
      this.transitionTo('SUMMARY');
      return;
    }

    this.transitionTo('PROMPTING');
    if (this.speakFn) {
      try {
        await this.speakFn(step.prompt_mr);
      } catch (err) {
        console.warn('Speech prompt failed, proceeding directly to listening:', err);
      }
    }
    this.transitionTo('LISTENING');
  }

  /**
   * Ingests ASR result for current field and applies validation / retry logic
   */
  public async handleSpeechInput(rawTranscript: string, confidence: number): Promise<void> {
    const step = this.getCurrentStep();
    if (!step) return;

    const trimmed = rawTranscript.trim();
    const threshold = VOICE_CONFIG.confidenceThreshold;

    // Confidence check
    if (confidence < threshold || trimmed.length === 0) {
      if (!this.retriedCurrentField) {
        // Re-ask ONCE
        this.retriedCurrentField = true;
        this.transitionTo('RE_ASKING');
        const reAskPrompt = `समजले नाही. कृपया ${step.label_mr} पुन्हा सांगा.`;
        if (this.speakFn) {
          try {
            await this.speakFn(reAskPrompt);
          } catch {
            // ignore
          }
        }
        this.transitionTo('LISTENING');
        return;
      } else {
        // Failed retry: fall back to manual text input for this field
        this.transitionTo('MANUAL_INPUT');
        return;
      }
    }

    // Success: save value and advance
    this.data[step.field] = {
      value: trimmed,
      confidence,
      label_mr: step.label_mr,
      isManual: false,
    };

    this.advanceStep();
  }

  /**
   * Allows manual typing for a field (either after retry failure or human edit)
   */
  public setManualFieldValue(field: RegistrationField, value: string): void {
    this.data[field] = {
      value: value.trim(),
      confidence: 1.0,
      label_mr: this.data[field]?.label_mr || field,
      isManual: true,
    };

    if (this.state === 'MANUAL_INPUT') {
      this.advanceStep();
    }
  }

  private advanceStep(): void {
    this.currentIndex++;
    this.retriedCurrentField = false;

    if (this.currentIndex >= REGISTRATION_FLOW.length) {
      this.transitionTo('SUMMARY');
      if (this.speakFn) {
        this.speakFn('दिलेली माहिती बरोबर आहे का?');
      }
    } else {
      this.promptCurrentStep();
    }
  }

  /**
   * Final commit point — user taps "हो, बरोबर आहे"
   */
  public confirm(): Record<RegistrationField, string> {
    this.transitionTo('CONFIRMED');
    return {
      name: this.data.name.value,
      district: this.data.district.value,
      village: this.data.village.value,
      primary_commodity: this.data.primary_commodity.value,
    };
  }

  private transitionTo(newState: SlotFillState): void {
    this.state = newState;
    if (this.onStateChange) {
      this.onStateChange(newState, this.getCurrentStep() ?? undefined);
    }
  }
}
