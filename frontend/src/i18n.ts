export type Lang = 'ta' | 'en';
// Tamil strings are a first draft: have a native speaker review them before field use.
const T = {
  recordToday: { ta: 'இன்றைய விற்பனையைப் பதிவு செய்க', en: 'Record today\'s sales' },
  stop: { ta: 'நிறுத்து', en: 'Stop' },
  speakNow: { ta: 'உங்கள் விற்பனைத் தொகையைச் சொல்லுங்கள்…', en: 'Say your sales amount…' },
  orTap: { ta: 'அல்லது தொகையைத் தொடவும்', en: 'Or tap the amount' },
  total: { ta: 'மொத்தம்', en: 'Total' },
  save: { ta: 'சேமி', en: 'Save' },
  clear: { ta: 'அழி', en: 'Clear' },
  saved: { ta: 'சேமிக்கப்பட்டது. இணையம் வந்ததும் அனுப்பப்படும்.', en: 'Saved on this phone. It will be sent when you are online.' },
  local: { ta: 'அனுப்ப நிலுவையில்', en: 'Waiting to send' },
  pendingTx: { ta: 'குரல் பதிவு சரிபார்க்கப்படுகிறது', en: 'Voice note being transcribed' },
  review: { ta: 'அதிகாரி சரிபார்க்க வேண்டும்', en: 'Officer to confirm' },
  done: { ta: 'பதிவாகிவிட்டது', en: 'Recorded' },
  failed: { ta: 'மீண்டும் முயல்கிறது', en: 'Will retry' },
  recent: { ta: 'சமீபத்திய பதிவுகள்', en: 'Recent entries' },
  noMic: { ta: 'இந்த உலாவியில் ஒலிப்பதிவு இல்லை. தொகையைத் தொடவும்.', en: 'Recording is not available here. Tap the amount instead.' },
  micDenied: { ta: 'மைக்ரோஃபோன் அனுமதி இல்லை. தொகையைத் தொடவும்.', en: 'Microphone blocked. Tap the amount instead.' },
  consentTitle: { ta: 'தரவு பகிர்வு ஒப்புதல்', en: 'Data-sharing consent' },
  consentText: { ta: 'எனது மின்சாதன இயக்கத் தரவையும் விற்பனைப் பதிவுகளையும் கடன் மதிப்பீட்டிற்காக WattCredit மற்றும் கடன் வழங்குநருடன் பகிர ஒப்புக்கொள்கிறேன். இந்த ஒப்புதலை எப்போது வேண்டுமானாலும் திரும்பப் பெறலாம். தரவு இந்தியாவில் மட்டுமே சேமிக்கப்படும்.',
    en: 'I agree to share my machine-usage data and sales records with WattCredit and the lender for credit assessment. I can withdraw this consent at any time. My data is stored in India only.' },
  consentName: { ta: 'உங்கள் பெயரை எழுதி கையொப்பமிடுங்கள்', en: 'Type your full name as signature' },
  consentAgree: { ta: 'நான் ஒப்புக்கொள்கிறேன்', en: 'I agree' },
} as const;
export type Key = keyof typeof T;
export const t = (k: Key, l: Lang): string => T[k][l];
