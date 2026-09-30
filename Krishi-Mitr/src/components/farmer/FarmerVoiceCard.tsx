import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, TouchableOpacity, View, Image } from 'react-native';
import { colors, fontFamily, radius, space } from '../../theme/tokens';
import { Icon } from '../ui/Icon';
import { voiceService } from '../../lib/voiceService';
import { CommodityItem, MarketItem, getCommodityDisplayName, getMarketDisplayName } from '../../lib/commodity';

interface Props {
  cropName?: string;
  mandiName?: string;
  heroPrice?: number;
  projectedShift?: number;
  commodity?: CommodityItem;
  market?: MarketItem;
  price?: number;
  arrivalsTonnes?: string | number;
  projectedPrice?: number;
  isHold: boolean;
  locale: 'mr' | 'hi' | 'en';
}

export function FarmerVoiceCard({
  cropName,
  mandiName,
  heroPrice,
  projectedShift,
  commodity,
  market,
  price,
  arrivalsTonnes,
  projectedPrice,
  isHold,
  locale,
}: Props) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [showTranscript, setShowTranscript] = useState(false);

  const isMr = locale === 'mr';
  const isHi = locale === 'hi';

  const commName =
    cropName ||
    (commodity ? getCommodityDisplayName(commodity, locale) : '') ||
    (isMr ? 'कांदा' : isHi ? 'प्याज' : 'Onion');

  const mktName =
    mandiName ||
    (market ? getMarketDisplayName(market, locale) : '') ||
    (isMr ? 'लासलगाव मुख्य बाजार' : isHi ? 'लासलगांव मुख्य मंडी' : 'Lasalgaon APMC');

  const currentPrice = heroPrice ?? price ?? 2350;
  const arrivals = arrivalsTonnes ? String(arrivalsTonnes) : '1,395';
  const targetPrice =
    projectedPrice ?? (currentPrice + (projectedShift ?? (isHold ? 230 : -180)));

  const speechText = isMr
    ? ('नमस्कार रामभाऊ! आज ' + mktName + ' बाजारात ' + commName + ' चा अधिकृत भाव ₹' + currentPrice + ' प्रति क्विंटल आहे. आवक ' + arrivals + ' टन झाली आहे. पुढील १४ दिवसांत भाव ₹' + targetPrice + ' रुपयांपर्यंत जाण्याचा अंदाज आहे. सल्ला: ' + (isHold ? 'माल ५ ते ७ दिवस राखून ठेवा, अधिक नफा मिळेल.' : 'सध्याचा दर चांगला आहे, आजच विक्री करा.'))
    : isHi
    ? ('नमस्ते रामभाऊ! आज ' + mktName + ' मंडी में ' + commName + ' का भाव ₹' + currentPrice + ' प्रति क्विंटल है। मंडी में ' + arrivals + ' टन आवक है। १४ दिनों में भाव ₹' + targetPrice + ' तक जाने का अनुमान है। सलाह: ' + (isHold ? 'माल ५ से ७ दिन रोकें, अधिक लाभ मिलेगा।' : 'वर्तमान दर अच्छा है, आज ही बिक्री करें।'))
    : ('Hello! Today modal rate for ' + commName + ' in ' + mktName + ' is ₹' + currentPrice + ' per quintal, with ' + arrivals + ' tonnes arrived. 14-day projection expects ₹' + targetPrice + '. Recommendation: ' + (isHold ? 'Hold 5 to 7 days for peak profit.' : 'Sell today to lock in high rate.'));

  const handleTogglePlay = () => {
    if (isPlaying) {
      voiceService.stop();
      setIsPlaying(false);
    } else {
      voiceService.speak({
        text: speechText,
        lang: isMr ? 'mr-IN' : isHi ? 'hi-IN' : 'en-IN',
        onStart: () => setIsPlaying(true),
        onEnd: () => setIsPlaying(false),
        onError: () => setIsPlaying(false),
      });
    }
  };

  useEffect(() => {
    return () => {
      voiceService.stop();
    };
  }, []);

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <View style={styles.badge}>
          <View style={[styles.pulseDot, isPlaying && styles.pulseDotActive]} />
          <Text style={styles.badgeText}>
            {isMr ? 'आजचा कृषी ऑडिओ सल्ला' : isHi ? 'आज की मंडी ऑडियो सलाह' : 'Today Audio Advisory'}
          </Text>
        </View>
        <Text style={styles.langIndicator}>
          {isMr ? 'मराठी आवाज' : isHi ? 'हिंदी आवाज' : 'English Audio'}
        </Text>
      </View>

      <View style={styles.bodyRow}>
        <Image
          source={{ uri: '/images/farmer.jpg' }}
          style={styles.farmerPhoto}
          resizeMode="cover"
        />
        <View style={styles.contentCol}>
          <Text style={styles.mainTitle}>
            {isMr
              ? (commName + ': आज विकावे की थांबावे?')
              : isHi
              ? (commName + ': आज बेचें या रोकें?')
              : (commName + ': Sell Today or Hold?')}
          </Text>
          <Text style={styles.subTitle}>
            {isHold
              ? (isMr ? '१० ते १४ दिवसांत भाव वाढण्याची शक्यता (HOLD)' : isHi ? '१० से १४ दिनों में भाव बढ़ने की संभावना (HOLD)' : 'Prices projected to surge over 14 days (HOLD)')
              : (isMr ? 'सध्याचा दर उच्च आहे — विक्री फायद्याची (SELL)' : isHi ? 'वर्तमान दर उच्चतम है — आज ही बेचें (SELL)' : 'Rates at weekly high — sell now (SELL)')}
          </Text>
        </View>
      </View>

      <View style={styles.audioControlsRow}>
        <TouchableOpacity
          style={[styles.playBtn, isPlaying && styles.playBtnActive]}
          onPress={handleTogglePlay}
          activeOpacity={0.85}
          accessibilityRole="button"
          accessibilityLabel="Listen to Market Advisory">
          <Icon
            name={isPlaying ? 'square' : 'play'}
            size={18}
            color="#FFFFFF"
          />
          <Text style={styles.playBtnText}>
            {isPlaying
              ? (isMr ? 'सल्ला थांबवा (Stop)' : isHi ? 'रोकें (Stop)' : 'Stop Audio')
              : (isMr ? 'सल्ला ऐका (Listen)' : isHi ? 'सलाह सुनें (Listen)' : 'Listen Advisory')}
          </Text>
        </TouchableOpacity>

        <View style={styles.waveContainer}>
          {[14, 26, 18, 32, 16, 28, 20].map((h, idx) => (
            <View
              key={idx}
              style={[
                styles.waveBar,
                {
                  height: isPlaying ? h : 5,
                  backgroundColor: isPlaying ? colors.primary : colors.outlineVariant,
                },
              ]}
            />
          ))}
        </View>

        <TouchableOpacity
          style={styles.transcriptBtn}
          onPress={() => setShowTranscript(!showTranscript)}
          activeOpacity={0.7}>
          <Icon name="file-text" size={15} color={colors.primary} />
          <Text style={styles.transcriptBtnText}>
            {showTranscript ? (isMr ? 'लपवा' : 'Hide') : (isMr ? 'मजकूर वाचा' : 'Read')}
          </Text>
        </TouchableOpacity>
      </View>

      {showTranscript && (
        <View style={styles.transcriptBox}>
          <Text style={styles.transcriptText}>{speechText}</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: space.md,
    borderWidth: 1.5,
    borderColor: colors.borderActive,
    shadowColor: '#9B2F00',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 3,
    marginBottom: space.md,
    width: '100%',
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: space.sm,
  },
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(155, 47, 0, 0.08)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: radius.pill,
    gap: 6,
  },
  pulseDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.primary,
  },
  pulseDotActive: {
    backgroundColor: colors.tertiary,
  },
  badgeText: {
    fontFamily: fontFamily.bold,
    fontSize: 13,
    color: colors.primary,
  },
  langIndicator: {
    fontFamily: fontFamily.bold,
    fontSize: 13,
    color: colors.outline,
  },
  bodyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    marginBottom: space.md,
  },
  farmerPhoto: {
    width: 58,
    height: 58,
    borderRadius: 29,
    borderWidth: 2,
    borderColor: colors.primary,
    backgroundColor: colors.surfaceContainerLow,
  },
  contentCol: {
    flex: 1,
  },
  mainTitle: {
    fontFamily: fontFamily.extraBold,
    fontSize: 18,
    color: colors.onSurface,
    lineHeight: 24,
  },
  subTitle: {
    fontFamily: fontFamily.bold,
    fontSize: 14,
    color: colors.onSurfaceVariant,
    marginTop: 4,
    lineHeight: 20,
  },
  audioControlsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingTop: space.xs,
  },
  playBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: colors.primary,
    paddingVertical: 12,
    paddingHorizontal: 18,
    borderRadius: radius.pill,
    shadowColor: colors.primary,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 3,
  },
  playBtnActive: {
    backgroundColor: colors.critical,
  },
  playBtnText: {
    fontFamily: fontFamily.bold,
    fontSize: 15,
    color: '#FFFFFF',
  },
  waveContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    height: 34,
    flex: 1,
    justifyContent: 'center',
  },
  waveBar: {
    width: 4,
    borderRadius: 2,
  },
  transcriptBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingVertical: 9,
    paddingHorizontal: 12,
    backgroundColor: colors.surfaceContainerLow,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.outlineVariant,
  },
  transcriptBtnText: {
    fontFamily: fontFamily.bold,
    fontSize: 13,
    color: colors.primary,
  },
  transcriptBox: {
    marginTop: space.sm,
    padding: space.sm,
    backgroundColor: colors.surfaceContainerLow,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.outlineVariant,
  },
  transcriptText: {
    fontFamily: fontFamily.medium,
    fontSize: 14,
    color: colors.onSurface,
    lineHeight: 21,
  },
});
