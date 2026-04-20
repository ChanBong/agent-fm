import type { Metadata } from "next";
import { JetBrains_Mono } from "next/font/google";
import clsx from "clsx";
import "./globals.css";

const jetBrainsMono = JetBrains_Mono({
  weight: "400",
  subsets: [],
  preload: true,
});

export const metadata: Metadata = {
  title: "agent-fm",
  description: "Give your AI agent a voice. Powered by Kokoro TTS with 50+ voices across 9 languages.",
  openGraph: {
    title: "agent-fm",
    description: "Give your AI agent a voice. Powered by Kokoro TTS with 50+ voices across 9 languages.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={clsx("antialiased", jetBrainsMono.className)} suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
