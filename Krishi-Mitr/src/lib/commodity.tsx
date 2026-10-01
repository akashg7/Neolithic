import React, { createContext, useContext, useState, useEffect } from 'react';
import { getAppInit } from './api';

export interface CommodityItem {
  id: string;
  name: string;
  name_mr: string;
  icon?: string;
}

export interface MarketItem {
  id: string;
  name: string;
  name_mr: string;
  district_name?: string;
}

export interface DistrictItem {
  id: string;
  name: string;
  name_mr: string;
}

export const COMMODITY_MR_NAMES: Record<string, string> = {
  Onion: 'कांदा',
  Soyabean: 'सोयाबीन',
  Soybean: 'सोयाबीन',
  Cotton: 'कापूस',
  Wheat: 'गहू',
  Tomato: 'टोमॅटो',
  'Bengal Gram': 'हरभरा (चना)',
  Maize: 'मका',
  'Green Chilli': 'हिरवी मिरची',
  Turmeric: 'हळद',
  Groundnut: 'भुईमूग',
  Pomegranate: 'डाळिंब',
  Grapes: 'द्राक्षे',
  Sugarcane: 'ऊस',
  Potato: 'बटाटा',
  Banana: 'केळी',
  Ginger: 'आले',
  Garlic: 'लसूण',
  Jowar: 'ज्वारी',
  Rice: 'तांदूळ',
};

export const COMMODITY_HI_NAMES: Record<string, string> = {
  Onion: 'प्याज',
  Soyabean: 'सोयाबीन',
  Soybean: 'सोयाबीन',
  Cotton: 'कपास',
  Wheat: 'गेहूं',
  Tomato: 'टमाटर',
  'Bengal Gram': 'चना',
  Maize: 'मक्का',
  'Green Chilli': 'हरी मिर्च',
  Turmeric: 'हल्दी',
  Groundnut: 'मूंगफली',
  Pomegranate: 'अनार',
  Grapes: 'अंगूर',
  Sugarcane: 'गन्ना',
  Potato: 'आलू',
  Banana: 'केला',
  Ginger: 'अदरक',
  Garlic: 'लहसुन',
  Jowar: 'ज्वार',
  Rice: 'चावल',
};

export const COMMODITY_ICONS: Record<string, string> = {
  Onion: '🧅',
  Soyabean: '🫘',
  Soybean: '🫘',
  Cotton: '⚪',
  Wheat: '🌾',
  Tomato: '🍅',
  'Bengal Gram': '🟤',
  Maize: '🌽',
  'Green Chilli': '🌶️',
  Turmeric: '🟡',
  Groundnut: '🥜',
  Pomegranate: '🍎',
  Grapes: '🍇',
  Sugarcane: '🎋',
  Potato: '🥔',
  Banana: '🍌',
  Ginger: '🫚',
  Garlic: '🧄',
  Jowar: '🌾',
  Rice: '🌾',
};

export const MARKET_MR_NAMES: Record<string, string> = {
  'Lasalgaon APMC': 'लासलगाव मुख्य बाजार',
  'Latur APMC': 'लातूर सोयाबीन मुख्य मंडी',
  'Pune APMC': 'पुणे गुलटेकडी बाजार समिती',
  'Pune(Moshi) APMC': 'पुणे (मोशी) बाजार समिती',
  'Baramati APMC': 'बारामती बाजार समिती',
  'Junnar APMC': 'जुन्नर (नारायणगाव) बाजार समिती',
  'Ahilyanagar APMC': 'अहिल्यानगर मुख्य बाजार',
  'Kopargaon APMC': 'कोपरगाव बाजार समिती',
  'Rahata APMC': 'राहाता बाजार समिती',
  'Jalgaon APMC': 'जळगाव कृषी बाजार समिती',
  'Chalisgaon APMC': 'चाळीसगाव बाजार समिती',
  'Yavatmal APMC': 'यवतमाळ कापूस मंडी',
  'Wani APMC': 'वणी बाजार समिती',
  'Solapur APMC': 'सोलापूर कृषी उत्पन्न बाजार',
  'Pandharpur APMC': 'पंढरपूर बाजार समिती',
  'Chattrapati Sambhajinagar APMC': 'छत्रपती संभाजीनगर (जाधववाडी)',
  'Vaijapur APMC': 'वैजापूर बाजार समिती',
  'Nashik APMC': 'नाशिक कृषी उत्पन्न बाजार समिती',
  'Pimpalgaon APMC': 'पिंपळगाव बसवंत बाजार समिती',
  'Yeola APMC': 'येवला बाजार समिती',
  'Satana APMC': 'सटाणा बाजार समिती',
  'Udgir APMC': 'उदगीर बाजार समिती',
  'Nagpur APMC': 'नागपूर संत्रा व धान्य बाजार',
  'Kolhapur APMC': 'कोल्हापूर गूळ व शेतीमाल बाजार',
  'Sangli APMC': 'सांगली हळद बाजार समिती',
  'Amravati APMC': 'अमरावती बाजार समिती',
  'Vashi APMC': 'वाशी मुंबई कृषी उत्पन्न बाजार समिती',
};

export const INITIAL_DISTRICTS: DistrictItem[] = [
  { id: '1', name: 'Nashik', name_mr: 'नाशिक' },
  { id: '2', name: 'Latur', name_mr: 'लातूर' },
  { id: '3', name: 'Ahmednagar', name_mr: 'अहिल्यानगर' },
  { id: '4', name: 'Pune', name_mr: 'पुणे' },
  { id: '5', name: 'Jalgaon', name_mr: 'जळगाव' },
  { id: '6', name: 'Yavatmal', name_mr: 'यवतमाळ' },
  { id: '7', name: 'Solapur', name_mr: 'सोलापूर' },
  { id: '8', name: 'Chhatrapati Sambhajinagar', name_mr: 'छत्रपती संभाजीनगर' },
  { id: '9', name: 'Nagpur', name_mr: 'नागपूर' },
  { id: '10', name: 'Amravati', name_mr: 'अमरावती' },
  { id: '11', name: 'Kolhapur', name_mr: 'कोल्हापूर' },
  { id: '12', name: 'Sangli', name_mr: 'सांगली' },
  { id: '13', name: 'Nanded', name_mr: 'नांदेड' },
  { id: '14', name: 'Beed', name_mr: 'बीड' },
  { id: '15', name: 'Dharashiv', name_mr: 'धाराशिव' },
];

export const INITIAL_COMMODITIES: CommodityItem[] = [
  { id: '1', name: 'Onion', name_mr: 'कांदा', icon: '🧅' },
  { id: '2', name: 'Soyabean', name_mr: 'सोयाबीन', icon: '🫘' },
  { id: '3', name: 'Cotton', name_mr: 'कापूस', icon: '⚪' },
  { id: '4', name: 'Wheat', name_mr: 'गहू', icon: '🌾' },
  { id: '5', name: 'Tomato', name_mr: 'टोमॅटो', icon: '🍅' },
  { id: '6', name: 'Bengal Gram', name_mr: 'हरभरा (चना)', icon: '🟤' },
  { id: '7', name: 'Maize', name_mr: 'मका', icon: '🌽' },
  { id: '8', name: 'Green Chilli', name_mr: 'हिरवी मिरची', icon: '🌶️' },
  { id: '9', name: 'Turmeric', name_mr: 'हळद', icon: '🟡' },
  { id: '10', name: 'Groundnut', name_mr: 'भुईमूग', icon: '🥜' },
  { id: '11', name: 'Pomegranate', name_mr: 'डाळिंब', icon: '🍎' },
  { id: '12', name: 'Grapes', name_mr: 'द्राक्षे', icon: '🍇' },
  { id: '13', name: 'Sugarcane', name_mr: 'ऊस', icon: '🎋' },
  { id: '14', name: 'Potato', name_mr: 'बटाटा', icon: '🥔' },
  { id: '15', name: 'Banana', name_mr: 'केळी', icon: '🍌' },
  { id: '16', name: 'Ginger', name_mr: 'आले', icon: '🫚' },
  { id: '17', name: 'Garlic', name_mr: 'लसूण', icon: '🧄' },
  { id: '18', name: 'Jowar', name_mr: 'ज्वारी', icon: '🌾' },
];

export const INITIAL_MARKETS: MarketItem[] = [
  { id: '1', name: 'Lasalgaon APMC', name_mr: 'लासलगाव मुख्य बाजार', district_name: 'Nashik' },
  { id: '2', name: 'Latur APMC', name_mr: 'लातूर सोयाबीन मुख्य मंडी', district_name: 'Latur' },
  { id: '3', name: 'Pune APMC', name_mr: 'पुणे गुलटेकडी बाजार समिती', district_name: 'Pune' },
  { id: '4', name: 'Ahilyanagar APMC', name_mr: 'अहिल्यानगर मुख्य बाजार', district_name: 'Ahmednagar' },
  { id: '5', name: 'Jalgaon APMC', name_mr: 'जळगाव कृषी बाजार समिती', district_name: 'Jalgaon' },
  { id: '6', name: 'Yavatmal APMC', name_mr: 'यवतमाळ कापूस मंडी', district_name: 'Yavatmal' },
  { id: '7', name: 'Solapur APMC', name_mr: 'सोलापूर कृषी उत्पन्न बाजार', district_name: 'Solapur' },
  { id: '8', name: 'Chattrapati Sambhajinagar APMC', name_mr: 'छत्रपती संभाजीनगर (जाधववाडी)', district_name: 'Chhatrapati Sambhajinagar' },
  { id: '9', name: 'Pimpalgaon APMC', name_mr: 'पिंपळगाव बसवंत बाजार समिती', district_name: 'Nashik' },
  { id: '10', name: 'Yeola APMC', name_mr: 'येवला बाजार समिती', district_name: 'Nashik' },
  { id: '11', name: 'Udgir APMC', name_mr: 'उदगीर बाजार समिती', district_name: 'Latur' },
  { id: '12', name: 'Baramati APMC', name_mr: 'बारामती बाजार समिती', district_name: 'Pune' },
  { id: '13', name: 'Junnar APMC', name_mr: 'जुन्नर (नारायणगाव) बाजार', district_name: 'Pune' },
  { id: '14', name: 'Kopargaon APMC', name_mr: 'कोपरगाव बाजार समिती', district_name: 'Ahmednagar' },
  { id: '15', name: 'Chalisgaon APMC', name_mr: 'चाळीसगाव बाजार समिती', district_name: 'Jalgaon' },
  { id: '16', name: 'Wani APMC', name_mr: 'वणी बाजार समिती', district_name: 'Yavatmal' },
  { id: '17', name: 'Pandharpur APMC', name_mr: 'पंढरपूर बाजार समिती', district_name: 'Solapur' },
  { id: '18', name: 'Nagpur APMC', name_mr: 'नागपूर संत्रा व धान्य बाजार', district_name: 'Nagpur' },
  { id: '19', name: 'Kolhapur APMC', name_mr: 'कोल्हापूर गूळ व शेतीमाल बाजार', district_name: 'Kolhapur' },
  { id: '20', name: 'Sangli APMC', name_mr: 'सांगली हळद बाजार समिती', district_name: 'Sangli' },
];

export function getCommodityDisplayName(c?: CommodityItem | null, locale: string = 'mr'): string {
  if (!c) return '';
  if (locale === 'mr') return c.name_mr || COMMODITY_MR_NAMES[c.name] || c.name || '';
  if (locale === 'hi') return COMMODITY_HI_NAMES[c.name] || c.name_mr || c.name || '';
  return c.name || '';
}

export function getCommodityIcon(name?: string): string {
  if (!name) return '🌾';
  return COMMODITY_ICONS[name] || '🌾';
}

export function getMarketDisplayName(m?: MarketItem | null, locale: string = 'mr'): string {
  if (!m) return '';
  if (locale === 'mr') return m.name_mr || m.name || '';
  return m.name || '';
}

export function getDistrictDisplayName(d?: DistrictItem | null, locale: string = 'mr'): string {
  if (!d) return '';
  if (locale === 'mr' || locale === 'hi') return d.name_mr || d.name || '';
  return d.name || '';
}

interface CommodityContextValue {
  commodities: CommodityItem[];
  markets: MarketItem[];
  districts: DistrictItem[];
  selectedCommodity: CommodityItem;
  selectedMarket: MarketItem;
  selectedDistrict: DistrictItem;
  setCommodity: (c: CommodityItem) => void;
  setMarket: (m: MarketItem) => void;
  setDistrict: (d: DistrictItem) => void;
}

const CommodityContext = createContext<CommodityContextValue | null>(null);

export function CommodityProvider({ children }: { children: React.ReactNode }) {
  const [commodities, setCommodities] = useState<CommodityItem[]>(INITIAL_COMMODITIES);
  const [markets, setMarkets] = useState<MarketItem[]>(INITIAL_MARKETS);
  const [districts, setDistricts] = useState<DistrictItem[]>(INITIAL_DISTRICTS);
  const [selectedCommodity, setSelectedCommodity] = useState<CommodityItem>(INITIAL_COMMODITIES[0]!);
  const [selectedMarket, setSelectedMarket] = useState<MarketItem>(INITIAL_MARKETS[0]!);
  const [selectedDistrict, setSelectedDistrict] = useState<DistrictItem>(INITIAL_DISTRICTS[0]!);

  useEffect(() => {
    getAppInit()
      .then(res => {
        if (res.commodities && res.commodities.length > 0) {
          const list: CommodityItem[] = res.commodities.map(c => ({
            id: String(c.id),
            name: c.name,
            name_mr: COMMODITY_MR_NAMES[c.name] || c.name,
            icon: COMMODITY_ICONS[c.name] || '🌾',
          }));
          setCommodities(list);
        }
        if (res.markets && res.markets.length > 0) {
          const list: MarketItem[] = res.markets.map(m => ({
            id: String(m.id),
            name: m.name,
            name_mr: MARKET_MR_NAMES[m.name] || m.name,
          }));
          setMarkets(list);
        }
      })
      .catch(() => {
        // Keep defaults on network error
      });
  }, []);

  return (
    <CommodityContext.Provider
      value={{
        commodities,
        markets,
        districts,
        selectedCommodity,
        selectedMarket,
        selectedDistrict,
        setCommodity: setSelectedCommodity,
        setMarket: setSelectedMarket,
        setDistrict: setSelectedDistrict,
      }}>
      {children}
    </CommodityContext.Provider>
  );
}

const defaultCommodityContext: CommodityContextValue = {
  commodities: INITIAL_COMMODITIES,
  markets: INITIAL_MARKETS,
  districts: INITIAL_DISTRICTS,
  selectedCommodity: INITIAL_COMMODITIES[0]!,
  selectedMarket: INITIAL_MARKETS[0]!,
  selectedDistrict: INITIAL_DISTRICTS[0]!,
  setCommodity: () => {},
  setMarket: () => {},
  setDistrict: () => {},
};

export function useCommodity() {
  const ctx = useContext(CommodityContext);
  return ctx || defaultCommodityContext;
}


export const COMMODITY_IMAGES: Record<string, string> = {
  Onion: '/images/onion.jpg',
  Soyabean: '/images/soybean.jpg',
  Soybean: '/images/soybean.jpg',
  Cotton: '/images/cotton.jpg',
  Wheat: '/images/wheat.jpg',
  Tomato: '/images/tomato.jpg',
  'Bengal Gram': '/images/chana.jpg',
  Maize: '/images/maize.jpg',
  'Green Chilli': '/images/chilli.jpg',
  Turmeric: '/images/turmeric.jpg',
  Pomegranate: '/images/pomegranate.jpg',
  Groundnut: '/images/groundnut.jpg',
  Grapes: '/images/grapes.jpg',
  Sugarcane: '/images/sugarcane.jpg',
  Potato: '/images/potato.jpg',
  Banana: '/images/turmeric.jpg',
  Ginger: '/images/turmeric.jpg',
  Garlic: '/images/onion.jpg',
  Jowar: '/images/wheat.jpg',
  Rice: '/images/wheat.jpg',
};

export function getCommodityImage(name: string): string {
  return COMMODITY_IMAGES[name] || '/images/onion.jpg';
}
