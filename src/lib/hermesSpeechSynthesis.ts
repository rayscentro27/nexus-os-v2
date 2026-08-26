/** Browser-native, bounded Hermes response speech. No audio is uploaded. */
export type SpeechResult = 'STARTED' | 'UNSUPPORTED' | 'EMPTY' | 'FAILED';

export function speakHermesResponse(text: string): SpeechResult {
  const clean = String(text || '').replace(/[*_`#>]/g, '').replace(/\s+/g, ' ').trim().slice(0, 4000);
  if (!clean) return 'EMPTY';
  if (typeof window === 'undefined' || !window.speechSynthesis || typeof window.SpeechSynthesisUtterance !== 'function') return 'UNSUPPORTED';
  try {
    window.speechSynthesis.cancel();
    const utterance = new window.SpeechSynthesisUtterance(clean);
    utterance.lang = 'en-US';
    utterance.rate = 1;
    utterance.pitch = 1;
    window.speechSynthesis.speak(utterance);
    return 'STARTED';
  } catch {
    return 'FAILED';
  }
}

export function stopHermesSpeech(): void {
  try { window.speechSynthesis?.cancel(); } catch { /* browser shutdown */ }
}
