/**
 * CommoditySelector.tsx — Clean, Polished Agricultural Selector.
 *
 * Restores the beloved clean, compact layout:
 * ★ 3 Sleek Selector Pills: [📍 District] [🏛️ Mandi] [🧅 Crop]
 * ★ Instant Horizontal Crop Chips with Real Photography & 1-tap web onClick
 * ★ 100% Language Specific: Clean English when in EN, authentic Marathi in MR, Hindi in HI
 * ★ Zero Clutter: Compact and fast, with zero lag and zero backend calls.
 */

import React, { useState } from 'react';
import {
  Image,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { colors, fontFamily, radius, space } from '../../theme/tokens';
import { Icon } from '../ui/Icon';
import {
  STATIC_CROPS,
  STATIC_DISTRICTS,
  STATIC_MANDIS,
  StaticCrop,
} from '../../lib/staticMarketData';

interface Props {
  selectedCrop: StaticCrop;
  onSelectCrop: (crop: StaticCrop) => void;
  selectedDistrict: string;
  onSelectDistrict: (d: string) => void;
  selectedMandi: string;
  onSelectMandi: (m: string) => void;
  locale: 'mr' | 'hi' | 'en';
}

export function CommoditySelector({
  selectedCrop,
  onSelectCrop,
  selectedDistrict,
  onSelectDistrict,
  selectedMandi,
  onSelectMandi,
  locale,
}: Props) {
  const [openDropdown, setOpenDropdown] = useState<'district' | 'mandi' | 'crop' | null>(null);

  const isMr = locale === 'mr';
  const isHi = locale === 'hi';

  const toggleDropdown = (type: 'district' | 'mandi' | 'crop') => {
    setOpenDropdown(prev => (prev === type ? null : type));
  };

  const getCropTitle = (c: StaticCrop) => {
    if (isMr) return c.name_mr;
    if (isHi) return c.name_hi;
    return c.name;
  };

  const getDistrictTitle = (d: { name: string; name_mr: string; name_hi: string }) => {
    if (isMr) return d.name_mr;
    if (isHi) return d.name_hi;
    return d.name;
  };

  const getMandiTitle = (m: { name: string; name_mr: string; name_hi: string }) => {
    if (isMr) return m.name_mr;
    if (isHi) return m.name_hi;
    return m.name;
  };

  // Find active district object
  const activeDistObj = STATIC_DISTRICTS.find(
    d => d.name === selectedDistrict || d.name_mr === selectedDistrict || d.name_hi === selectedDistrict
  ) || STATIC_DISTRICTS[0];

  // Display labels
  const districtLabel = isMr ? activeDistObj.name_mr : isHi ? activeDistObj.name_hi : activeDistObj.name;
  const mandiCleanName = selectedMandi
    .replace(' मुख्य बाजार समिती', '')
    .replace(' बाजार समिती', '')
    .replace(' मुख्य मंडी', '')
    .replace(' APMC', '');

  return (
    <View style={styles.container}>
      {/* ── 1. The 3 Clean Selector Pills ─────────────────────── */}
      <View style={styles.pillsRow}>
        {/* District Pill */}
        <TouchableOpacity
          style={[styles.pill, openDropdown === 'district' && styles.pillActive]}
          onPress={() => toggleDropdown('district')}
          // @ts-ignore web native click
          onClick={() => toggleDropdown('district')}
          activeOpacity={0.8}
          accessibilityRole="button">
          <Icon name="navigation" size={14} color={colors.primary} />
          <Text style={styles.pillText} numberOfLines={1}>
            {districtLabel}
          </Text>
          <Icon
            name={openDropdown === 'district' ? 'chevron-up' : 'chevron-down'}
            size={13}
            color={colors.outline}
          />
        </TouchableOpacity>

        {/* Mandi Pill */}
        <TouchableOpacity
          style={[styles.pill, openDropdown === 'mandi' && styles.pillActive]}
          onPress={() => toggleDropdown('mandi')}
          // @ts-ignore web native click
          onClick={() => toggleDropdown('mandi')}
          activeOpacity={0.8}
          accessibilityRole="button">
          <Icon name="map-pin" size={14} color={colors.primary} />
          <Text style={styles.pillText} numberOfLines={1}>
            {mandiCleanName}
          </Text>
          <Icon
            name={openDropdown === 'mandi' ? 'chevron-up' : 'chevron-down'}
            size={13}
            color={colors.outline}
          />
        </TouchableOpacity>

        {/* Crop Pill with Real Thumbnail */}
        <TouchableOpacity
          style={[styles.pill, styles.pillHighlight, openDropdown === 'crop' && styles.pillActive]}
          onPress={() => toggleDropdown('crop')}
          // @ts-ignore web native click
          onClick={() => toggleDropdown('crop')}
          activeOpacity={0.8}
          accessibilityRole="button">
          <Image
            source={{ uri: selectedCrop.image }}
            style={styles.pillThumb}
            resizeMode="cover"
          />
          <Text style={[styles.pillText, styles.pillTextHighlight]} numberOfLines={1}>
            {getCropTitle(selectedCrop)}
          </Text>
          <Icon
            name={openDropdown === 'crop' ? 'chevron-up' : 'chevron-down'}
            size={13}
            color={colors.primary}
          />
        </TouchableOpacity>
      </View>

      {/* ── Dropdown: District ─────────────────────────────────── */}
      {openDropdown === 'district' && (
        <View style={styles.dropdownPanel}>
          <Text style={styles.dropdownTitle}>
            {isMr ? '📍 जिल्हा निवडा:' : isHi ? '📍 जिला चुनें:' : '📍 Select District:'}
          </Text>
          <View style={styles.dropdownGrid}>
            {STATIC_DISTRICTS.map(d => {
              const title = getDistrictTitle(d);
              const isSel = d.id === activeDistObj.id;
              return (
                <TouchableOpacity
                  key={d.id}
                  style={[styles.dropdownItem, isSel && styles.dropdownItemActive]}
                  onPress={() => {
                    onSelectDistrict(title);
                    onSelectMandi(isMr ? d.defaultMandi : d.defaultMandiEn || d.name + ' APMC');
                    setOpenDropdown(null);
                  }}
                  // @ts-ignore
                  onClick={() => {
                    onSelectDistrict(title);
                    onSelectMandi(isMr ? d.defaultMandi : d.defaultMandiEn || d.name + ' APMC');
                    setOpenDropdown(null);
                  }}
                  activeOpacity={0.75}
                  accessibilityRole="button">
                  <Text style={[styles.dropdownItemText, isSel && styles.dropdownItemTextActive]}>
                    {title}
                  </Text>
                  {isSel && <Icon name="check" size={13} color="#FFFFFF" />}
                </TouchableOpacity>
              );
            })}
          </View>
        </View>
      )}

      {/* ── Dropdown: Mandi ────────────────────────────────────── */}
      {openDropdown === 'mandi' && (
        <View style={styles.dropdownPanel}>
          <Text style={styles.dropdownTitle}>
            {isMr ? '🏛️ बाजार समिती (APMC) निवडा:' : isHi ? '🏛️ मंडी चुनें:' : '🏛️ Select APMC Mandi:'}
          </Text>
          <View style={styles.dropdownGrid}>
            {STATIC_MANDIS.map(m => {
              const title = getMandiTitle(m);
              const isSel = selectedMandi.includes(m.name) || selectedMandi.includes(m.name_mr);
              return (
                <TouchableOpacity
                  key={m.id}
                  style={[styles.dropdownItem, isSel && styles.dropdownItemActive]}
                  onPress={() => {
                    onSelectMandi(title);
                    setOpenDropdown(null);
                  }}
                  // @ts-ignore
                  onClick={() => {
                    onSelectMandi(title);
                    setOpenDropdown(null);
                  }}
                  activeOpacity={0.75}
                  accessibilityRole="button">
                  <Text style={[styles.dropdownItemText, isSel && styles.dropdownItemTextActive]}>
                    {title}
                  </Text>
                  {isSel && <Icon name="check" size={13} color="#FFFFFF" />}
                </TouchableOpacity>
              );
            })}
          </View>
        </View>
      )}

      {/* ── Dropdown: All 14 Crops Modal Grid ─────────────────── */}
      {openDropdown === 'crop' && (
        <View style={styles.dropdownPanel}>
          <Text style={styles.dropdownTitle}>
            {isMr ? '🌾 शेतीमाल निवडा (सर्व १४ पिके):' : isHi ? '🌾 फसल चुनें (सभी १४ फसलें):' : '🌾 Select Crop (All 14 Crops):'}
          </Text>
          <View style={styles.cropModalGrid}>
            {STATIC_CROPS.map(c => {
              const isSel = c.id === selectedCrop.id;
              const title = getCropTitle(c);
              return (
                <TouchableOpacity
                  key={c.id}
                  style={[styles.cropGridItem, isSel && styles.cropGridItemActive]}
                  onPress={() => {
                    onSelectCrop(c);
                    setOpenDropdown(null);
                  }}
                  // @ts-ignore
                  onClick={() => {
                    onSelectCrop(c);
                    setOpenDropdown(null);
                  }}
                  activeOpacity={0.8}
                  accessibilityRole="button">
                  <Image source={{ uri: c.image }} style={styles.cropGridImg} resizeMode="cover" />
                  <Text style={[styles.cropGridText, isSel && styles.cropGridTextActive]} numberOfLines={1}>
                    {title}
                  </Text>
                  <Text style={styles.cropGridPrice}>₹{c.heroPrice}</Text>
                  {isSel && (
                    <View style={styles.activeCheckBadge}>
                      <Icon name="check" size={11} color="#FFFFFF" />
                    </View>
                  )}
                </TouchableOpacity>
              );
            })}
          </View>
        </View>
      )}

      {/* ── 2. Sleek Horizontal Crop Chips Bar (1-Tap Selection) ── */}
      <View style={styles.chipsSection}>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.chipsScroll}>
          {STATIC_CROPS.map(c => {
            const isSel = c.id === selectedCrop.id;
            const title = getCropTitle(c);
            return (
              <TouchableOpacity
                key={c.id}
                style={[styles.chip, isSel && styles.chipActive]}
                onPress={() => onSelectCrop(c)}
                // @ts-ignore web native click
                onClick={(e: any) => {
                  if (e && e.preventDefault) e.preventDefault();
                  onSelectCrop(c);
                }}
                activeOpacity={0.75}
                accessibilityRole="button">
                <Image source={{ uri: c.image }} style={styles.chipThumb} resizeMode="cover" />
                <Text style={[styles.chipText, isSel && styles.chipTextActive]}>
                  {title}
                </Text>
                <Text style={[styles.chipPrice, isSel && styles.chipPriceActive]}>
                  ₹{c.heroPrice}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#FFFFFF',
    paddingVertical: space.xs + 2,
    borderBottomWidth: 1,
    borderBottomColor: colors.outlineVariant,
    width: '100%',
    marginBottom: space.sm,
    borderRadius: radius.md,
    shadowColor: '#000000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  pillsRow: {
    flexDirection: 'row',
    paddingHorizontal: space.sm,
    gap: space.xs,
    width: '100%',
  },
  pill: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 9,
    backgroundColor: '#FAF6EE',
    borderRadius: radius.md,
    borderWidth: 1.5,
    borderColor: '#E2D7C8',
    cursor: 'pointer' as any,
  },
  pillActive: {
    borderColor: colors.primary,
    backgroundColor: '#FFF8F5',
  },
  pillHighlight: {
    backgroundColor: '#FFF8F5',
    borderColor: 'rgba(155, 47, 0, 0.3)',
  },
  pillThumb: {
    width: 22,
    height: 22,
    borderRadius: 5,
  },
  pillText: {
    flex: 1,
    fontFamily: fontFamily.bold,
    fontSize: 13,
    color: colors.onSurface,
  },
  pillTextHighlight: {
    color: colors.primary,
  },
  dropdownPanel: {
    backgroundColor: '#FAF6EE',
    marginHorizontal: space.sm,
    marginTop: space.xs,
    padding: space.sm,
    borderRadius: radius.md,
    borderWidth: 1.5,
    borderColor: colors.primaryContainer,
  },
  dropdownTitle: {
    fontFamily: fontFamily.bold,
    fontSize: 13,
    color: colors.primary,
    marginBottom: space.xs,
  },
  dropdownGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  dropdownItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 7,
    backgroundColor: '#FFFFFF',
    borderRadius: radius.pill,
    borderWidth: 1.2,
    borderColor: '#DCC9A8',
    cursor: 'pointer' as any,
  },
  dropdownItemActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  dropdownItemText: {
    fontFamily: fontFamily.bold,
    fontSize: 12.5,
    color: colors.onSurface,
  },
  dropdownItemTextActive: {
    color: '#FFFFFF',
  },
  cropModalGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 7,
  },
  cropGridItem: {
    width: 76,
    backgroundColor: '#FFFFFF',
    borderRadius: radius.md,
    padding: 6,
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: '#E2D7C8',
    cursor: 'pointer' as any,
    position: 'relative',
  },
  cropGridItemActive: {
    borderColor: colors.primary,
    backgroundColor: '#FFF8F5',
  },
  cropGridImg: {
    width: 40,
    height: 40,
    borderRadius: 6,
    marginBottom: 3,
  },
  cropGridText: {
    fontFamily: fontFamily.bold,
    fontSize: 11.5,
    color: colors.onSurface,
    textAlign: 'center',
  },
  cropGridTextActive: {
    color: colors.primary,
  },
  cropGridPrice: {
    fontFamily: fontFamily.semiBold,
    fontSize: 11,
    color: colors.tertiary,
    marginTop: 1,
  },
  activeCheckBadge: {
    position: 'absolute',
    top: 3,
    right: 3,
    backgroundColor: colors.primary,
    width: 15,
    height: 15,
    borderRadius: 7.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
  chipsSection: {
    marginTop: space.xs,
    width: '100%',
  },
  chipsScroll: {
    paddingHorizontal: space.sm,
    gap: 8,
    paddingVertical: 3,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 11,
    paddingVertical: 7,
    backgroundColor: '#FAF6EE',
    borderRadius: radius.pill,
    borderWidth: 1.5,
    borderColor: '#E2D7C8',
    cursor: 'pointer' as any,
  },
  chipActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  chipThumb: {
    width: 22,
    height: 22,
    borderRadius: 11,
  },
  chipText: {
    fontFamily: fontFamily.bold,
    fontSize: 13,
    color: colors.onSurfaceVariant,
  },
  chipTextActive: {
    color: '#FFFFFF',
  },
  chipPrice: {
    fontFamily: fontFamily.bold,
    fontSize: 11.5,
    color: colors.tertiary,
    marginLeft: 2,
  },
  chipPriceActive: {
    color: '#FFE0B2',
  },
});
