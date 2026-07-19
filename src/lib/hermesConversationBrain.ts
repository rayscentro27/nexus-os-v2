export type ConversationIntent = 'preference' | 'favorite_food' | 'favorite_sport' | 'joke' | 'wellbeing' | 'opinion' | 'simple_explanation' | 'identity' | 'casual_followup';

export function classifyConversationIntent(message: string): ConversationIntent | null {
  const text = message.toLowerCase();
  if (/favorite food/.test(text)) return 'favorite_food';
  if (/favorite sport/.test(text)) return 'favorite_sport';
  if (/\b(favou?rite|would you choose|do you prefer)\b/.test(text)) return 'preference';
  if (/tell me a joke|make me laugh/.test(text)) return 'joke';
  if (/how are you|how'?s it going/.test(text)) return 'wellbeing';
  if (/what do you think|your opinion/.test(text)) return 'opinion';
  if (/explain (this|it) simply|simple terms/.test(text)) return 'simple_explanation';
  if (/are you real|who are you|what are you|your name|call you/.test(text)) return 'identity';
  if (/^(why|really|how so|tell me more|what about that)[?.! ]*$/.test(text.trim())) return 'casual_followup';
  return null;
}

export function answerConversation(message: string, intent = classifyConversationIntent(message)): string | null {
  switch (intent) {
    case 'preference': return "I can make a reasoned choice if you give me the criteria that matter.";
    case 'favorite_food': return "I don't eat, but if I'm answering in Nexus mode, I'd pick tacos: flexible, fast, modular, and easy to scale. That's how Nexus should work too — simple on the surface, powerful underneath.";
    case 'favorite_sport': return "I don't play sports, but basketball fits how I think: read the floor, move the ball, protect against turnovers, and take the highest-quality shot. That's a useful operating model for Nexus too.";
    case 'joke': return 'Why did the automation bring a receipt? Because in Nexus, even the punchline needs an audit trail.';
    case 'wellbeing': return "I'm ready and tracking the work. What do you want to focus on?";
    case 'opinion': return 'I can give you a direct recommendation, but I need the decision or topic you want judged. What should I evaluate?';
    case 'simple_explanation': return 'I can simplify it. Point me to the specific report, page item, or idea, and I’ll explain what it means, why it matters, and the next safe step.';
    case 'identity': return "I'm Hermes, Ray's private Nexus advisor. I answer from the current message, eligible memory, and governed Nexus evidence.";
    case 'casual_followup': return 'I can follow that. Which prior recommendation or page item do you mean?';
    default: return null;
  }
}
