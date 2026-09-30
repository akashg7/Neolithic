/**
 * staticMarketStore.ts — Centralized 100% Offline Static Market State.
 *
 * Synchronizes selected crop, district, and mandi across Home and Market screens
 * with zero backend dependency and instantaneous reactivity.
 */

import { useState, useEffect } from 'react';
import { STATIC_CROPS, STATIC_DISTRICTS, STATIC_MANDIS, StaticCrop } from './staticMarketData';

interface MarketState {
  selectedCrop: StaticCrop;
  selectedDistrict: string;
  selectedMandi: string;
  timeframe: 7 | 14 | 30;
  activeFilter: 'all' | 'nearby' | 'highest';
}

const STORAGE_KEY = 'krishi_mitra_static_selection_v2';

function loadInitialState(): MarketState {
  const defaultCrop = STATIC_CROPS[0]; // Onion (कांदा)
  const defaultDistrict = 'नाशिक';
  const defaultMandi = 'लासलगाव मुख्य बाजार समिती';

  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        const matchedCrop = STATIC_CROPS.find(c => c.id === parsed.cropId) || defaultCrop;
        return {
          selectedCrop: matchedCrop,
          selectedDistrict: parsed.district || defaultDistrict,
          selectedMandi: parsed.mandi || defaultMandi,
          timeframe: parsed.timeframe || 7,
          activeFilter: parsed.activeFilter || 'all',
        };
      }
    } catch (e) {
      // fallback to defaults
    }
  }

  return {
    selectedCrop: defaultCrop,
    selectedDistrict: defaultDistrict,
    selectedMandi: defaultMandi,
    timeframe: 7,
    activeFilter: 'all',
  };
}

let currentState: MarketState = loadInitialState();
const listeners = new Set<(state: MarketState) => void>();

function persist(state: MarketState) {
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          cropId: state.selectedCrop.id,
          district: state.selectedDistrict,
          mandi: state.selectedMandi,
          timeframe: state.timeframe,
          activeFilter: state.activeFilter,
        })
      );
    } catch (e) {}
  }
}

function notify() {
  persist(currentState);
  listeners.forEach(fn => fn(currentState));
}

export const staticMarketStore = {
  getState(): MarketState {
    return currentState;
  },

  setSelectedCrop(crop: StaticCrop) {
    currentState = { ...currentState, selectedCrop: crop };
    notify();
  },

  setSelectedDistrict(district: string) {
    // Find default mandi for this district if available
    const distObj = STATIC_DISTRICTS.find(d => d.name_mr === district || d.name === district);
    const newMandi = distObj ? distObj.defaultMandi : currentState.selectedMandi;
    currentState = {
      ...currentState,
      selectedDistrict: district,
      selectedMandi: newMandi,
    };
    notify();
  },

  setSelectedMandi(mandi: string) {
    currentState = { ...currentState, selectedMandi: mandi };
    notify();
  },

  setTimeframe(timeframe: 7 | 14 | 30) {
    currentState = { ...currentState, timeframe };
    notify();
  },

  setActiveFilter(activeFilter: 'all' | 'nearby' | 'highest') {
    currentState = { ...currentState, activeFilter };
    notify();
  },

  subscribe(listener: (state: MarketState) => void) {
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  },
};

export function useStaticMarket() {
  const [state, setState] = useState<MarketState>(staticMarketStore.getState());

  useEffect(() => {
    return staticMarketStore.subscribe(setState);
  }, []);

  return {
    ...state,
    setSelectedCrop: staticMarketStore.setSelectedCrop,
    setSelectedDistrict: staticMarketStore.setSelectedDistrict,
    setSelectedMandi: staticMarketStore.setSelectedMandi,
    setTimeframe: staticMarketStore.setTimeframe,
    setActiveFilter: staticMarketStore.setActiveFilter,
  };
}
