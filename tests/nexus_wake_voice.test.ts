import { describe, expect, it } from 'vitest';
import fs from 'node:fs';
import { isNewThreadCommand, routeWakePhrase, stripWakePhrase } from '../src/lib/nexusAgentDispatch';

const source = fs.readFileSync('src/admin/NexusWakeVoice.jsx', 'utf8');

describe('Nexus wake-routed Voice', () => {
  it('routes wake phrases independently of the visible agent selector', () => {
    expect(routeWakePhrase('Hey Nexus, what needs my attention?')).toBe('hermes');
    expect(routeWakePhrase('Hey Hermes. What happened?')).toBe('hermes');
    expect(routeWakePhrase('Hey Nova, challenge this plan.')).toBe('nova');
    expect(routeWakePhrase('Hey Alpha can you research this?')).toBe('alpha');
    expect(stripWakePhrase('Hey Nova, challenge this plan.')).toBe('challenge this plan.');
  });

  it('supports explicit new-chat voice commands', () => {
    expect(isNewThreadCommand('Hey Nova, start a new chat.')).toBe(true);
    expect(isNewThreadCommand('Hey Alpha, new conversation about lending.')).toBe(true);
    expect(isNewThreadCommand('Hey Nexus, what should I do?')).toBe(false);
  });

  it('uses private bounded capture, local VAD, automatic dispatch, and one owner', () => {
    expect(source).toContain('nexus-voice-listener-owner');
    expect(source).toContain('getUserMedia');
    expect(source).toContain('AudioContext');
    expect(source).toContain('SILENCE_MS = 1100');
    expect(source).toContain('sendAgentMessage');
    expect(source).toContain('nexus:voice-thread-update');
    expect(source).toContain('Quick Voice');
    expect(source).not.toMatch(/SpeechRecognition|webkitSpeechRecognition|google|deepgram|assemblyai/i);
  });
});
