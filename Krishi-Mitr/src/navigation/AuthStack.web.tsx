/**
 * Web-only signed-out stack: wraps the AuthStack navigator with `AgentProvider`,
 * `FloatingAssistant`, and `ChatDrawer` so onboarding screens (e.g. S3_Profile)
 * can reach the `extract_onboarding_profile` assistant tool on Web without
 * altering the native mobile `AuthStack.tsx`.
 */

import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import Landing from '../screens/web/Landing';
import BuyerSplash from '../screens/buyer/BuyerSplash';
import { useAuth } from '../lib/auth';
import { demoLogin } from '../lib/api';
import { AgentProvider } from '../lib/agentContext';
import { FloatingAssistant } from '../components/chat/FloatingAssistant';
import { ChatDrawer } from '../components/chat/ChatDrawer';
import S00_Splash from '../screens/farmer/S00_Splash';
import S01_Language from '../screens/farmer/S01_Language';
import S01b_ValueCarousel from '../screens/farmer/S01b_ValueCarousel';
import S02_Phone from '../screens/farmer/S02_Phone';
import S03_OTP from '../screens/farmer/S03_OTP';
import S03_Profile from '../screens/farmer/S03_Profile';
import S03_Welcome from '../screens/farmer/S03_Welcome';
import type { AuthStackParamList } from './AuthStack';

export type { AuthStackParamList };

const Stack = createNativeStackNavigator<AuthStackParamList>();

function BuyerSplashRoute() {
  const { signIn } = useAuth();
  return <BuyerSplash onSignIn={() => void demoLogin('BUYER').then(signIn).catch(() => undefined)} />;
}

export function AuthStack() {
  return (
    <AgentProvider>
      <Stack.Navigator
        initialRouteName="Web_Landing"
        screenOptions={{ headerShown: false, animation: 'slide_from_right' }}>
        <Stack.Screen name="Web_Landing" component={Landing} />
        <Stack.Screen name="Buyer_Splash" component={BuyerSplashRoute} />
        <Stack.Screen name="S0_Splash" component={S00_Splash} />
        <Stack.Screen name="S1_Language" component={S01_Language} />
        <Stack.Screen name="S1b_ValueCarousel" component={S01b_ValueCarousel} />
        <Stack.Screen name="S2_Phone" component={S02_Phone} />
        <Stack.Screen name="S3_OTP" component={S03_OTP} />
        <Stack.Screen name="S3_Profile" component={S03_Profile} />
        <Stack.Screen name="S3_Welcome" component={S03_Welcome} />
      </Stack.Navigator>
      <FloatingAssistant />
      <ChatDrawer />
    </AgentProvider>
  );
}
