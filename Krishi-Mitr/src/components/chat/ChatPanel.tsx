/**
 * ChatPanel — the whole conversation surface. Rendered inside the drawer and,
 * full-screen, as the Assistant page, so there is one chat implementation.
 */
import React, { useEffect, useRef } from 'react';
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import { colors, radius, space, type as typography } from '../../theme/tokens';
import { useT } from '../../lib/i18n';
import { useAgent } from '../../lib/agentContext';
import { Icon, IconName } from '../ui/Icon';
import { nm } from './ChatCards';
import { Composer } from './Composer';
import { MARGIN, MessageRow } from './MessageRow';
import { Seal } from './Seal';
import { ThinkingBeads } from './ThinkingBeads';

const slugToEnglish = (slug: string | null, kind: 'cmd' | 'mkt'): string | null => {
  if (!slug) return null;
  const w = slug.replace(/^(cmd|mkt|dist)_/, '');
  const cap = w.charAt(0).toUpperCase() + w.slice(1);
  return kind === 'mkt' ? `${cap} APMC` : cap;
};

const LANG_NAME = { mr: 'मराठी', hi: 'हिन्दी', en: 'English' } as const;

export function ChatPanel({
  onClose,
  bare = false,
  closeIcon = 'chevron-down',
}: {
  onClose?: () => void;
  bare?: boolean;
  closeIcon?: IconName;
}) {
  const { t, locale } = useT();
  const { messages, isThinking, screen, starters, send, reset } = useAgent();
  const scroller = useRef<ScrollView>(null);

  useEffect(() => {
    const id = setTimeout(() => scroller.current?.scrollToEnd({ animated: true }), 60);
    return () => clearTimeout(id);
  }, [messages.length, isThinking]);

  const crop = slugToEnglish(screen.active_commodity_id, 'cmd');
  const mandi = slugToEnglish(screen.active_market_id, 'mkt');
  const context = [crop && nm(crop, locale), mandi && nm(mandi, locale)].filter(Boolean).join(' · ');

  const last = messages[messages.length - 1];
  const chips = !isThinking && last?.role === 'assistant' ? last.response.quick_replies : [];
  const empty = messages.length === 0;

  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <Seal size={40} label={t('chat_fab_seal')} />
        <View style={styles.headText}>
          <View style={styles.titleRow}>
            <Text style={styles.title} numberOfLines={1}>
              {t('agent_title')}
            </Text>
            <View style={styles.langChip}>
              <Text style={styles.langChipText}>{LANG_NAME[locale]}</Text>
            </View>
          </View>
          {context ? (
            <View style={styles.context}>
              <Text style={styles.contextText} numberOfLines={1}>
                {t('chat_reading')}: {context}
              </Text>
            </View>
          ) : null}
        </View>
        {!empty ? (
          <TouchableOpacity style={styles.iconBtn} onPress={reset} accessibilityRole="button" accessibilityLabel={t('chat_new')}>
            <Icon name="edit" size={20} color={colors.onSurfaceVariant} />
          </TouchableOpacity>
        ) : null}
        {onClose ? (
          <TouchableOpacity style={styles.iconBtn} onPress={onClose} accessibilityRole="button" accessibilityLabel={t('chat_close')}>
            <Icon name={closeIcon} size={24} color={colors.onSurfaceVariant} />
          </TouchableOpacity>
        ) : null}
      </View>

      <View style={styles.page}>
        <ScrollView
          ref={scroller}
          style={styles.scroll}
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}>
          {empty ? (
            <View style={styles.hero}>
              <Text style={styles.heroTitle}>{t('chat_greeting')}</Text>
              <Text style={styles.heroSub}>{t('chat_greeting_sub')}</Text>
              <Text style={styles.tryLabel}>{t('chat_try_asking')}</Text>
              {starters.map(s => (
                <TouchableOpacity key={s} style={styles.slip} onPress={() => send(s)} activeOpacity={0.8} accessibilityRole="button">
                  <View style={[styles.notch, { left: -7 }]} />
                  <View style={[styles.notch, { right: -7 }]} />
                  <Text style={styles.slipText}>{s}</Text>
                  <Icon name="arrow-right" size={18} color={colors.primary} />
                </TouchableOpacity>
              ))}
            </View>
          ) : (
            messages.map(m => <MessageRow key={m.id} msg={m} />)
          )}

          {isThinking ? (
            <View style={styles.thinkingRow}>
              <View style={{ width: MARGIN - 12 }} />
              <View style={{ paddingLeft: 12 }}>
                <ThinkingBeads />
              </View>
            </View>
          ) : null}
        </ScrollView>
      </View>

      <View style={[styles.footer, bare && styles.footerBare]}>
        {chips.length > 0 ? (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips} keyboardShouldPersistTaps="handled">
            {chips.map(c => (
              <TouchableOpacity key={c} style={styles.chip} onPress={() => send(c)} accessibilityRole="button">
                <Text style={styles.chipText}>{c}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        ) : null}
        <Composer onSend={send} busy={isThinking} />
        <Text style={styles.note}>{t('chat_footer_note')}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.sm,
    paddingHorizontal: space.md,
    paddingBottom: space.sm,
    paddingTop: space.xs,
    borderBottomWidth: 1.5,
    borderBottomColor: colors.borderCard,
    backgroundColor: colors.surface,
  },
  headText: { flex: 1 },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: space.xs },
  title: { ...typography.titleLg, color: colors.onSurface, flexShrink: 1 },
  langChip: { backgroundColor: colors.surfaceContainer, borderRadius: radius.full, paddingHorizontal: 8, paddingVertical: 1 },
  langChipText: { ...typography.labelSm, fontSize: 12, color: colors.onSurfaceVariant },
  context: {
    alignSelf: 'flex-start',
    marginTop: 3,
    borderWidth: 1,
    borderStyle: 'dashed',
    borderColor: colors.borderField,
    borderRadius: radius.full,
    paddingHorizontal: 8,
    paddingVertical: 1,
    maxWidth: '100%',
  },
  contextText: { ...typography.bodySm, fontSize: 12, lineHeight: 16, color: colors.onSurfaceVariant },
  iconBtn: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },

  page: { flex: 1 },
  scroll: { flex: 1 },
  scrollContent: { padding: space.md, paddingBottom: space.lg, flexGrow: 1 },

  hero: { paddingTop: space.xl, paddingLeft: MARGIN - 12 },
  heroTitle: { ...typography.displayLg, fontSize: 38, lineHeight: 46, color: colors.onSurface },
  heroSub: { ...typography.bodyLg, color: colors.onSurfaceVariant, marginTop: space.xs, maxWidth: 420 },
  tryLabel: { ...typography.labelMd, color: colors.primary, marginTop: space.xl, marginBottom: space.sm },
  slip: {
    minHeight: 56,
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.sm,
    backgroundColor: colors.surface,
    borderWidth: 1.5,
    borderStyle: 'dashed',
    borderColor: colors.borderField,
    borderRadius: radius.md,
    paddingHorizontal: space.md,
    paddingVertical: 10,
    marginBottom: space.sm,
  },
  slipText: { ...typography.titleMd, color: colors.onSurface, flex: 1 },
  // Tear-off perforation: circles the colour of the page, biting into each edge.
  notch: { position: 'absolute', top: '50%', marginTop: -7, width: 14, height: 14, borderRadius: 7, backgroundColor: colors.background, borderWidth: 1.5, borderColor: colors.borderField },

  thinkingRow: { flexDirection: 'row', marginBottom: space.md },

  footer: {
    paddingHorizontal: space.md,
    paddingTop: space.sm,
    paddingBottom: space.sm,
    backgroundColor: colors.surface,
    borderTopWidth: 1.5,
    borderTopColor: colors.borderCard,
  },
  footerBare: { paddingBottom: space.md },
  chips: { gap: space.xs, paddingBottom: space.sm },
  chip: {
    minHeight: 40,
    justifyContent: 'center',
    paddingHorizontal: 14,
    borderRadius: radius.full,
    borderWidth: 1.5,
    borderColor: colors.primaryContainer,
    backgroundColor: colors.surfaceBright,
  },
  chipText: { ...typography.labelMd, color: colors.primary },
  note: { ...typography.bodySm, fontSize: 12, lineHeight: 16, color: colors.outline, textAlign: 'center', marginTop: space.xs },
});
