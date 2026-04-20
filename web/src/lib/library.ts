import { LibraryEntry } from "./types";

export const LIBRARY: Record<string, LibraryEntry> = {
  "Warm Welcome": {
    name: "Warm Welcome",
    input:
      "Hey there! Welcome to agent FM, your AI agent's voice. I can speak in over fifty different voices across nine languages. Pick a voice, type something, and hit play to hear it come to life.",
    prompt: "A warm, friendly introduction to the agent-fm voice system.",
    voice: "af_heart",
  },
  "Task Complete": {
    name: "Task Complete",
    input:
      "Hey, just finished the refactoring. All twenty-three tests are passing, and I cleaned up the circular dependency in the payments module. Want me to walk you through the changes?",
    prompt: "How an AI agent might report completing a coding task.",
    voice: "am_adam",
  },
  "Design Decision": {
    name: "Design Decision",
    input:
      "Quick question — I'm at a fork in the implementation. We can either use a factory pattern for the parsers, which is more extensible, or keep it simple with a switch statement. The factory adds about forty lines but makes adding new formats trivial. What do you think?",
    prompt: "An AI agent asking the developer for a design decision.",
    voice: "bf_emma",
  },
  "Bug Found": {
    name: "Bug Found",
    input:
      "Heads up, I found something concerning. There's a SQL injection vulnerability in the login endpoint — the username field isn't sanitized before the query. I've patched it, but you should review the fix before I commit.",
    prompt: "An AI agent reporting a security issue it discovered.",
    voice: "am_onyx",
  },
  Dramatic: {
    name: "Dramatic",
    input:
      "The night was thick with fog, wrapping the town in mist. Detective Evelyn Harper pulled her coat tighter, feeling the chill creep down her spine. She knew the town's buried secrets were rising again. Footsteps echoed behind her, slow and deliberate.",
    prompt: "Atmospheric noir storytelling.",
    voice: "bm_george",
  },
  "Bedtime Story": {
    name: "Bedtime Story",
    input:
      "Once upon a time, in a forest painted with moonlight, there lived a tiny fox named Ember. Every night, Ember would chase fireflies through the silver meadow, leaping and twirling until the stars themselves seemed to dance along.",
    prompt: "A gentle children's bedtime story.",
    voice: "bf_alice",
  },
  "News Anchor": {
    name: "News Anchor",
    input:
      "Good evening. In our top story tonight, researchers at the university have made a breakthrough in quantum computing, achieving stable qubit operation at room temperature for the first time. The team says this could revolutionize everything from drug discovery to climate modeling.",
    prompt: "Professional news broadcast delivery.",
    voice: "am_michael",
  },
  "Fitness Coach": {
    name: "Fitness Coach",
    input:
      "Alright team, let's bring the energy! We're starting with dynamic stretches, then rolling into squats, lunges, and high knees. Keep that core tight, breathe through it, and push! Last ten seconds, give me everything you've got! And done! You crushed it!",
    prompt: "High-energy workout motivation.",
    voice: "af_nova",
  },
  Poetry: {
    name: "Poetry",
    input:
      "Do not go gentle into that good night. Old age should burn and rave at close of day. Rage, rage against the dying of the light. Though wise men at their end know dark is right, because their words had forked no lightning they do not go gentle into that good night.",
    prompt: "Dylan Thomas — classic poetry recitation.",
    voice: "bm_fable",
  },
  Meditation: {
    name: "Meditation",
    input:
      "Welcome to your moment of stillness. Close your eyes and take a deep, slow breath in. Hold it gently. Now release, letting go of everything that doesn't serve you. Feel your body soften. Your mind quiets. You are exactly where you need to be.",
    prompt: "Calm guided meditation.",
    voice: "af_sarah",
  },
  "Code Review": {
    name: "Code Review",
    input:
      "I've reviewed the pull request. Overall it looks solid — clean separation of concerns and good test coverage. Two things: the retry logic in the API client should have exponential backoff instead of fixed delays, and there's a potential race condition in the cache invalidation. I've left inline comments.",
    prompt: "An AI agent delivering a code review summary.",
    voice: "am_adam",
  },
  Pirate: {
    name: "Pirate",
    input:
      "Ahoy, ye scallywags! Captain Blackbeard here, and I've got news that'll shiver yer timbers! We've found the treasure map, hidden in the old lighthouse! Set sail at dawn, me hearties, for the Isle of Golden Doubloons awaits!",
    prompt: "Theatrical pirate character.",
    voice: "am_fenrir",
  },
  "Hindi Greeting": {
    name: "Hindi Greeting",
    input:
      "Namaste! Aaj hum baat karenge artificial intelligence ke baare mein. Yeh technology hamare jeevan ko kai tareekon se badal rahi hai. Shiksha se lekar swasthya tak, AI har jagah apna prabhav dikha raha hai.",
    prompt: "A greeting and introduction in Hindi.",
    voice: "hf_alpha",
  },
  "Japanese Story": {
    name: "Japanese Story",
    input:
      "\u6614\u3005\u3001\u3042\u308B\u5C71\u306E\u5965\u6DF1\u304F\u306B\u3001\u5C0F\u3055\u306A\u6751\u304C\u3042\u308A\u307E\u3057\u305F\u3002\u305D\u306E\u6751\u306B\u306F\u3001\u4E0D\u601D\u8B70\u306A\u529B\u3092\u6301\u3064\u8001\u4EBA\u304C\u4F4F\u3093\u3067\u3044\u307E\u3057\u305F\u3002\u6751\u4EBA\u305F\u3061\u306F\u5F7C\u3092\u300C\u5C71\u306E\u8CE2\u8005\u300D\u3068\u547C\u3093\u3067\u3044\u307E\u3057\u305F\u3002",
    prompt: "A traditional Japanese folktale opening.",
    voice: "jf_alpha",
  },
  "Cooking Show": {
    name: "Cooking Show",
    input:
      "Now, here's where the magic happens. We're going to deglaze this pan with a splash of white wine — listen to that sizzle! Scrape up all those beautiful caramelized bits from the bottom. That's pure flavor right there. A knob of butter, a squeeze of lemon, and we have ourselves a restaurant-quality sauce.",
    prompt: "Enthusiastic cooking demonstration.",
    voice: "af_bella",
  },
};

export const getLibraryByPrompt = (
  maybePrompt: string
): LibraryEntry | null => {
  const found = Object.keys(LIBRARY).find(
    (key) => LIBRARY[key].prompt === maybePrompt
  );
  return found ? LIBRARY[found] : null;
};

export function getRandomLibrarySet(count = 5): LibraryEntry[] {
  const availableLibrary = Object.values(LIBRARY);
  return availableLibrary.sort(() => Math.random() - 0.5).slice(0, count);
}

export const DEFAULT_LIBRARY = LIBRARY["Warm Welcome"];

export const VOICES = [
  "af_heart",
  "af_bella",
  "af_nova",
  "af_sky",
  "af_sarah",
  "am_adam",
  "am_michael",
  "am_onyx",
  "am_fenrir",
  "bf_emma",
  "bf_alice",
  "bm_george",
  "bm_fable",
  "hf_alpha",
  "hm_psi",
  "jf_alpha",
];

export const DEFAULT_VOICE = "af_heart";

export const getRandomVoice = (currentVoice: string): string => {
  const availableVoices = VOICES.filter((voice) => voice !== currentVoice);
  return availableVoices[Math.floor(Math.random() * availableVoices.length)];
};
