/**
 * The landing page — web only.
 *
 * Provides a high-trust, polished visual gateway for farmers, buyers,
 * and SIH 2026 evaluators.
 *
 * ★ Synchronized global locale — selecting Marathi, Hindi, or English
 *   here sets the app's global i18n context immediately so no language
 *   choice is asked twice.
 * ★ Direct access doors for both full walkthrough and instant demo view.
 */

import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';

import { Logo } from '../../components/ui/Logo';
import { SpeakingFace } from '../../components/ui/SpeakingFace';
import { Icon, type IconName } from '../../components/ui/Icon';
import { useAuth } from '../../lib/auth';
import { useT } from '../../lib/i18n';
import { fxAuthRegistered, fxAuthRegisteredBuyer } from '../../fixtures/auth';
import { colors, fontFamily, radius, space, touch, type } from '../../theme/tokens';
import type { Locale } from '../../types/api';

const COPY: Record<
  Locale,
  {
    govBadge: string;
    tagline: string;
    subtagline: string;
    promise: string;
    farmerBadge: string;
    farmerTitle: string;
    farmerSub: string;
    farmerPerks: string[];
    farmerCta: string;
    farmerQuickDemo: string;
    buyerBadge: string;
    buyerTitle: string;
    buyerSub: string;
    buyerPerks: string[];
    buyerCta: string;
    pointsTitle: string;
    points: Array<{ title: string; desc: string; icon: IconName }>;
    footerNotice: string;
  }
> = {
  mr: {
    govBadge: 'SIH 2026 · महाराष्ट्र शासन कृषी विभाग',
    tagline: 'आज विकू की थांबू?',
    subtagline: 'खरा बाजारभाव, अचूक सल्ला आणि थेट शेतकरी-व्यापारी व्यापार',
    promise:
      'वाहतूक व हमाली वजा करून मिळणारा खरा नफा, कृत्रिम बुद्धिमत्तेचा पारदर्शक अंदाज — आणि नफा किती तसाच तोटा किती, दोन्ही एकाच आकारात.',
    farmerBadge: 'शेतकरी पोर्टल',
    farmerTitle: 'मी शेतकरी आहे',
    farmerSub: 'बाजारभाव तपासा, आवाज सल्ला ऐका आणि थेट खरेदीदारांशी व्यवहार करा',
    farmerPerks: [
      'हमाली व भाडे वजा केलेला निव्वळ भाव',
      '११ दिवसांचा जोखीम व नफा अंदाज (I16 नियम)',
      'प्रत्येक स्क्रीन मराठीत बोलून दाखवणारे ॲप',
    ],
    farmerCta: 'शेतकरी प्रवास सुरू करा',
    farmerQuickDemo: 'किंवा थेट डॅशबोर्ड बघा →',
    buyerBadge: 'खरेदीदार कन्सोल',
    buyerTitle: 'मी खरेदीदार / व्यापारी आहे',
    buyerSub: 'सत्यापित लॉट शोधा, मागणी टाका, डिजिटल सौदे करा आणि एस्क्रो सुरक्षा मिळवा',
    buyerPerks: [
      'गुणवत्ता ग्रेडिंग व फोटो पुरावा',
      'थेट शेतकरी करार व पारदर्शक काउंटर-ऑफर',
      '१००% सुरक्षित बँक एस्क्रो पेमेंट',
    ],
    buyerCta: 'व्यापारी कन्सोल उघडा',
    pointsTitle: 'Krishi Mitr चे ४ पारदर्शक नियम',
    points: [
      {
        title: 'नफा आणि जोखीम दोन्ही समान आकारात',
        desc: 'अंदाज दाखवताना केवळ मोठा नफा नाही, तर संभाव्य घटही समान ठळक आकारात स्पष्ट दिसते.',
        icon: 'trending-up',
      },
      {
        title: 'अंदाजात शंका असल्यास थेट नकार',
        desc: 'डेटा अपुरा असल्यास मॉडेल अंदाज न बांधता "सल्ला उपलब्ध नाही" सांगते.',
        icon: 'info',
      },
      {
        title: 'प्रत्येक स्क्रीन आवाजात वाचून दाखवते',
        desc: 'वाचण्याची सक्ती नाही; सर्व आकडे व सल्ले अस्खलित भाषेत ऐकवले जातात.',
        icon: 'volume',
      },
      {
        title: 'मध्यस्थ विरहित थेट एस्क्रो सुरक्षा',
        desc: 'माल स्वीकारल्याची पडताळणी झाल्यावरच थेट शेतकऱ्याच्या खात्यात रक्कम जमा.',
        icon: 'shield',
      },
    ],
    footerNotice: 'SIH २०२६ · समस्या क्रमांक २६१३२ · आधार क्रमांक संग्रहित केला जात नाही (I9)',
  },
  hi: {
    govBadge: 'SIH 2026 · महाराष्ट्र शासन कृषि विभाग',
    tagline: 'आज बेचूं या रुकूं?',
    subtagline: 'सच्चा मंडी भाव, सटीक सलाह और सीधा किसान-खरीदार व्यापार',
    promise:
      'भाड़ा और पल्लेदारी घटाकर मिलने वाला असली मुनाफा, एआई का पारदर्शी अनुमान — और फायदा कितना, जोखिम कितना, दोनों समान आकार में.',
    farmerBadge: 'किसान पोर्टल',
    farmerTitle: 'मैं किसान हूँ',
    farmerSub: 'मंडी भाव देखें, बोलकर सलाह सुनें और खरीदारों से सीधा सौदा करें',
    farmerPerks: [
      'भाड़ा काटकर मिलने वाला शुद्ध भाव',
      '११ दिनों का नफा-नुकसान पूर्वानुमान (I16)',
      'हर पन्ना हिंदी में बोलकर सुनाने की सुविधा',
    ],
    farmerCta: 'किसान यात्रा शुरू करें',
    farmerQuickDemo: 'या सीधा डैशबोर्ड देखें →',
    buyerBadge: 'खरीदार कंसोल',
    buyerTitle: 'मैं खरीदार / व्यापारी हूँ',
    buyerSub: 'सत्यापित लॉट खोजें, मांग डालें, डिजिटल सौदे करें और एस्क्रो सुरक्षा पाएं',
    buyerPerks: [
      'गुणवत्ता ग्रेडिंग व असली फोटो रिपोर्ट',
      'सीधे किसान से मोलभाव व काउंटर-ऑफर',
      '१००% सुरक्षित डिजिटल एस्क्रो भुगतान',
    ],
    buyerCta: 'व्यापारी कंसोल खोलें',
    pointsTitle: 'Krishi Mitr के ४ पारदर्शी नियम',
    points: [
      {
        title: 'मुनाफा और जोखिम दोनों समान आकार में',
        desc: 'पूर्वानुमान में केवल लाभ नहीं, बल्कि संभावित जोखिम भी पूरी स्पष्टता से दिखाया जाता है.',
        icon: 'trending-up',
      },
      {
        title: 'संदेह होने पर मॉडल साफ मना करता है',
        desc: 'डेटा अधूरा होने पर गलत सलाह देने के बजाय "सलाह उपलब्ध नहीं" कहता है.',
        icon: 'info',
      },
      {
        title: 'हर पन्ना बोलकर सुनाता है',
        desc: 'पढ़ने की मजबूरी नहीं; हर भाव और सलाह को स्थानीय भाषा में सुनाया जाता है.',
        icon: 'volume',
      },
      {
        title: 'बिचौलियों के बिना सीधा सुरक्षित एस्क्रो',
        desc: 'माल की डिलीवरी पुष्टि के बाद ही किसान के खाते में सुरक्षित भुगतान ट्रांसफर.',
        icon: 'shield',
      },
    ],
    footerNotice: 'SIH 2026 · समस्या कोड 26132 · कोई आधार डेटा संचित नहीं होता (I9)',
  },
  en: {
    govBadge: 'SIH 2026 · Govt of Maharashtra · Agriculture Dept',
    tagline: 'Sell today, or wait?',
    subtagline: 'Real Mandi Benchmark, Unbiased Advice & Direct Farmer-Buyer Trade',
    promise:
      'Real net payout after transport & mandi fees, AI quantile forecasting — and the downside shown at the exact same visual weight as the gain.',
    farmerBadge: 'Farmer Portal',
    farmerTitle: 'I am a Farmer',
    farmerSub: 'Track prices, listen to voice advisory, and sell directly to verified traders',
    farmerPerks: [
      'Net-in-hand rates after transport & handling',
      '11-day downside risk & expected upside (I16)',
      'Speaks every figure aloud in local language',
    ],
    farmerCta: 'Start Farmer Onboarding',
    farmerQuickDemo: 'or Jump Directly to Dashboard →',
    buyerBadge: 'Trader Console',
    buyerTitle: 'I am a Buyer / Trader',
    buyerSub: 'Browse verified farmer lots, submit bids, track delivery, and settle via escrow',
    buyerPerks: [
      'Diagnostic AI grading & photo inspection',
      'Direct-to-farm transparent counter-offers',
      'Milestone-driven escrow settlement',
    ],
    buyerCta: 'Launch Buyer Console',
    pointsTitle: 'Core Engineering Invariants',
    points: [
      {
        title: 'Dual Transparency: Gain & Risk Side-by-Side',
        desc: 'The worst case is displayed at the exact same font size and visual weight as the expected gain (Invariant I16).',
        icon: 'trending-up',
      },
      {
        title: 'Honest Refusal Under Low Confidence',
        desc: 'When mandi data is sparse or volatility spikes, the model says "No Advice" rather than guessing (Invariant I6).',
        icon: 'info',
      },
      {
        title: 'Voice First Multilingual Delivery',
        desc: 'Full screen narration in Marathi, Hindi, and English so literacy is never a barrier.',
        icon: 'volume',
      },
      {
        title: 'Middleman-Free Secure Escrow',
        desc: 'Payments are locked in escrow and released to the farmer only upon delivery verification.',
        icon: 'shield',
      },
    ],
    footerNotice: 'SIH 2026 · Problem Statement 26132 · Zero Aadhaar Storage (I9)',
  },
};

const LANGUAGES: Array<{ id: Locale; label: string }> = [
  { id: 'mr', label: 'मराठी' },
  { id: 'hi', label: 'हिंदी' },
  { id: 'en', label: 'English' },
];

export default function Landing() {
  const navigation = useNavigation<{ navigate: (screen: string) => void }>();
  const { signIn } = useAuth();
  const { locale, setLocale } = useT();
  const copy = COPY[locale] ?? COPY.mr;

  const handleFarmerStart = () => {
    navigation.navigate('S0_Splash');
  };

  const handleFarmerQuickDemo = async () => {
    await signIn(fxAuthRegistered);
  };

  const handleBuyerStart = () => {
    navigation.navigate('Buyer_Splash');
  };

  return (
    <ScrollView style={styles.root} contentContainerStyle={styles.content}>
      {/* ── Top Bar ────────────────────────────────────────── */}
      <View style={styles.topBar}>
        <View style={styles.brandRow}>
          <Logo size={42} />
          <View style={styles.brandTextGroup}>
            <Text style={styles.brandName}>Krishi Mitr</Text>
            <Text style={styles.brandSub}>कृषी मित्र</Text>
          </View>
        </View>

        {/* Global Language Selector — synchronizes whole app */}
        <View style={styles.langRow}>
          {LANGUAGES.map(language => {
            const active = language.id === locale;
            return (
              <Pressable
                key={language.id}
                onPress={() => setLocale(language.id)}
                accessibilityRole="button"
                accessibilityState={{ selected: active }}
                style={[styles.langChip, active && styles.langChipActive]}>
                <Text style={[styles.langChipText, active && styles.langChipTextActive]}>
                  {language.label}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </View>

      {/* ── Gov & Innovation Badge ─────────────────────────── */}
      <View style={styles.badgeContainer}>
        <View style={styles.govPill}>
          <View style={styles.pulseDot} />
          <Text style={styles.govPillText}>{copy.govBadge}</Text>
        </View>
      </View>

      {/* ── Hero Section ───────────────────────────────────── */}
      <View style={styles.hero}>
        <Text style={styles.tagline}>{copy.tagline}</Text>
        <Text style={styles.subtagline}>{copy.subtagline}</Text>
        <Text style={styles.promise}>{copy.promise}</Text>
      </View>

      {/* ── The Two Doors ──────────────────────────────────── */}
      <View style={styles.doors}>
        {/* Farmer Door */}
        <View style={[styles.door, styles.doorFarmer]}>
          <View style={styles.doorHeader}>
            <View style={styles.doorIconBgFarmer}>
              <SpeakingFace size={48} />
            </View>
            <View style={styles.badgeTagFarmer}>
              <Text style={styles.badgeTagFarmerText}>{copy.farmerBadge}</Text>
            </View>
          </View>

          <Text style={styles.doorTitle}>{copy.farmerTitle}</Text>
          <Text style={styles.doorSub}>{copy.farmerSub}</Text>

          <View style={styles.perksList}>
            {copy.farmerPerks.map((perk, i) => (
              <View key={i} style={styles.perkRow}>
                <Icon name="check-circle" size={14} color={colors.primary} />
                <Text style={styles.perkText}>{perk}</Text>
              </View>
            ))}
          </View>

          <Pressable
            onPress={handleFarmerStart}
            accessibilityRole="button"
            accessibilityLabel={copy.farmerCta}
            style={({ pressed }) => [styles.primaryCta, styles.primaryCtaFarmer, pressed && styles.ctaPressed]}>
            <Text style={styles.primaryCtaText}>{copy.farmerCta}</Text>
            <Icon name="arrow-right" size={18} color={colors.onPrimary} />
          </Pressable>

          <Pressable
            onPress={handleFarmerQuickDemo}
            accessibilityRole="button"
            style={styles.quickDemoLink}>
            <Text style={styles.quickDemoText}>{copy.farmerQuickDemo}</Text>
          </Pressable>
        </View>

        {/* Buyer Door */}
        <View style={[styles.door, styles.doorBuyer]}>
          <View style={styles.doorHeader}>
            <View style={styles.doorIconBgBuyer}>
              <Icon name="truck" size={38} color={colors.tertiary} />
            </View>
            <View style={styles.badgeTagBuyer}>
              <Text style={styles.badgeTagBuyerText}>{copy.buyerBadge}</Text>
            </View>
          </View>

          <Text style={styles.doorTitle}>{copy.buyerTitle}</Text>
          <Text style={styles.doorSub}>{copy.buyerSub}</Text>

          <View style={styles.perksList}>
            {copy.buyerPerks.map((perk, i) => (
              <View key={i} style={styles.perkRow}>
                <Icon name="check-circle" size={14} color={colors.tertiary} />
                <Text style={styles.perkText}>{perk}</Text>
              </View>
            ))}
          </View>

          <Pressable
            onPress={handleBuyerStart}
            accessibilityRole="button"
            accessibilityLabel={copy.buyerCta}
            style={({ pressed }) => [styles.primaryCta, styles.primaryCtaBuyer, pressed && styles.ctaPressed]}>
            <Text style={styles.primaryCtaText}>{copy.buyerCta}</Text>
            <Icon name="arrow-right" size={18} color={colors.onTertiary} />
          </Pressable>

          <Pressable
            onPress={async () => {
              await signIn(fxAuthRegisteredBuyer);
            }}
            accessibilityRole="button"
            style={styles.quickDemoLink}>
            <Text style={[styles.quickDemoText, { color: colors.tertiary }]}>
              {locale === 'mr'
                ? 'किंवा थेट खरेदीदार कन्सोल बघा →'
                : locale === 'hi'
                ? 'या सीधा खरीदार कंसोल देखें →'
                : 'or Instant Trader Dashboard →'}
            </Text>
          </Pressable>
        </View>
      </View>

      {/* ── 4 Invariant Highlights ─────────────────────────── */}
      <View style={styles.pointsSection}>
        <Text style={styles.pointsSectionTitle}>{copy.pointsTitle}</Text>
        <View style={styles.pointsGrid}>
          {copy.points.map((point, index) => (
            <View key={index} style={styles.pointCard}>
              <View style={styles.pointCardHeader}>
                <View style={styles.pointIconBg}>
                  <Icon name={point.icon} size={18} color={colors.primary} />
                </View>
                <Text style={styles.pointTitle}>{point.title}</Text>
              </View>
              <Text style={styles.pointDesc}>{point.desc}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* ── Footer ─────────────────────────────────────────── */}
      <View style={styles.footer}>
        <Text style={styles.footerText}>{copy.footerNotice}</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    paddingHorizontal: space.lg,
    paddingTop: space.md,
    paddingBottom: space.xxl,
    maxWidth: 1040,
    width: '100%',
    alignSelf: 'center',
  },

  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: space.sm,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(220,201,168,0.5)',
    marginBottom: space.md,
  },
  brandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.xs + 2,
  },
  brandTextGroup: {
    justifyContent: 'center',
  },
  brandName: {
    fontFamily: fontFamily.extraBold,
    fontSize: 20,
    color: colors.primary,
    letterSpacing: -0.5,
  },
  brandSub: {
    fontFamily: fontFamily.semiBold,
    fontSize: 11,
    color: colors.outline,
    marginTop: -2,
  },

  langRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.xs,
  },
  langChip: {
    paddingHorizontal: space.sm + 2,
    paddingVertical: space.xxs + 3,
    borderRadius: radius.full,
    borderWidth: 1.2,
    borderColor: colors.borderField,
    backgroundColor: colors.surface,
  },
  langChipActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
    elevation: 2,
  },
  langChipText: {
    fontFamily: fontFamily.medium,
    fontSize: 13,
    color: colors.onSurfaceVariant,
  },
  langChipTextActive: {
    fontFamily: fontFamily.bold,
    color: colors.onPrimary,
  },

  badgeContainer: {
    alignItems: 'center',
    marginTop: space.xs,
  },
  govPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: 'rgba(4,108,78,0.08)',
    borderWidth: 1,
    borderColor: 'rgba(4,108,78,0.25)',
    paddingHorizontal: space.md,
    paddingVertical: 5,
    borderRadius: radius.full,
  },
  pulseDot: {
    width: 8,
    height: 8,
    borderRadius: radius.full,
    backgroundColor: colors.tertiary,
  },
  govPillText: {
    fontFamily: fontFamily.semiBold,
    fontSize: 12,
    color: colors.tertiary,
    letterSpacing: 0.3,
  },

  hero: {
    alignItems: 'center',
    paddingTop: space.md,
    paddingBottom: space.lg,
  },
  tagline: {
    fontFamily: fontFamily.extraBold,
    fontSize: 34,
    color: colors.onSurface,
    textAlign: 'center',
    letterSpacing: -0.5,
    marginTop: space.xs,
  },
  subtagline: {
    fontFamily: fontFamily.bold,
    fontSize: 17,
    color: colors.primary,
    textAlign: 'center',
    marginTop: space.xxs,
  },
  promise: {
    fontFamily: fontFamily.regular,
    fontSize: 14.5,
    lineHeight: 22,
    color: colors.onSurfaceVariant,
    marginTop: space.sm,
    textAlign: 'center',
    maxWidth: 680,
  },

  doors: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: space.lg,
    justifyContent: 'center',
    marginBottom: space.xl,
  },
  door: {
    flexGrow: 1,
    flexBasis: 340,
    maxWidth: 480,
    backgroundColor: colors.surface,
    borderRadius: radius.xl,
    borderWidth: 1.5,
    padding: space.xl,
    shadowColor: '#1C1C17',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.06,
    shadowRadius: 16,
    elevation: 3,
  },
  doorFarmer: {
    borderColor: colors.borderActive,
  },
  doorBuyer: {
    borderColor: colors.tertiaryContainer,
  },
  doorHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: space.sm,
  },
  doorIconBgFarmer: {
    width: 64,
    height: 64,
    borderRadius: radius.lg,
    backgroundColor: 'rgba(155,47,0,0.08)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  doorIconBgBuyer: {
    width: 64,
    height: 64,
    borderRadius: radius.lg,
    backgroundColor: 'rgba(0,97,70,0.08)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeTagFarmer: {
    backgroundColor: colors.primary,
    paddingHorizontal: space.sm,
    paddingVertical: 3,
    borderRadius: radius.full,
  },
  badgeTagFarmerText: {
    fontFamily: fontFamily.bold,
    fontSize: 11,
    color: colors.onPrimary,
  },
  badgeTagBuyer: {
    backgroundColor: colors.tertiary,
    paddingHorizontal: space.sm,
    paddingVertical: 3,
    borderRadius: radius.full,
  },
  badgeTagBuyerText: {
    fontFamily: fontFamily.bold,
    fontSize: 11,
    color: colors.onTertiary,
  },

  doorTitle: {
    fontFamily: fontFamily.extraBold,
    fontSize: 22,
    color: colors.onSurface,
    marginTop: space.xs,
  },
  doorSub: {
    fontFamily: fontFamily.regular,
    fontSize: 13.5,
    color: colors.onSurfaceVariant,
    marginTop: space.xxs,
    lineHeight: 19,
    minHeight: 38,
  },

  perksList: {
    marginTop: space.md,
    marginBottom: space.lg,
    gap: space.xs,
  },
  perkRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  perkText: {
    fontFamily: fontFamily.medium,
    fontSize: 13,
    color: colors.onSurface,
  },

  primaryCta: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    minHeight: 48,
    borderRadius: radius.full,
    paddingHorizontal: space.lg,
  },
  primaryCtaFarmer: {
    backgroundColor: colors.primary,
  },
  primaryCtaBuyer: {
    backgroundColor: colors.tertiary,
  },
  primaryCtaText: {
    fontFamily: fontFamily.bold,
    fontSize: 15,
    color: '#FFFFFF',
  },
  ctaPressed: {
    opacity: 0.88,
    transform: [{ scale: 0.99 }],
  },

  quickDemoLink: {
    alignItems: 'center',
    marginTop: space.sm,
    paddingVertical: space.xs,
  },
  quickDemoText: {
    fontFamily: fontFamily.semiBold,
    fontSize: 12.5,
    color: colors.primary,
    textDecorationLine: 'underline',
  },

  pointsSection: {
    marginTop: space.lg,
    backgroundColor: colors.surfaceContainerLow,
    borderRadius: radius.xl,
    borderWidth: 1,
    borderColor: colors.borderCard,
    padding: space.xl,
  },
  pointsSectionTitle: {
    fontFamily: fontFamily.extraBold,
    fontSize: 20,
    color: colors.onSurface,
    marginBottom: space.lg,
    textAlign: 'center',
  },
  pointsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: space.md,
  },
  pointCard: {
    flexGrow: 1,
    flexBasis: 220,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: space.md,
    borderWidth: 1,
    borderColor: colors.borderCard,
  },
  pointCardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: space.xs,
  },
  pointIconBg: {
    width: 32,
    height: 32,
    borderRadius: 8,
    backgroundColor: 'rgba(155,47,0,0.08)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  pointTitle: {
    fontFamily: fontFamily.bold,
    fontSize: 14,
    color: colors.onSurface,
    flex: 1,
  },
  pointDesc: {
    fontFamily: fontFamily.regular,
    fontSize: 12.5,
    lineHeight: 18,
    color: colors.onSurfaceVariant,
  },

  footer: {
    marginTop: space.xl,
    paddingTop: space.md,
    borderTopWidth: 1,
    borderTopColor: 'rgba(220,201,168,0.5)',
    alignItems: 'center',
  },
  footerText: {
    fontFamily: fontFamily.medium,
    fontSize: 12,
    color: colors.outline,
    textAlign: 'center',
  },
});

