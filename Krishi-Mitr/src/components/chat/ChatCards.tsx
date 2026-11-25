/**
 * Cards the agent can attach to a reply. Each renders ONLY the structured
 * `data` from the response — never numbers parsed out of the sentence — so a
 * figure on screen is always one the deterministic engines produced.
 *
 * Design: every card is a slip from a trader's pad. The verdict is a stamped
 * word, not a coloured chip; gain and worst case are the same size on purpose
 * (project invariant: the downside is never smaller than the upside).
 *
 * Colour rules inherited from the app: red is reserved for the worst case,
 * emerald for a gain, and a refusal is neutral ink — never red, because
 * "I don't know" is not a warning.
 */
import React, { useState } from 'react';
import { LayoutChangeEvent, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import Svg, { Circle, Line, Path, Rect } from 'react-native-svg';

import { colors, fontFamily, radius, space, type as typography, weights } from '../../theme/tokens';
import { Icon } from '../ui/Icon';
import { useT } from '../../lib/i18n';
import { formatPaise, formatNumber } from '../../lib/money';
import type { Locale } from '../../types/api';
import type {
  AgentCard,
  Citation,
  LotDraftCardData,
  PriceSnapshotCardData,
  WindowVerdictCardData,
} from '../../lib/agentTypes';

const NAMES: Record<string, { mr: string; hi: string }> = {
  Onion: { mr: 'कांदा', hi: 'प्याज' },
  Tomato: { mr: 'टोमॅटो', hi: 'टमाटर' },
  Soyabean: { mr: 'सोयाबीन', hi: 'सोयाबीन' },
  'Lasalgaon APMC': { mr: 'लासलगाव', hi: 'लासलगांव' },
  'Pimpalgaon APMC': { mr: 'पिंपळगाव', hi: 'पिंपळगांव' },
  'Pune APMC': { mr: 'पुणे', hi: 'पुणे' },
  'Nashik APMC': { mr: 'नाशिक', hi: 'नाशिक' },
};
export function nm(en: string, l: Locale): string {
  if (l === 'en') return en.replace(' APMC', '');
  return NAMES[en]?.[l] ?? en.replace(' APMC', '');
}

/* ─────────────────────────── Window verdict ─────────────────────────── */

function Stamp({ word, sub, tone }: { word: string; sub?: string; tone: string }) {
  return (
    <View style={[styles.stampOuter, { borderColor: tone }]}>
      <View style={[styles.stampInner, { borderColor: tone }]}>
        <Text style={[styles.stampWord, { color: tone }]} numberOfLines={1}>
          {word}
        </Text>
        {sub ? <Text style={[styles.stampSub, { color: tone }]}>{sub}</Text> : null}
      </View>
    </View>
  );
}

function RangeBar({ worst, gain }: { worst: number; gain: number }) {
  const [w, setW] = useState(0);
  const lo = Math.min(worst, 0);
  const hi = Math.max(gain, 0);
  const span = hi - lo || 1;
  const x = (v: number) => 8 + ((v - lo) / span) * Math.max(0, w - 16);
  return (
    <View onLayout={(e: LayoutChangeEvent) => setW(e.nativeEvent.layout.width)} style={styles.rangeWrap}>
      {w > 0 ? (
        <Svg width={w} height={28}>
          <Line x1={8} x2={w - 8} y1={14} y2={14} stroke={colors.borderField} strokeWidth={2} strokeLinecap="round" />
          <Rect x={x(worst)} y={11} width={Math.max(2, x(gain) - x(worst))} height={6} rx={3} fill={colors.tertiaryContainer} opacity={0.35} />
          <Line x1={x(0)} x2={x(0)} y1={4} y2={24} stroke={colors.onSurfaceVariant} strokeWidth={1.5} strokeDasharray="2 2" />
          <Circle cx={x(worst)} cy={14} r={6} fill={colors.critical} />
          <Circle cx={x(gain)} cy={14} r={6} fill={colors.positive} />
        </Svg>
      ) : null}
    </View>
  );
}

function WindowVerdictCard({ d }: { d: WindowVerdictCardData }) {
  const { t, locale } = useT();
  const none = d.action === 'NO_ADVICE';
  const tone = none ? colors.onSurfaceVariant : d.action === 'HOLD' || d.action === 'SPLIT' ? colors.primary : colors.positive;
  const word = none ? t('chat_verdict_none') : d.action === 'SPLIT' ? t('chat_verdict_split') : d.action === 'HOLD' ? t('chat_verdict_hold') : t('chat_verdict_sell');
  const sub = (d.action === 'HOLD' || d.action === 'SPLIT') && d.hold_days ? t('chat_hold_days', { days: formatNumber(d.hold_days, locale) }) : undefined;
  const qty = `${formatNumber(d.quantity_kg, locale)} ${t('chat_kg')}`;

  return (
    <View style={styles.card}>
      <View style={styles.verdictTop}>
        <Stamp word={word} sub={sub} tone={tone} />
        <View style={styles.verdictMeta}>
          <Text style={styles.metaCrop}>{nm(d.commodity, locale)}</Text>
          <Text style={styles.metaLine}>
            {nm(d.mandi, locale)} · {qty}
          </Text>
        </View>
      </View>

      {none ? (
        <View style={styles.gauge}>
          <View style={styles.gaugeTrack}>
            <View style={[styles.gaugeFill, { width: `${Math.min(100, ((d.uncertainty_pct ?? 0) / 50) * 100)}%` }]} />
            <View style={[styles.gaugeLimit, { left: `${(35 / 50) * 100}%` }]} />
          </View>
          <Text style={styles.gaugeText}>{t('chat_uncertainty', { pct: formatNumber(d.uncertainty_pct ?? 0, locale) })}</Text>
        </View>
      ) : (
        <>
          <View style={styles.figures}>
            <View style={styles.figure}>
              <View style={styles.figureLabelRow}>
                <View style={[styles.dot, { backgroundColor: colors.positive }]} />
                <Text style={styles.figureLabel}>{t('chat_gain')}</Text>
              </View>
              <Text style={[styles.figureValue, { color: colors.positive }]}>{formatPaise(d.expected_gain_paise ?? 0, locale)}</Text>
            </View>
            <View style={styles.figureRule} />
            <View style={styles.figure}>
              <View style={styles.figureLabelRow}>
                <View style={[styles.dot, { backgroundColor: colors.critical }]} />
                <Text style={styles.figureLabel}>{t('chat_worst')}</Text>
              </View>
              <Text style={[styles.figureValue, { color: colors.critical }]}>{formatPaise(d.worst_case_paise ?? 0, locale)}</Text>
            </View>
          </View>
          <RangeBar worst={d.worst_case_paise ?? 0} gain={d.expected_gain_paise ?? 0} />
          <Text style={styles.footnote}>{t('chat_after_costs')}</Text>
        </>
      )}
    </View>
  );
}

/* ─────────────────────────── Price snapshot ─────────────────────────── */

function Sparkline({ series }: { series: number[] }) {
  if (series.length < 2) return null;
  const W = 112;
  const H = 46;
  const min = Math.min(...series);
  const max = Math.max(...series);
  const span = max - min || 1;
  const pts = series.map((v, i) => [4 + (i / (series.length - 1)) * (W - 8), H - 6 - ((v - min) / span) * (H - 12)] as const);
  const d = pts.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join(' ');
  const last = pts[pts.length - 1]!;
  return (
    <Svg width={W} height={H}>
      <Path d={d} stroke={colors.primaryContainer} strokeWidth={2.25} fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <Circle cx={last[0]} cy={last[1]} r={4} fill={colors.primaryContainer} />
      <Circle cx={last[0]} cy={last[1]} r={7} fill={colors.primaryContainer} opacity={0.18} />
    </Svg>
  );
}

function PriceSnapshotCard({ d }: { d: PriceSnapshotCardData }) {
  const { t, locale } = useT();
  const series = d.series_paise_per_qtl ?? [];
  const first = series[0] ?? d.modal_price_paise_per_qtl;
  const delta = series.length >= 2 ? d.modal_price_paise_per_qtl - first : (d.change_bps ?? 0);
  const flat = series.length >= 2 ? Math.abs(delta) < first * 0.005 : Math.abs(delta) < 50;
  const up = delta > 0;
  return (
    <View style={styles.card}>
      <Text style={styles.metaCrop}>
        {nm(d.commodity, locale)} · {nm(d.mandi, locale)}
      </Text>
      <Text style={styles.figureLabel}>{t('chat_modal_price')}</Text>
      <View style={styles.priceRow}>
        <Text style={styles.priceHero}>{formatPaise(d.modal_price_paise_per_qtl, locale)}</Text>
        <Sparkline series={d.series_paise_per_qtl} />
      </View>
      <View style={styles.trendRow}>
        {flat ? null : <Icon name={up ? 'trending-up' : 'trending-down'} size={16} color={up ? colors.positive : colors.critical} />}
        <Text style={styles.trendText}>{flat ? t('chat_trend_flat') : up ? t('chat_trend_up') : t('chat_trend_down')}</Text>
        <View style={styles.sourceChip}>
          <Text style={styles.sourceChipText}>{d.source}</Text>
        </View>
      </View>
    </View>
  );
}

/* ───────────────────────────── Lot draft ────────────────────────────── */

function LotDraftCard({ d, onConfirm }: { d: LotDraftCardData; onConfirm: () => void }) {
  const { t, locale } = useT();
  const rows: [string, string][] = [
    [t('chat_lot_commodity'), nm(d.commodity, locale)],
    [t('chat_lot_qty'), `${formatNumber(d.quantity_kg, locale)} ${t('chat_kg')}`],
    ...(d.mandi ? [[t('chat_lot_mandi'), nm(d.mandi, locale)] as [string, string]] : []),
  ];
  return (
    <View style={[styles.card, styles.slip]}>
      <Text style={styles.slipTitle}>{t('chat_lot_draft')}</Text>
      {rows.map(([k, v]) => (
        <View key={k} style={styles.slipRow}>
          <Text style={styles.slipKey}>{k}</Text>
          <View style={styles.slipLeader} />
          <Text style={styles.slipVal}>{v}</Text>
        </View>
      ))}
      <TouchableOpacity style={styles.confirm} onPress={onConfirm} activeOpacity={0.85} accessibilityRole="button">
        <Text style={styles.confirmText}>{t('chat_lot_confirm')}</Text>
        <Icon name="arrow-right" size={18} color={colors.onPrimary} />
      </TouchableOpacity>
      <Text style={styles.footnote}>{t('chat_lot_note')}</Text>
    </View>
  );
}

/* ───────────────────────────── Citations ────────────────────────────── */

export function CitationList({ items }: { items: Citation[] }) {
  const { t } = useT();
  const [open, setOpen] = useState(false);
  if (!items.length) return null;
  return (
    <View style={styles.citeWrap}>
      <TouchableOpacity onPress={() => setOpen(o => !o)} style={styles.citeHead} accessibilityRole="button" accessibilityState={{ expanded: open }}>
        <Icon name="shield-check" size={15} color={colors.tertiary} />
        <Text style={styles.citeHeadText}>
          {t('chat_sources')} ({items.length})
        </Text>
        <Icon name={open ? 'chevron-down' : 'chevron-right'} size={14} color={colors.outline} />
      </TouchableOpacity>
      {open
        ? items.map((c, idx) => (
            <View key={`${c.source}-${idx}`} style={styles.citeItem}>
              <Text style={styles.citeTitle}>{c.title}</Text>
              <Text style={styles.citeSrc}>{c.source}</Text>
            </View>
          ))
        : null}
    </View>
  );
}

/* ───────────────────────────── Dispatcher ───────────────────────────── */

export function CardView({ card, onConfirmLot }: { card: AgentCard; onConfirmLot: () => void }) {
  switch (card.type) {
    case 'WINDOW_VERDICT':
      return <WindowVerdictCard d={card.data} />;
    case 'PRICE_SNAPSHOT':
      return <PriceSnapshotCard d={card.data} />;
    case 'LOT_DRAFT':
      return <LotDraftCard d={card.data} onConfirm={onConfirmLot} />;
    default:
      return null;
  }
}

const styles = StyleSheet.create({
  card: {
    marginTop: space.sm,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.borderCard,
    padding: space.md,
  },
  verdictTop: { flexDirection: 'row', alignItems: 'center', gap: space.md },
  verdictMeta: { flex: 1 },
  metaCrop: { ...typography.titleLg, color: colors.onSurface },
  metaLine: { ...typography.bodySm, color: colors.onSurfaceVariant, marginTop: 2 },

  stampOuter: { borderWidth: 2.5, borderRadius: 10, padding: 3, transform: [{ rotate: '-4deg' }] },
  stampInner: { borderWidth: 1, borderRadius: 6, paddingHorizontal: 12, paddingVertical: 6, alignItems: 'center', minWidth: 96 },
  stampWord: { fontFamily: fontFamily.extraBold, fontWeight: weights.extraBold, fontSize: 22, lineHeight: 28, letterSpacing: 0.5 },
  stampSub: { ...typography.labelSm, marginTop: 1 },

  figures: { flexDirection: 'row', alignItems: 'stretch', marginTop: space.md },
  figure: { flex: 1 },
  figureRule: { width: 1, backgroundColor: colors.borderCard, marginHorizontal: space.md },
  figureLabelRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  figureLabel: { ...typography.bodySm, color: colors.onSurfaceVariant },
  // Same size for both on purpose — the downside is never typeset smaller than the upside.
  figureValue: { ...typography.numeralData, fontSize: 26, lineHeight: 32, marginTop: 2 },
  rangeWrap: { marginTop: space.sm, height: 28 },
  footnote: { ...typography.bodySm, color: colors.onSurfaceVariant, marginTop: space.xs },

  gauge: { marginTop: space.md },
  gaugeTrack: { height: 10, borderRadius: 5, backgroundColor: colors.surfaceContainerHigh, overflow: 'visible', justifyContent: 'center' },
  gaugeFill: { height: 10, borderRadius: 5, backgroundColor: colors.onSurfaceVariant },
  gaugeLimit: { position: 'absolute', top: -4, width: 2, height: 18, backgroundColor: colors.primary },
  gaugeText: { ...typography.bodySm, color: colors.onSurfaceVariant, marginTop: space.xs },

  priceRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 2 },
  priceHero: { ...typography.numeralHero, color: colors.onSurface },
  trendRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: space.xs },
  trendText: { ...typography.bodySm, color: colors.onSurfaceVariant, flex: 1 },
  sourceChip: { borderRadius: radius.full, borderWidth: 1, borderColor: colors.tertiaryContainer, paddingHorizontal: 8, paddingVertical: 2 },
  sourceChipText: { ...typography.labelSm, fontSize: 11, color: colors.tertiary },

  slip: { backgroundColor: colors.surfaceBright, borderStyle: 'dashed', borderColor: colors.borderField, borderWidth: 1.5 },
  slipTitle: { ...typography.labelMd, color: colors.primary, marginBottom: space.xs },
  slipRow: { flexDirection: 'row', alignItems: 'flex-end', paddingVertical: 6 },
  slipKey: { ...typography.bodySm, color: colors.onSurfaceVariant },
  slipLeader: { flex: 1, height: 1, marginHorizontal: 8, marginBottom: 5, borderBottomWidth: 1.5, borderStyle: 'dotted', borderColor: colors.borderField },
  slipVal: { ...typography.titleMd, color: colors.onSurface },
  confirm: {
    marginTop: space.md,
    minHeight: 48,
    borderRadius: radius.md,
    backgroundColor: colors.primaryContainer,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  confirmText: { ...typography.labelLg, color: colors.onPrimary },

  citeWrap: { marginTop: space.sm },
  citeHead: { flexDirection: 'row', alignItems: 'center', gap: 6, alignSelf: 'flex-start', minHeight: 32 },
  citeHeadText: { ...typography.labelMd, color: colors.tertiary },
  citeItem: { marginTop: 6, paddingLeft: 10, borderLeftWidth: 2, borderLeftColor: colors.tertiaryContainer },
  citeTitle: { ...typography.bodySm, color: colors.onSurface },
  citeSrc: { ...typography.bodySm, fontSize: 12, color: colors.outline },
});
