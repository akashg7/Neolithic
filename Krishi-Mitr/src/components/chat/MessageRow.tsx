/**
 * One turn. Assistant replies sit on the ledger itself — no bubble, a seal in
 * the margin, the words written straight onto the page. The farmer's own turn
 * is a marigold chit with a squared corner, like a slip handed across a counter.
 */
import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import { colors, radius, space, type as typography } from '../../theme/tokens';
import { useT } from '../../lib/i18n';
import { useAgent } from '../../lib/agentContext';
import type { ChatMessage } from '../../lib/agentTypes';
import { Icon } from '../ui/Icon';
import { ListenButton } from '../ui/ListenButton';
import { CardView, CitationList } from './ChatCards';
import { Seal } from './Seal';

export const MARGIN = 44;

export function MessageRow({ msg }: { msg: ChatMessage }) {
  const { t } = useT();
  const { runUiAction, retry } = useAgent();

  if (msg.role === 'user') {
    return (
      <View style={styles.userRow}>
        <View style={styles.chit}>
          <Text style={styles.chitText}>{msg.text}</Text>
        </View>
      </View>
    );
  }

  if (msg.role === 'error') {
    return (
      <View style={styles.aiRow}>
        <View style={styles.gutter} />
        <View style={styles.aiBody}>
          <Text style={styles.errText}>{t('chat_error')}</Text>
          <TouchableOpacity style={styles.retry} onPress={() => retry(msg.id)} accessibilityRole="button">
            <Icon name="refresh" size={16} color={colors.primary} />
            <Text style={styles.retryText}>{t('chat_retry')}</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  const r = msg.response;
  return (
    <View style={styles.aiRow}>
      <View style={styles.gutter}>
        <Seal size={30} label={t('chat_fab_seal')} ring={false} />
      </View>
      <View style={styles.aiBody}>
        <View style={styles.aiBubble}>
          <Text style={styles.aiText}>{r.reply_text}</Text>
        </View>

        {r.cards.map((c, i) => (
          <CardView key={i} card={c} onConfirmLot={() => runUiAction({ target_screen: 'S15_MyLots' })} />
        ))}

        <View style={styles.actions}>
          <ListenButton text={r.reply_text} />
          {r.ui_action ? (
            <TouchableOpacity
              style={styles.cta}
              onPress={() => runUiAction(r.ui_action!)}
              accessibilityRole="button"
              accessibilityLabel={r.ui_action.cta_label}>
              <Text style={styles.ctaText}>{r.ui_action.cta_label}</Text>
              <Icon name="arrow-right" size={16} color={colors.primary} />
            </TouchableOpacity>
          ) : null}
        </View>

        <CitationList items={r.citations} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  userRow: { alignItems: 'flex-end', paddingLeft: 56, marginBottom: space.lg },
  chit: {
    backgroundColor: colors.primaryContainer,
    borderRadius: radius.lg,
    borderTopRightRadius: 4,
    paddingHorizontal: space.md,
    paddingVertical: 12,
  },
  chitText: { ...typography.bodyLg, color: colors.onPrimary },

  aiRow: { flexDirection: 'row', marginBottom: space.xl },
  gutter: { width: MARGIN - 12, alignItems: 'flex-start', paddingTop: 2 },
  aiBody: { flex: 1, paddingLeft: 12 },
  aiBubble: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderCard,
    borderRadius: radius.lg,
    borderTopLeftRadius: 4,
    paddingHorizontal: space.md,
    paddingVertical: 12,
    alignSelf: 'flex-start',
    maxWidth: '100%',
  },
  aiText: { ...typography.bodyLg, color: colors.onSurface },

  actions: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', gap: space.sm, marginTop: space.sm },
  cta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    minHeight: 40,
    paddingHorizontal: 14,
    borderRadius: radius.full,
    borderWidth: 1.5,
    borderColor: colors.primaryContainer,
  },
  ctaText: { ...typography.labelMd, color: colors.primary },

  errText: { ...typography.bodyMd, color: colors.onSurfaceVariant },
  retry: { flexDirection: 'row', alignItems: 'center', gap: 6, minHeight: 44, alignSelf: 'flex-start' },
  retryText: { ...typography.labelMd, color: colors.primary },
});
