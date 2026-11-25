/**
 * Composer — one row that is either a text field or a live recording strip.
 * Tap-to-record, tap-to-stop (not press-and-hold): a farmer holding a phone
 * one-handed in a mandi is exactly who a hold gesture fails. Mic audio goes
 * through `transcribeAudio` (→ FastAPI → Sarvam); no key lives here.
 * If recording fails the text box is still right there — it is never hidden.
 */
import React, { useEffect, useRef, useState } from 'react';
import { PermissionsAndroid, Permission, Platform, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import AudioRecorderPlayer, {
  AudioEncoderAndroidType,
  AudioSourceAndroidType,
  OutputFormatAndroidType,
} from 'react-native-audio-recorder-player';

import { transcribeAudio } from '../../lib/api';
import { useT } from '../../lib/i18n';
import { colors, radius, space, type as typography } from '../../theme/tokens';
import { Icon } from '../ui/Icon';
import { Waveform } from './Waveform';

type Mic = 'idle' | 'recording' | 'transcribing';

const AUDIO_SET = {
  AudioEncoderAndroid: AudioEncoderAndroidType.AAC,
  AudioSourceAndroid: AudioSourceAndroidType.MIC,
  OutputFormatAndroid: OutputFormatAndroidType.MPEG_4,
};

async function micPermission(): Promise<boolean> {
  if (Platform.OS !== 'android') return true;
  const r = await PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.RECORD_AUDIO as Permission);
  return r === PermissionsAndroid.RESULTS.GRANTED;
}

export function Composer({
  onSend,
  onSendVoice,
  busy,
}: {
  onSend: (text: string) => void;
  onSendVoice?: (audioUri: string, transcribeFallback: () => Promise<string>) => Promise<void>;
  busy: boolean;
}) {
  const { t, locale } = useT();
  const [text, setText] = useState('');
  const [mic, setMic] = useState<Mic>('idle');
  const [micError, setMicError] = useState(false);
  const recorder = useRef(new AudioRecorderPlayer()).current;

  useEffect(
    () => () => {
      recorder.stopRecorder().catch(() => {});
      recorder.removeRecordBackListener();
    },
    [recorder],
  );

  const start = async () => {
    setMicError(false);
    if (!(await micPermission())) return setMicError(true);
    try {
      await recorder.startRecorder(undefined, AUDIO_SET);
      recorder.addRecordBackListener(() => undefined);
      setMic('recording');
    } catch {
      setMicError(true);
    }
  };

  const stop = async () => {
    setMic('transcribing');
    try {
      const uri = await recorder.stopRecorder();
      recorder.removeRecordBackListener();
      if (onSendVoice) {
        await onSendVoice(uri, async () => (await transcribeAudio(uri, locale)).transcript);
      } else {
        const { transcript } = await transcribeAudio(uri, locale);
        if (transcript.trim()) onSend(transcript);
      }
    } catch {
      setMicError(true);
    } finally {
      setMic('idle');
    }
  };

  const submit = () => {
    const v = text.trim();
    if (!v || busy) return;
    setText('');
    onSend(v);
  };

  if (mic !== 'idle') {
    const rec = mic === 'recording';
    return (
      <View style={styles.row}>
        <View style={styles.strip}>
          <Waveform active={rec} />
          <Text style={styles.stripLabel}>{rec ? t('chat_listening') : t('chat_transcribing')}</Text>
        </View>
        {rec ? (
          <TouchableOpacity style={[styles.round, styles.roundLive]} onPress={stop} accessibilityRole="button" accessibilityLabel={t('chat_mic_stop')}>
            <View style={styles.stopSquare} />
          </TouchableOpacity>
        ) : null}
      </View>
    );
  }

  const canSend = text.trim().length > 0 && !busy;
  return (
    <View>
      {micError ? <Text style={styles.err}>{t('chat_mic_error')}</Text> : null}
      <View style={styles.row}>
        <TextInput
          value={text}
          onChangeText={setText}
          onSubmitEditing={submit}
          placeholder={t('chat_placeholder')}
          placeholderTextColor={colors.outline}
          style={styles.input}
          multiline
          blurOnSubmit
          returnKeyType="send"
          accessibilityLabel={t('chat_placeholder')}
        />
        {canSend ? (
          <TouchableOpacity style={styles.round} onPress={submit} accessibilityRole="button" accessibilityLabel={t('chat_send')}>
            <Icon name="arrow-right" size={22} color={colors.onPrimary} />
          </TouchableOpacity>
        ) : (
          <TouchableOpacity
            style={[styles.round, busy && styles.roundOff]}
            onPress={start}
            disabled={busy}
            accessibilityRole="button"
            accessibilityLabel={t('chat_mic_start')}>
            <Icon name="mic" size={22} color={colors.onPrimary} />
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'flex-end', gap: space.sm },
  input: {
    flex: 1,
    minHeight: 52,
    maxHeight: 112,
    borderRadius: radius.xl,
    borderWidth: 1.5,
    borderColor: colors.borderInput,
    backgroundColor: colors.surface,
    paddingHorizontal: space.md,
    paddingTop: 14,
    paddingBottom: 12,
    color: colors.onSurface,
    ...typography.bodyLg,
  },
  round: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: colors.primaryContainer,
    alignItems: 'center',
    justifyContent: 'center',
  },
  roundOff: { opacity: 0.4 },
  roundLive: { backgroundColor: colors.primary },
  stopSquare: { width: 16, height: 16, borderRadius: 3, backgroundColor: colors.onPrimary },
  strip: {
    flex: 1,
    minHeight: 52,
    borderRadius: radius.xl,
    borderWidth: 1.5,
    borderColor: colors.borderActive,
    backgroundColor: colors.surfaceBright,
    paddingHorizontal: space.md,
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.md,
  },
  stripLabel: { ...typography.labelMd, color: colors.primary },
  err: { ...typography.bodySm, color: colors.critical, marginBottom: space.xs },
});
