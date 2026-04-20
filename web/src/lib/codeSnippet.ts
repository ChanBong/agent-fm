export const getCodeSnippet = (
  language: string,
  { input, voice }: { input: string; prompt: string; voice: string }
): string => {
  switch (language) {
    case "py":
      return `import requests

text = ${JSON.stringify(input)}

response = requests.post(
    "http://localhost:3001/api/generate",
    json={
        "text": text,
        "voice": "${voice}",
        "speed": 1.0,
    },
)

with open("output.wav", "wb") as f:
    f.write(response.content)

print("Saved to output.wav")`;
    case "js":
      return `const text = ${JSON.stringify(input)};

const response = await fetch('http://localhost:3001/api/generate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    text,
    voice: '${voice}',
    speed: 1.0,
  }),
});

const blob = await response.blob();
// Save or play the audio blob
`;
    case "curl":
      return `curl -X POST http://localhost:3001/api/generate \\
  -H "Content-Type: application/json" \\
  -d '{
    "text": ${JSON.stringify(input)},
    "voice": "${voice}",
    "speed": 1.0
  }' \\
  --output output.wav`;
    default:
      return "";
  }
};
