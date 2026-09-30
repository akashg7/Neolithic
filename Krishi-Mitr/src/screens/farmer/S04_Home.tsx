/**
 * S04_Home — Screen 08: Krishi-Mitr Farmer-First Intelligence Dashboard.
 *
 * ★ High contrast, bold, legible typography for outdoor sunlight readability.
 * ★ 1-tap quick crop ribbon: Onion, Soyabean, Cotton, Wheat, Gram, Maize, Tomato.
 * ★ 1-tap Mandi switcher across 8 major Maharashtra APMC markets.
 * ★ Prominent Voice Advisory hero banner with Web Speech & Sarvam audio playback.
 * ★ Invariant I16: Expected Gain and Worst Case Downside rendered with identical visual weight.
 */

import React, { useState } from 'react';
import {
  Image,
  Platform,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import Svg, { Rect, Line, Circle, Defs, LinearGradient, Path, Stop, Text as SvgText } from 'react-native-svg';
import { useQuery } from '@tanstack/react-query';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { CompositeNavigationProp } from '@react-navigation/native';
import type { BottomTabNavigationProp } from '@react-navigation/bottom-tabs';
import { colors, fontFamily, space, radius, cardShadow } from '../../theme/tokens';
import { Icon } from '../../components/ui/Icon';
import { WebFooter } from '../../components/web/WebFooter';
import { useT } from '../../lib/i18n';
import { useAuth } from '../../lib/auth';
import { useSelection } from '../../lib/selection';
import { getLots, getPriceSeries, recommendWindow } from '../../lib/api';
import { formatNumber, formatPaise, formatQuintal } from '../../lib/money';
import {
  DEFAULT_COMMODITY_ID,
  DEFAULT_GRADE,
  DEFAULT_HORIZON_DAYS,
  DEFAULT_MARKET_ID,
  DEFAULT_QTY_KG,
  USE_FIXTURES,
} from '../../config';
import { fxPriceSeries, fxSeriesFor } from '../../fixtures/prices';
import { fxHold, fxWindowFor } from '../../fixtures/window';
import { fxMyLots } from '../../fixtures/lots';
import type { HomeStackParamList, FarmerTabParamList } from '../../navigation/FarmerTabs';
import type { Locale, PricePoint } from '../../types/api';
import { ListenButton } from '../../components/ui/ListenButton';
import { buildHomeNarration } from '../../lib/pageNarration';
import { useScreenNarration } from '../../lib/useScreenNarration';
import { Logo } from '../../components/ui/Logo';

type Props = NativeStackScreenProps<HomeStackParamList, 'S4_Home'>;
type ParentNav = CompositeNavigationProp<
  Props['navigation'],
  BottomTabNavigationProp<FarmerTabParamList>
>;

// ── Crops Catalogue ──────────────────────────────────────────────────
interface CropOption {
  id: string;
  name_mr: string;
  name_hi: string;
  name_en: string;
  icon: string;
  tag: string;
}

const CROPS: CropOption[] = [
  { id: 'cmd_onion', name_mr: 'कांदा', name_hi: 'प्याज', name_en: 'Onion', icon: '🧅', tag: 'नाशिक / पुणे' },
  { id: 'cmd_soyabean', name_mr: 'सोयाबीन', name_hi: 'सोयाबीन', name_en: 'Soyabean', icon: '🫘', tag: 'लातूर / विदर्भ' },
  { id: 'cmd_cotton', name_mr: 'कापूस', name_hi: 'कपास', name_en: 'Cotton', icon: '⚪', tag: 'यवतमाळ / जळगाव' },
  { id: 'cmd_wheat', name_mr: 'गहू', name_hi: 'गेहूं', name_en: 'Wheat', icon: '🌾', tag: 'अ.नगर / पुणे' },
  { id: 'cmd_gram', name_mr: 'हरभरा (चना)', name_hi: 'चना', name_en: 'Gram/Chana', icon: '🟤', tag: 'लातूर / सोलापूर' },
  { id: 'cmd_maize', name_mr: 'मका', name_hi: 'मक्का', name_en: 'Maize', icon: '🌽', tag: 'बारामती / जळगाव' },
  { id: 'cmd_tomato', name_mr: 'टोमॅटो', name_hi: 'टमाटर', name_en: 'Tomato', icon: '🍅', tag: 'नाशिक / जुन्नर' },
];

// ── Top Maharashtra Mandis ───────────────────────────────────────────
interface MandiOption {
  id: string;
  name_mr: string;
  name_en: string;
  dist_mr: string;
  dist_en: string;
  dist_id: string;
}

const POPULAR_MANDIS: MandiOption[] = [
  { id: 'mkt_lasalgaon', name_mr: 'लासलगाव', name_en: 'Lasalgaon', dist_mr: 'नाशिक', dist_en: 'Nashik', dist_id: 'dist_nashik' },
  { id: 'mkt_latur', name_mr: 'लातूर मुख्य मंडी', name_en: 'Latur APMC', dist_mr: 'लातूर', dist_en: 'Latur', dist_id: 'dist_latur' },
  { id: 'mkt_ahmednagar', name_mr: 'अहमदनगर', name_en: 'Ahmednagar', dist_mr: 'अ.नगर', dist_en: 'Ahmednagar', dist_id: 'dist_ahmednagar' },
  { id: 'mkt_pune', name_mr: 'पुणे गुलटेकडी', name_en: 'Pune Market', dist_mr: 'पुणे', dist_en: 'Pune', dist_id: 'dist_pune' },
  { id: 'mkt_jalgaon', name_mr: 'जळगाव मंडी', name_en: 'Jalgaon APMC', dist_mr: 'जळगाव', dist_en: 'Jalgaon', dist_id: 'dist_jalgaon' },
  { id: 'mkt_solapur', name_mr: 'सोलापूर मंडी', name_en: 'Solapur APMC', dist_mr: 'सोलापूर', dist_en: 'Solapur', dist_id: 'dist_solapur' },
  { id: 'mkt_aurangabad', name_mr: 'छ. संभाजीनगर', name_en: 'Aurangabad', dist_mr: 'संभाजीनगर', dist_en: 'Aurangabad', dist_id: 'dist_aurangabad' },
  { id: 'mkt_yavatmal', name_mr: 'यवतमाळ मंडी', name_en: 'Yavatmal APMC', dist_mr: 'यवतमाळ', dist_en: 'Yavatmal', dist_id: 'dist_yavatmal' },
];

// ── Price chart — responsive, sleek 7-day visualization with gradient fills & trendline ──
const CHART_W = 330;
const CHART_H = 135;
const BAR_GAP = 8;

function PriceChart({ points }: { points: PricePoint[] }) {
  const numBars = points.length;
  if (numBars === 0) return null;
  const barW = (CHART_W - 32 - BAR_GAP * (numBars - 1)) / numBars;
  const prices = points.map(p => p.modal_paise_per_qtl);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const range = maxPrice - minPrice || 1;

  const barCenters = points.map((p, i) => {
    const normH = ((p.modal_paise_per_qtl - minPrice) / range) * (CHART_H - 38) + 18;
    const x = 16 + i * (barW + BAR_GAP) + barW / 2;
    const y = CHART_H - normH;
    return { x, y, modal: p.modal_paise_per_qtl };
  });

  let trendPath = '';
  if (barCenters.length > 1) {
    const first = barCenters[0]!;
    trendPath = `M ${first.x},${first.y}`;
    for (let i = 1; i < barCenters.length; i++) {
      const prev = barCenters[i - 1]!;
      const cur = barCenters[i]!;
      const mx = (prev.x + cur.x) / 2;
      trendPath += ` C ${mx},${prev.y} ${mx},${cur.y} ${cur.x},${cur.y}`;
    }
  }

  return (
    <View style={{ width: '100%', alignItems: 'center' }}>
      <Svg width="100%" height={CHART_H + 28} viewBox={`0 0 ${CHART_W} ${CHART_H + 28}`} style={{ maxWidth: 440 }}>
        <Defs>
          <LinearGradient id="todayBarGrad" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor={colors.primaryContainer} stopOpacity="1" />
            <Stop offset="1" stopColor={colors.primary} stopOpacity="0.85" />
          </LinearGradient>
          <LinearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#E2D7C5" stopOpacity="0.95" />
            <Stop offset="1" stopColor="#CDC0AB" stopOpacity="0.75" />
          </LinearGradient>
          <LinearGradient id="trendGlow" x1="0" y1="0" x2="1" y2="0">
            <Stop offset="0" stopColor={colors.primary} stopOpacity="0.4" />
            <Stop offset="1" stopColor={colors.primaryContainer} stopOpacity="0.9" />
          </LinearGradient>
        </Defs>

        {[0.15, 0.55, 0.95].map(frac => {
          const y = CHART_H * (1 - frac) + 6;
          return (
            <Line
              key={frac}
              x1={8}
              y1={y}
              x2={CHART_W - 8}
              y2={y}
              stroke="rgba(141,113,104,0.14)"
              strokeWidth={1}
              strokeDasharray="3,3"
            />
          );
        })}

        {points.map((p, i) => {
          const normH = ((p.modal_paise_per_qtl - minPrice) / range) * (CHART_H - 38) + 18;
          const x = 16 + i * (barW + BAR_GAP);
          const y = CHART_H - normH;
          const isToday = i === points.length - 1;
          const dayLabel = new Date(p.obs_date).toLocaleDateString(undefined, { weekday: 'short' }).slice(0, 3);

          return (
            <React.Fragment key={p.obs_date}>
              <Rect
                x={x}
                y={y}
                width={barW}
                height={normH}
                rx={6}
                fill={isToday ? 'url(#todayBarGrad)' : 'url(#barGrad)'}
                stroke={isToday ? colors.primary : 'transparent'}
                strokeWidth={isToday ? 1.5 : 0}
              />

              <SvgText
                x={x + barW / 2}
                y={CHART_H + 20}
                textAnchor="middle"
                fontSize={12}
                fontWeight={isToday ? '800' : '600'}
                fill={isToday ? colors.primary : colors.onSurfaceVariant}>
                {dayLabel}
              </SvgText>

              {isToday && (
                <SvgText
                  x={x + barW / 2}
                  y={Math.max(y - 6, 12)}
                  textAnchor="middle"
                  fontSize={11}
                  fontWeight="800"
                  fill={colors.primary}>
                  {formatPaise(p.modal_paise_per_qtl, 'en')}
                </SvgText>
              )}
            </React.Fragment>
          );
        })}

        {trendPath ? (
          <Path
            d={trendPath}
            fill="none"
            stroke="url(#trendGlow)"
            strokeWidth={2.4}
            strokeLinecap="round"
          />
        ) : null}

        {barCenters.length > 0 && (
          <Circle
            cx={barCenters[barCenters.length - 1]!.x}
            cy={barCenters[barCenters.length - 1]!.y}
            r={5}
            fill={colors.tertiary}
            stroke="#FFFFFF"
            strokeWidth={2}
          />
        )}
      </Svg>
    </View>
  );
}

async function fetchPrices(commodityId: string, marketId: string) {
  if (USE_FIXTURES) return fxSeriesFor(commodityId, marketId) ?? fxPriceSeries;
  return getPriceSeries(commodityId, marketId, 14);
}

async function fetchVerdict(commodityId: string, marketId: string) {
  if (USE_FIXTURES) return fxWindowFor(commodityId, marketId) ?? fxHold;
  return recommendWindow({
    commodity_id: commodityId,
    market_id: marketId,
    qty_kg: DEFAULT_QTY_KG,
    grade: DEFAULT_GRADE,
    lot_id: null,
    horizon_days: DEFAULT_HORIZON_DAYS,
  });
}

const redOnions = require('../../assets/images/red_onions.jpg');

export default function S04_Home({ navigation }: Props) {
  const { t, locale, setLocale } = useT();
  const { user } = useAuth();
  const selection = useSelection();
  const insets = useSafeAreaInsets();
  const [showVoiceTranscript, setShowVoiceTranscript] = useState(false);

  const parentNav = navigation as unknown as ParentNav;
  const goToLots = () => parentNav.navigate('MyLots', { screen: 'S15_MyLots' } as never);

  const marketId = selection.marketId ?? DEFAULT_MARKET_ID;
  const commodityId = selection.commodityId ?? DEFAULT_COMMODITY_ID;

  // Active crop and mandi
  const currentCrop = CROPS.find(c => c.id === commodityId) ?? CROPS[0]!;
  const currentMarket = POPULAR_MANDIS.find(m => m.id === marketId) ?? POPULAR_MANDIS[0]!;

  const cropDisplayName =
    locale === 'mr' ? currentCrop.name_mr : locale === 'hi' ? currentCrop.name_hi : currentCrop.name_en;
  const marketDisplayName =
    locale === 'mr' ? currentMarket.name_mr : currentMarket.name_en;

  const pricesQuery = useQuery({
    queryKey: ['home', 'prices', commodityId, marketId],
    queryFn: () => fetchPrices(commodityId, marketId),
    staleTime: 5 * 60 * 1000,
  });

  const lotsQuery = useQuery({
    queryKey: ['lots', 'mine'],
    queryFn: async () => (USE_FIXTURES ? fxMyLots : getLots()),
    staleTime: 5 * 60 * 1000,
  });
  const lots = lotsQuery.data ?? [];
  const lot = lots[0] ?? null;

  const verdictQuery = useQuery({
    queryKey: ['home', 'verdict', commodityId, marketId],
    queryFn: () => fetchVerdict(commodityId, marketId),
    staleTime: 5 * 60 * 1000,
  });

  const points = pricesQuery.data?.points ?? [];
  const last = points[points.length - 1];
  const prev = points.length >= 2 ? points[points.length - 2] : undefined;
  const recent7 = points.slice(-7);
  const minPaise = recent7.length ? Math.min(...recent7.map(p => p.min_paise_per_qtl)) : 0;
  const maxPaise = recent7.length ? Math.max(...recent7.map(p => p.max_paise_per_qtl)) : 0;
  const avgPaise = recent7.length
    ? Math.floor(recent7.reduce((s, p) => s + p.modal_paise_per_qtl, 0) / recent7.length)
    : 0;
  const deltaPaise = last && prev ? last.modal_paise_per_qtl - prev.modal_paise_per_qtl : 0;
  const isUp = deltaPaise >= 0;

  const verdict = verdictQuery.data;

  const streakDays = (() => {
    if (points.length < 3) return null;
    const rising = deltaPaise >= 0;
    let n = 0;
    for (let i = points.length - 1; i > 0; i -= 1) {
      const step = points[i]!.modal_paise_per_qtl - points[i - 1]!.modal_paise_per_qtl;
      if (rising ? step >= 0 : step < 0) n += 1;
      else break;
    }
    return n;
  })();

  const homeNarration = buildHomeNarration(
    {
      farmerName: user?.name ?? (locale === 'mr' ? 'शेतकरी मित्र' : locale === 'hi' ? 'किसान भाई' : 'Farmer'),
      marketName: marketDisplayName,
      cropName: cropDisplayName,
      latest: last ?? null,
      deltaPaise,
      streakDays,
      verdict: verdict ?? null,
      lotKg: DEFAULT_QTY_KG,
      holdCostPaisePerQtl: verdict?.costs.total_paise_per_qtl ?? null,
    },
    locale,
  );

  useScreenNarration(homeNarration, locale, {
    ready: !pricesQuery.isLoading && !verdictQuery.isLoading,
  });

  const switchLanguage = (target: Locale) => {
    setLocale(target);
  };

  return (
    <View style={styles.root}>
      <StatusBar barStyle="dark-content" backgroundColor={colors.background} />

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {/* ── 1. Top Navbar (mobile only — WebNavbar handles this on web) ── */}
        {Platform.OS !== 'web' && (
        <View style={[styles.topBar, { paddingTop: insets.top + space.xs }]}>
          <TouchableOpacity
            style={styles.menuBtn}
            onPress={() => navigation.getParent()?.getParent()?.navigate('Menu' as never)}
            accessibilityRole="button"
            accessibilityLabel={t('app_name')}>
            <View style={styles.hamburgerLine} />
            <View style={styles.hamburgerLine} />
            <View style={styles.hamburgerLine} />
          </TouchableOpacity>

          <View style={styles.topBrandGroup}>
            <Logo size={28} />
            <View>
              <Text style={styles.brandTitle}>{t('app_name')}</Text>
              <Text style={styles.brandSub}>
                {locale === 'mr' ? 'शेतकरी साथीदार' : locale === 'hi' ? 'किसान मित्र' : 'Farmer Intelligence'}
              </Text>
            </View>
          </View>

          {/* Quick 1-tap Language Switcher */}
          <View style={styles.topRightControls}>
            <View style={styles.langPill}>
              {(['mr', 'hi', 'en'] as Locale[]).map(lng => (
                <TouchableOpacity
                  key={lng}
                  style={[styles.langTab, locale === lng && styles.langTabActive]}
                  onPress={() => switchLanguage(lng)}>
                  <Text style={[styles.langTabText, locale === lng && styles.langTabTextActive]}>
                    {lng === 'mr' ? 'मरा' : lng === 'hi' ? 'हिं' : 'EN'}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <TouchableOpacity
              style={styles.topIconBtn}
              onPress={() => navigation.navigate('S38_Notifications')}
              accessibilityRole="button"
              accessibilityLabel={t('nt_title')}>
              <Icon name="bell" size={20} color={colors.primary} />
            </TouchableOpacity>
          </View>
        </View>
        )}

        {/* ── 2. Farmer Welcome & Location Ribbon ── */}
        <View style={styles.welcomeRibbon}>
          <View style={styles.welcomeTextGroup}>
            <Text style={styles.farmerSalutation}>
              {locale === 'mr'
                ? `रामराम, ${user?.name || 'शेतकरी मित्र'}`
                : locale === 'hi'
                ? `नमस्ते, ${user?.name || 'किसान भाई'}`
                : `Welcome, ${user?.name || 'Farmer'}`}
            </Text>
            <View style={styles.mandiLocationBadge}>
              <Icon name="map-pin" size={13} color={colors.primary} />
              <Text style={styles.mandiLocationText}>
                {marketDisplayName} ({currentMarket.dist_mr})
              </Text>
            </View>
          </View>

          <TouchableOpacity
            style={styles.mandiPickerBtn}
            onPress={() => parentNav.navigate('Prices', { screen: 'S5_Market' } as never)}>
            <Text style={styles.mandiPickerBtnText}>
              {locale === 'mr' ? 'मंडी बदला' : locale === 'hi' ? 'मंडी बदलें' : 'Change Mandi'}
            </Text>
            <Icon name="chevron-right" size={13} color={colors.primary} />
          </TouchableOpacity>
        </View>

        {/* ── 3. Quick Mandi Horizontal Chips ── */}
        <View style={styles.mandiChipsContainer}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.mandiScrollList}>
            {POPULAR_MANDIS.map(m => {
              const active = m.id === marketId;
              return (
                <TouchableOpacity
                  key={m.id}
                  style={[styles.mandiChip, active && styles.mandiChipActive]}
                  onPress={() => {
                    selection.setDistrict(m.dist_id);
                    selection.setMarket(m.id);
                  }}>
                  <Text style={[styles.mandiChipText, active && styles.mandiChipTextActive]}>
                    {locale === 'mr' ? m.name_mr : m.name_en}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </ScrollView>
        </View>

        {/* ── 4. Quick-Crop Horizontal Ribbon ── */}
        <View style={styles.cropRibbonSection}>
          <View style={styles.ribbonHeaderRow}>
            <Text style={styles.ribbonSectionTitle}>
              {locale === 'mr' ? '🌾 तुमचे पीक निवडा' : locale === 'hi' ? '🌾 अपनी फसल चुनें' : '🌾 Select Your Crop'}
            </Text>
            <Text style={styles.ribbonHint}>
              {locale === 'mr' ? 'थेट दर व सल्ला पहा' : locale === 'hi' ? 'लाइव भाव व सलाह' : 'Live Rates & Advice'}
            </Text>
          </View>

          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.cropScrollList}>
            {CROPS.map(c => {
              const isSelected = c.id === commodityId;
              const name = locale === 'mr' ? c.name_mr : locale === 'hi' ? c.name_hi : c.name_en;
              return (
                <TouchableOpacity
                  key={c.id}
                  style={[styles.cropCard, isSelected && styles.cropCardActive]}
                  onPress={() => selection.setCommodity(c.id)}>
                  <Text style={styles.cropIcon}>{c.icon}</Text>
                  <Text style={[styles.cropName, isSelected && styles.cropNameActive]}>{name}</Text>
                  <Text style={[styles.cropTag, isSelected && styles.cropTagActive]}>{c.tag}</Text>
                </TouchableOpacity>
              );
            })}
          </ScrollView>
        </View>

        {/* ── 5. Hero Voice Advisory Card ── */}
        <View style={styles.voiceHeroCard}>
          <View style={styles.voiceHeroHeader}>
            <View style={styles.voiceIconCircle}>
              <Icon name="volume" size={24} color={colors.onPrimary} />
            </View>
            <View style={styles.voiceHeroTextWrap}>
              <Text style={styles.voiceHeroTitle}>
                {locale === 'mr'
                  ? '🎙️ आजचा कृषी सल्ला ऐका'
                  : locale === 'hi'
                  ? '🎙️ आज की कृषि सलाह सुनें'
                  : "🎙️ Listen to Today's Advisory"}
              </Text>
              <Text style={styles.voiceHeroSubtitle}>
                {locale === 'mr'
                  ? `${cropDisplayName} भाव, आवक आणि विक्रीचा निर्णय आवाजात ऐका`
                  : locale === 'hi'
                  ? `${cropDisplayName} भाव, आवक और सलाह अपनी भाषा में सुनें`
                  : `Listen to ${cropDisplayName} prices, arrivals and selling window`}
              </Text>
            </View>
          </View>

          <View style={styles.voiceHeroActionRow}>
            <ListenButton
              large={true}
              text={homeNarration}
              label={locale === 'mr' ? 'सल्ला ऐका' : locale === 'hi' ? 'सलाह सुनें' : 'Listen Now'}
            />
            <TouchableOpacity
              style={styles.transcriptToggleBtn}
              onPress={() => setShowVoiceTranscript(!showVoiceTranscript)}>
              <Text style={styles.transcriptToggleText}>
                {showVoiceTranscript
                  ? locale === 'mr' ? 'मजकूर लपवा' : 'Hide Text'
                  : locale === 'mr' ? 'मजकूर वाचा' : 'Read Text'}
              </Text>
              <Icon name={showVoiceTranscript ? 'chevron-down' : 'chevron-right'} size={14} color={colors.primary} />
            </TouchableOpacity>
          </View>

          {showVoiceTranscript && (
            <View style={styles.transcriptBox}>
              <Text style={styles.transcriptTitle}>
                {locale === 'mr' ? '📝 आवाजी सल्ला मजकूर:' : '📝 Audio Narration Script:'}
              </Text>
              <Text style={styles.transcriptBody}>{homeNarration}</Text>
            </View>
          )}
        </View>

        {/* ── 6. Price Intelligence Card ── */}
        <View style={styles.priceCard}>
          {pricesQuery.isLoading ? (
            <Text style={styles.cardStatusText}>{t('loading_label')}</Text>
          ) : pricesQuery.isError || !last ? (
            <Text style={styles.cardErrorText}>{t('home_price_error')}</Text>
          ) : (
            <>
              {/* Header row with Crop name and Location */}
              <View style={styles.priceCardTopMeta}>
                <View style={styles.cropBadgePill}>
                  <Text style={styles.cropBadgePillText}>{cropDisplayName}</Text>
                </View>
                <Text style={styles.marketNameMeta}>{marketDisplayName}</Text>
              </View>

              <View style={styles.priceCardHeader}>
                <View>
                  <Text style={styles.priceCardLabel}>{t('home_todays_rate')}</Text>
                  <Text style={styles.priceHero}>
                    {formatPaise(last.modal_paise_per_qtl, locale)}
                    <Text style={styles.priceHeroUnit}> / क्विंटल</Text>
                  </Text>
                </View>

                <View style={styles.priceCardRight}>
                  {deltaPaise !== 0 && (
                    <View
                      style={[
                        styles.trendBadge,
                        !isUp && { backgroundColor: colors.criticalContainer, borderColor: 'rgba(185,28,28,0.2)' },
                      ]}>
                      <Icon
                        name={isUp ? 'trending-up' : 'trending-down'}
                        size={14}
                        color={isUp ? colors.tertiary : colors.critical}
                      />
                      <Text style={[styles.trendText, !isUp && { color: colors.critical }]}>
                        {isUp ? '+' : ''}
                        {formatPaise(deltaPaise, locale)}
                      </Text>
                    </View>
                  )}
                  <View style={styles.arrivalsPill}>
                    <Icon name="truck" size={13} color={colors.onSurfaceVariant} />
                    <Text style={styles.arrivalsText}>
                      {t('home_arrivals', { count: formatNumber(last.arrivals_qtl, locale) })}
                    </Text>
                  </View>
                </View>
              </View>

              {/* Min / Avg / Max 3-pillar stats */}
              <View style={styles.priceStats}>
                {[
                  { labelKey: 'home_min', labelMr: 'किमान दर', value: minPaise },
                  { labelKey: 'home_avg', labelMr: 'सरासरी दर', value: avgPaise },
                  { labelKey: 'home_max', labelMr: 'कमाल दर', value: maxPaise },
                ].map(({ labelMr, value }, idx) => (
                  <View key={idx} style={styles.priceStat}>
                    <Text style={styles.priceStatLabel}>{labelMr}</Text>
                    <Text style={styles.priceStatValue}>{formatPaise(value, locale)}</Text>
                  </View>
                ))}
              </View>

              {/* 7-day SVG chart */}
              <View style={styles.chartSection}>
                <View style={styles.chartHeader}>
                  <Icon name="chart-bar" size={14} color={colors.primary} />
                  <Text style={styles.chartLabel}>
                    {locale === 'mr' ? '७ दिवसांचा बाजार कल' : t('home_7day_climb')}
                  </Text>
                </View>
                <View style={styles.chartArea}>
                  <PriceChart points={recent7} />
                </View>
              </View>

              {/* AI Intelligence reliability */}
              <View style={styles.aiRow}>
                <View style={styles.aiIconBg}>
                  <Icon name="star" size={14} color={colors.primary} />
                </View>
                <Text style={styles.aiLabel}>
                  {locale === 'mr' ? 'अॅगमार्कनेट कृषी बुद्धिमत्ता (Agmarknet AI)' : t('home_ai_intelligence')}
                </Text>
                {verdict && (
                  <View style={styles.confidenceBadge}>
                    <Text style={styles.aiConfidence}>
                      {t('home_confidence_label', { level: t(`confidence_${verdict.confidence.toLowerCase()}`) })}
                    </Text>
                  </View>
                )}
              </View>
            </>
          )}
        </View>

        {/* ── 7. AI Selling Window Advisory Card ── */}
        <View style={styles.advisoryCard}>
          {verdictQuery.isLoading ? (
            <Text style={styles.cardStatusText}>{t('loading_label')}</Text>
          ) : verdictQuery.isError || !verdict ? (
            <Text style={styles.cardErrorText}>{t('home_verdict_error')}</Text>
          ) : (
            <>
              <View style={styles.advisoryHeader}>
                <View style={styles.advisoryFlag}>
                  <Icon name="shield-check" size={14} color={colors.onPrimary} />
                  <Text style={styles.advisoryFlagText}>
                    {locale === 'mr' ? 'विक्री सल्ला' : 'Selling Recommendation'}
                  </Text>
                </View>
                <Text style={styles.cropContextLabel}>{cropDisplayName}</Text>
              </View>

              {/* Prominent Action Banner */}
              <View style={styles.recommendationBanner}>
                <Text style={styles.advisoryRecommendation}>
                  {verdict.action === 'HOLD' && verdict.hold_days !== null
                    ? locale === 'mr'
                      ? `🟡 ${verdict.hold_days} दिवस थांबा (HOLD)`
                      : `🟡 Hold for ${verdict.hold_days} Days`
                    : verdict.action === 'SELL_NOW'
                    ? locale === 'mr'
                      ? '🔴 आजच विक्री करा (SELL NOW)'
                      : '🔴 Sell Today'
                    : verdict.action === 'SPLIT'
                    ? locale === 'mr'
                      ? `🟢 ५०% आज विका, उरलेला ${verdict.hold_days ?? 7} दिवस थांबा (SPLIT)`
                      : `🟢 Sell Half Now, Hold Half`
                    : verdict.action === 'SELL_ELSEWHERE'
                    ? locale === 'mr'
                      ? '🔵 इतर बाजारात जास्त दर (SELL ELSEWHERE)'
                      : '🔵 Sell Elsewhere'
                    : locale === 'mr'
                    ? '⚠️ अनिश्चित कल — सल्ला स्थगित'
                    : 'No Advice Due to Volatility'}
                </Text>
              </View>

              {/* Explanatory text */}
              <Text style={styles.advisoryExplain}>
                {locale === 'mr' ? verdict.explain_mr : verdict.explain_en}
              </Text>

              <Text style={styles.advisoryHoldCosts}>
                {locale === 'mr'
                  ? `साठवणूक, घट व वाहतूक खर्च: ${formatPaise(verdict.costs.total_paise_per_qtl, locale)} /क्विंटल`
                  : t('home_holding_costs', { cost: formatPaise(verdict.costs.total_paise_per_qtl, 'en') })}
              </Text>

              {/* Gain & Loss Row — INVARIANT I16: IDENTICAL FONT SIZE & PROMINENCE */}
              {verdict.expected_gain_paise !== null && verdict.worst_case_paise !== null && (
                <View style={styles.advisoryStats}>
                  <View style={[styles.advisoryStat, styles.gainStatBox]}>
                    <Text style={styles.advisoryStatLabel}>
                      {locale === 'mr'
                        ? `अपेक्षित फायदा (${Math.floor(DEFAULT_QTY_KG / 100)} क्विंटल)`
                        : t('home_expected_gain', { qty: String(Math.floor(DEFAULT_QTY_KG / 100)) })}
                    </Text>
                    <Text style={[styles.advisoryStatValue, { color: colors.tertiary }]}>
                      +{formatPaise(verdict.expected_gain_paise, locale)}
                    </Text>
                  </View>

                  <View style={styles.advisoryStatDivider} />

                  <View style={[styles.advisoryStat, styles.riskStatBox]}>
                    <Text style={styles.advisoryStatLabel}>
                      {locale === 'mr'
                        ? `कमाल जोखीम (${Math.floor(DEFAULT_QTY_KG / 100)} क्विंटल)`
                        : t('home_worst_case', { qty: String(Math.floor(DEFAULT_QTY_KG / 100)) })}
                    </Text>
                    <Text style={[styles.advisoryStatValue, { color: colors.critical }]}>
                      {formatPaise(verdict.worst_case_paise, locale)}
                    </Text>
                  </View>
                </View>
              )}

              {/* Scaled Visual Comparison Bars */}
              {verdict.expected_gain_paise !== null && verdict.worst_case_paise !== null && (
                <View style={styles.compareBars}>
                  {(() => {
                    const gain = Math.abs(verdict.expected_gain_paise);
                    const risk = Math.abs(verdict.worst_case_paise);
                    const peak = Math.max(gain, risk) || 1;
                    return (
                      <>
                        <View style={styles.compareRow}>
                          <View
                            style={[
                              styles.compareBar,
                              { width: `${(gain / peak) * 100}%`, backgroundColor: colors.positiveSolid },
                            ]}
                          />
                        </View>
                        <View style={styles.compareRow}>
                          <View
                            style={[
                              styles.compareBar,
                              { width: `${(risk / peak) * 100}%`, backgroundColor: colors.criticalSolid },
                            ]}
                          />
                        </View>
                      </>
                    );
                  })()}
                </View>
              )}

              <TouchableOpacity style={styles.costBreakdownBtn} onPress={() => navigation.navigate('S9_Verdict')}>
                <Icon name="clipboard" size={15} color={colors.primary} />
                <Text style={styles.costBreakdownText}>
                  {locale === 'mr'
                    ? `खर्चाचा संपूर्ण हिशोब पहा (${formatPaise(verdict.costs.total_paise_per_qtl, locale)} /क्विंटल)`
                    : t('home_cost_breakdown', { cost: formatPaise(verdict.costs.total_paise_per_qtl, 'en') })}
                </Text>
                <Icon name="chevron-right" size={15} color={colors.primary} />
              </TouchableOpacity>
            </>
          )}
        </View>

        {/* ── 8. My Lots Section ── */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>{t('home_active_lots')}</Text>
          <TouchableOpacity style={styles.sectionAction} onPress={goToLots}>
            <Text style={styles.sectionActionText}>{t('home_manage_all')}</Text>
            <Icon name="chevron-right" size={15} color={colors.primaryContainer} />
          </TouchableOpacity>
        </View>

        {lot === null ? (
          <View style={styles.lotCard}>
            <Text style={styles.lotEmptyText}>{t('home_no_lots')}</Text>
            <TouchableOpacity style={styles.lotPrimaryBtn} onPress={goToLots}>
              <Icon name="plus" size={16} color={colors.onPrimary} />
              <Text style={styles.lotPrimaryBtnText}>{t('home_list_lot')}</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <View style={styles.lotCard}>
            <View style={styles.lotCardHeader}>
              <Image source={redOnions} style={styles.lotPhoto} />
              <View style={styles.lotInfo}>
                <View style={styles.lotTitleRow}>
                  <Text style={styles.lotTitle} numberOfLines={1}>
                    {cropDisplayName} ({lot.grade ?? 'FAQ दर्जा'})
                  </Text>
                  <View style={styles.lotActiveBadge}>
                    <View style={styles.lotActiveDot} />
                    <Text style={styles.lotActiveText}>{t(`lot_status_${lot.status.toLowerCase()}`)}</Text>
                  </View>
                </View>
                <Text style={styles.lotSub}>
                  {t('home_stored_at', { location: marketDisplayName })}
                </Text>
              </View>
            </View>

            <View style={styles.lotStatsRow}>
              <View style={styles.lotStat}>
                <Text style={styles.lotStatLabel}>{t('home_qty_label')}</Text>
                <Text style={styles.lotStatValue}>
                  {formatQuintal(lot.qty_kg, locale)} {t('unit_quintal_short')}
                </Text>
              </View>
              <View style={styles.lotStat}>
                <Text style={styles.lotStatLabel}>{locale === 'mr' ? 'दर्जा (Grade)' : 'Grade'}</Text>
                <Text style={[styles.lotStatValue, { color: colors.primary }]}>{lot.grade ?? 'FAQ'}</Text>
              </View>
              <View style={styles.lotStat}>
                <Text style={styles.lotStatLabel}>{locale === 'mr' ? 'लॉट क्र.' : 'Lot #'}</Text>
                <Text style={styles.lotStatValue}>{lot.id.slice(-4).toUpperCase()}</Text>
              </View>
            </View>

            <View style={styles.lotActions}>
              <TouchableOpacity style={styles.lotPrimaryBtn} onPress={goToLots}>
                <Text style={styles.lotPrimaryBtnText}>{t('home_view_lot')}</Text>
                <Icon name="chevron-right" size={15} color={colors.onPrimary} />
              </TouchableOpacity>
            </View>

            <View style={styles.escrowRow}>
              <Icon name="shield-check" size={14} color={colors.tertiary} />
              <Text style={styles.escrowText}>{t('home_escrow_guarantee')}</Text>
            </View>
          </View>
        )}
        
        {Platform.OS === 'web' && <WebFooter />}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.background,
  },
  scrollContent: {
    paddingBottom: 90,
  },

  // Top bar
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: space.md,
    paddingBottom: space.sm,
    backgroundColor: colors.surface,
    zIndex: 1,
    borderBottomWidth: 1,
    borderBottomColor: colors.outlineVariant,
    ...cardShadow,
  },
  menuBtn: {
    width: 44,
    height: 44,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4.5,
    backgroundColor: colors.surfaceContainerLow,
    borderWidth: 1,
    borderColor: colors.outlineVariant,
  },
  hamburgerLine: {
    width: 22,
    height: 2.5,
    borderRadius: 1.5,
    backgroundColor: colors.onSurface,
  },
  topBrandGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flex: 1,
    marginLeft: 10,
  },
  brandTitle: {
    fontFamily: fontFamily.extraBold,
    fontSize: 20,
    color: colors.primary,
    letterSpacing: -0.2,
  },
  brandSub: {
    fontFamily: fontFamily.medium,
    fontSize: 11,
    color: colors.onSurfaceVariant,
    marginTop: -1,
  },
  topRightControls: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  langPill: {
    flexDirection: 'row',
    backgroundColor: colors.surfaceContainerHigh,
    borderRadius: radius.full,
    padding: 2,
    borderWidth: 1,
    borderColor: colors.outlineVariant,
  },
  langTab: {
    paddingHorizontal: 8,
    paddingVertical: 5,
    borderRadius: radius.full,
  },
  langTabActive: {
    backgroundColor: colors.primary,
  },
  langTabText: {
    fontFamily: fontFamily.bold,
    fontSize: 12,
    color: colors.onSurfaceVariant,
  },
  langTabTextActive: {
    color: colors.onPrimary,
  },
  topIconBtn: {
    width: 42,
    height: 42,
    borderRadius: 12,
    backgroundColor: colors.surfaceContainerLow,
    borderWidth: 1.5,
    borderColor: colors.outlineVariant,
    alignItems: 'center',
    justifyContent: 'center',
  },

  // Welcome & Mandi Ribbon
  welcomeRibbon: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: space.md,
    paddingVertical: space.sm,
    backgroundColor: colors.surfaceContainerLowest,
    borderBottomWidth: 1,
    borderBottomColor: colors.outlineVariant,
  },
  welcomeTextGroup: {
    flex: 1,
  },
  farmerSalutation: {
    fontFamily: fontFamily.bold,
    fontSize: 18,
    color: colors.onSurface,
    letterSpacing: -0.2,
  },
  mandiLocationBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 3,
  },
  mandiLocationText: {
    fontFamily: fontFamily.semiBold,
    fontSize: 14,
    color: colors.primary,
  },
  mandiPickerBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: radius.full,
    backgroundColor: colors.onPrimaryContainer,
    borderWidth: 1,
    borderColor: colors.primaryContainer,
  },
  mandiPickerBtnText: {
    fontFamily: fontFamily.bold,
    fontSize: 13,
    color: colors.primary,
  },

  // Mandi Horizontal Chips
  mandiChipsContainer: {
    paddingVertical: space.xs,
    backgroundColor: colors.background,
  },
  mandiScrollList: {
    paddingHorizontal: space.md,
    gap: 8,
  },
  mandiChip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: radius.full,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.outlineVariant,
  },
  mandiChipActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  mandiChipText: {
    fontFamily: fontFamily.semiBold,
    fontSize: 13,
    color: colors.onSurfaceVariant,
  },
  mandiChipTextActive: {
    color: colors.onPrimary,
    fontFamily: fontFamily.bold,
  },

  // Quick-Crop Ribbon Section
  cropRibbonSection: {
    marginTop: space.xs,
    marginBottom: space.sm,
  },
  ribbonHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: space.md,
    marginBottom: space.xs,
  },
  ribbonSectionTitle: {
    fontFamily: fontFamily.bold,
    fontSize: 16,
    color: colors.onSurface,
  },
  ribbonHint: {
    fontFamily: fontFamily.medium,
    fontSize: 12,
    color: colors.onSurfaceVariant,
  },
  cropScrollList: {
    paddingHorizontal: space.md,
    gap: 10,
    paddingVertical: 4,
  },
  cropCard: {
    width: 105,
    paddingVertical: 12,
    paddingHorizontal: 8,
    borderRadius: radius.lg,
    backgroundColor: colors.surface,
    borderWidth: 1.5,
    borderColor: colors.outlineVariant,
    alignItems: 'center',
    shadowColor: '#9A3412',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 6,
    elevation: 2,
  },
  cropCardActive: {
    backgroundColor: colors.onPrimaryContainer,
    borderColor: colors.primary,
    borderWidth: 2,
    shadowOpacity: 0.15,
  },
  cropIcon: {
    fontSize: 26,
    marginBottom: 4,
  },
  cropName: {
    fontFamily: fontFamily.bold,
    fontSize: 14,
    color: colors.onSurface,
    textAlign: 'center',
  },
  cropNameActive: {
    color: colors.primary,
  },
  cropTag: {
    fontFamily: fontFamily.medium,
    fontSize: 10,
    color: colors.onSurfaceVariant,
    marginTop: 2,
    textAlign: 'center',
  },
  cropTagActive: {
    color: colors.primaryContainer,
    fontFamily: fontFamily.bold,
  },

  // Voice Hero Card
  voiceHeroCard: {
    marginHorizontal: space.md,
    marginBottom: space.sm,
    padding: space.md,
    borderRadius: radius.lg,
    backgroundColor: '#FFF7ED',
    borderWidth: 1.5,
    borderColor: '#FDBA74',
    shadowColor: '#C2410C',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.12,
    shadowRadius: 10,
    elevation: 3,
  },
  voiceHeroHeader: {
    flexDirection: 'row',
    gap: space.sm,
    alignItems: 'center',
    marginBottom: space.sm,
  },
  voiceIconCircle: {
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  voiceHeroTextWrap: {
    flex: 1,
  },
  voiceHeroTitle: {
    fontFamily: fontFamily.extraBold,
    fontSize: 17,
    color: colors.primary,
  },
  voiceHeroSubtitle: {
    fontFamily: fontFamily.medium,
    fontSize: 13,
    color: colors.onSurfaceVariant,
    marginTop: 2,
    lineHeight: 18,
  },
  voiceHeroActionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: space.xs,
  },
  transcriptToggleBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  transcriptToggleText: {
    fontFamily: fontFamily.bold,
    fontSize: 13,
    color: colors.primary,
  },
  transcriptBox: {
    marginTop: space.sm,
    padding: space.sm,
    borderRadius: radius.md,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: '#FED7AA',
  },
  transcriptTitle: {
    fontFamily: fontFamily.bold,
    fontSize: 13,
    color: colors.primary,
    marginBottom: 4,
  },
  transcriptBody: {
    fontFamily: fontFamily.medium,
    fontSize: 14,
    lineHeight: 22,
    color: colors.onSurface,
  },

  // Price card
  cardStatusText: {
    fontFamily: fontFamily.medium,
    fontSize: 15,
    color: colors.onSurfaceVariant,
    padding: space.md,
  },
  cardErrorText: {
    fontFamily: fontFamily.bold,
    fontSize: 15,
    color: colors.critical,
    padding: space.md,
  },
  priceCard: {
    marginHorizontal: space.md,
    marginBottom: space.sm,
    padding: space.md,
    borderRadius: radius.lg,
    backgroundColor: colors.surface,
    borderWidth: 1.5,
    borderColor: colors.outlineVariant,
    ...cardShadow,
  },
  priceCardTopMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: space.xs,
  },
  cropBadgePill: {
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: radius.full,
    backgroundColor: colors.onPrimaryContainer,
    borderWidth: 1,
    borderColor: colors.primaryContainer,
  },
  cropBadgePillText: {
    fontFamily: fontFamily.bold,
    fontSize: 13,
    color: colors.primary,
  },
  marketNameMeta: {
    fontFamily: fontFamily.semiBold,
    fontSize: 14,
    color: colors.onSurfaceVariant,
  },
  priceCardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: space.sm,
  },
  priceCardLabel: {
    fontFamily: fontFamily.bold,
    fontSize: 13,
    color: colors.primary,
    letterSpacing: 0.5,
    textTransform: 'uppercase',
  },
  priceHero: {
    fontFamily: fontFamily.extraBold,
    fontSize: 38,
    color: colors.primary,
    letterSpacing: -0.5,
    lineHeight: 46,
  },
  priceHeroUnit: {
    fontFamily: fontFamily.bold,
    fontSize: 16,
    color: colors.onSurfaceVariant,
  },
  priceCardRight: {
    alignItems: 'flex-end',
    gap: 6,
  },
  trendBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: radius.full,
    backgroundColor: colors.positiveContainer,
    borderWidth: 1,
    borderColor: 'rgba(4,120,87,0.25)',
  },
  trendText: {
    fontFamily: fontFamily.extraBold,
    fontSize: 13,
    color: colors.tertiary,
  },
  arrivalsPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 2,
  },
  arrivalsText: {
    fontFamily: fontFamily.semiBold,
    fontSize: 13,
    color: colors.onSurfaceVariant,
    textAlign: 'right',
  },

  // Price stats
  priceStats: {
    flexDirection: 'row',
    borderRadius: radius.md,
    backgroundColor: colors.surfaceContainerLow,
    borderWidth: 1,
    borderColor: colors.outlineVariant,
    overflow: 'hidden',
    marginBottom: space.sm,
  },
  priceStat: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: space.sm,
    borderRightWidth: 1,
    borderRightColor: colors.outlineVariant,
  },
  priceStatLabel: {
    fontFamily: fontFamily.bold,
    fontSize: 12,
    color: colors.onSurfaceVariant,
    textTransform: 'uppercase',
    letterSpacing: 0.3,
  },
  priceStatValue: {
    fontFamily: fontFamily.extraBold,
    fontSize: 16,
    color: colors.onSurface,
    marginTop: 2,
  },

  // Chart
  chartSection: {
    marginBottom: space.sm,
  },
  chartHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: space.xs,
  },
  chartLabel: {
    fontFamily: fontFamily.bold,
    fontSize: 13,
    color: colors.primary,
    letterSpacing: 0.5,
  },
  chartArea: {
    alignItems: 'center',
  },

  // AI row
  aiRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingTop: space.sm,
    borderTopWidth: 1,
    borderTopColor: colors.outlineVariant,
  },
  aiIconBg: {
    width: 26,
    height: 26,
    borderRadius: 8,
    backgroundColor: 'rgba(155,47,0,0.1)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  aiLabel: {
    fontFamily: fontFamily.bold,
    fontSize: 13,
    color: colors.primary,
    flex: 1,
  },
  confidenceBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: radius.full,
    backgroundColor: colors.warningContainer,
  },
  aiConfidence: {
    fontFamily: fontFamily.bold,
    fontSize: 12,
    color: colors.warning,
  },

  // Advisory card
  advisoryCard: {
    marginHorizontal: space.md,
    marginBottom: space.sm,
    padding: space.md,
    borderRadius: radius.lg,
    backgroundColor: colors.onPrimaryContainer,
    borderWidth: 2,
    borderColor: colors.primaryContainer,
    shadowColor: '#C2410C',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.12,
    shadowRadius: 12,
    elevation: 3,
  },
  advisoryHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: space.xs,
  },
  advisoryFlag: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    backgroundColor: colors.primary,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: radius.full,
  },
  advisoryFlagText: {
    fontFamily: fontFamily.bold,
    fontSize: 12,
    color: colors.onPrimary,
    letterSpacing: 0.5,
    textTransform: 'uppercase',
  },
  cropContextLabel: {
    fontFamily: fontFamily.bold,
    fontSize: 14,
    color: colors.primary,
  },
  recommendationBanner: {
    marginVertical: space.xs,
  },
  advisoryRecommendation: {
    fontFamily: fontFamily.extraBold,
    fontSize: 20,
    color: colors.primary,
    letterSpacing: -0.2,
    lineHeight: 26,
  },
  advisoryExplain: {
    fontFamily: fontFamily.semiBold,
    fontSize: 15,
    lineHeight: 22,
    color: colors.onSurface,
    marginVertical: 4,
  },
  advisoryHoldCosts: {
    fontFamily: fontFamily.medium,
    fontSize: 13,
    color: colors.onSurfaceVariant,
    marginBottom: space.sm,
    lineHeight: 18,
  },
  advisoryStats: {
    flexDirection: 'row',
    borderRadius: radius.md,
    overflow: 'hidden',
    borderWidth: 1.5,
    borderColor: 'rgba(194,65,12,0.2)',
    marginBottom: space.sm,
  },
  advisoryStat: {
    flex: 1,
    padding: space.sm,
    alignItems: 'center',
  },
  gainStatBox: {
    backgroundColor: 'rgba(4,120,87,0.06)',
  },
  riskStatBox: {
    backgroundColor: 'rgba(185,28,28,0.06)',
  },
  advisoryStatDivider: {
    width: 1.5,
    backgroundColor: 'rgba(194,65,12,0.2)',
  },
  advisoryStatLabel: {
    fontFamily: fontFamily.bold,
    fontSize: 13,
    color: colors.onSurfaceVariant,
    textAlign: 'center',
    marginBottom: 3,
  },
  advisoryStatValue: {
    fontFamily: fontFamily.extraBold,
    fontSize: 24,
    letterSpacing: -0.3,
  },
  compareBars: {
    marginTop: space.xs,
    gap: 6,
  },
  compareRow: {
    height: 12,
    borderRadius: 6,
    backgroundColor: 'rgba(0,0,0,0.06)',
    overflow: 'hidden',
  },
  compareBar: {
    height: '100%',
    borderRadius: 6,
    minWidth: 8,
  },
  costBreakdownBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingVertical: 10,
    paddingHorizontal: space.sm,
    borderRadius: radius.md,
    backgroundColor: 'rgba(155,47,0,0.08)',
    borderWidth: 1,
    borderColor: 'rgba(155,47,0,0.18)',
    marginTop: space.sm,
  },
  costBreakdownText: {
    fontFamily: fontFamily.bold,
    fontSize: 14,
    color: colors.primary,
    flex: 1,
  },

  // Section header
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: space.md,
    marginTop: space.sm,
    marginBottom: space.xs,
  },
  sectionTitle: {
    fontFamily: fontFamily.bold,
    fontSize: 17,
    color: colors.onSurface,
  },
  sectionAction: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
  },
  sectionActionText: {
    fontFamily: fontFamily.bold,
    fontSize: 14,
    color: colors.primaryContainer,
  },

  // Lot card
  lotCard: {
    marginHorizontal: space.md,
    marginBottom: space.sm,
    padding: space.md,
    borderRadius: radius.lg,
    backgroundColor: colors.surface,
    borderWidth: 1.5,
    borderColor: colors.outlineVariant,
    ...cardShadow,
  },
  lotCardHeader: {
    flexDirection: 'row',
    gap: space.sm,
    marginBottom: space.sm,
  },
  lotPhoto: {
    width: 60,
    height: 60,
    borderRadius: radius.md,
    flexShrink: 0,
  },
  lotInfo: {
    flex: 1,
  },
  lotTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    flexWrap: 'wrap',
  },
  lotTitle: {
    fontFamily: fontFamily.bold,
    fontSize: 16,
    color: colors.onSurface,
  },
  lotActiveBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: radius.full,
    backgroundColor: colors.positiveContainer,
  },
  lotActiveDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.tertiary,
  },
  lotActiveText: {
    fontFamily: fontFamily.bold,
    fontSize: 11,
    color: colors.tertiary,
    letterSpacing: 0.4,
  },
  lotSub: {
    fontFamily: fontFamily.medium,
    fontSize: 13,
    color: colors.onSurfaceVariant,
    marginTop: 2,
  },
  lotEmptyText: {
    fontFamily: fontFamily.regular,
    fontSize: 16,
    lineHeight: 24,
    color: colors.onSurfaceVariant,
    marginBottom: space.sm,
  },
  lotStatsRow: {
    flexDirection: 'row',
    borderRadius: radius.md,
    backgroundColor: colors.surfaceContainerLow,
    borderWidth: 1,
    borderColor: colors.outlineVariant,
    overflow: 'hidden',
    marginBottom: space.sm,
  },
  lotStat: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: space.sm,
    borderRightWidth: 1,
    borderRightColor: colors.outlineVariant,
  },
  lotStatLabel: {
    fontFamily: fontFamily.bold,
    fontSize: 12,
    color: colors.onSurfaceVariant,
    textTransform: 'uppercase',
    letterSpacing: 0.3,
  },
  lotStatValue: {
    fontFamily: fontFamily.extraBold,
    fontSize: 15,
    color: colors.onSurface,
    marginTop: 2,
  },
  lotActions: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: space.xs,
  },
  lotPrimaryBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 12,
    borderRadius: radius.md,
    backgroundColor: colors.primaryContainer,
  },
  lotPrimaryBtnText: {
    fontFamily: fontFamily.bold,
    fontSize: 15,
    color: colors.onPrimary,
  },
  escrowRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    justifyContent: 'center',
    paddingTop: space.xs,
    borderTopWidth: 1,
    borderTopColor: colors.outlineVariant,
  },
  escrowText: {
    fontFamily: fontFamily.bold,
    fontSize: 13,
    color: colors.tertiary,
  },
});
