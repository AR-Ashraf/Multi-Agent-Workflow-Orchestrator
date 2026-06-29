import type { Metadata } from "next";
import { Fraunces, Inter, JetBrains_Mono } from "next/font/google";
import { Analytics, GtmNoScript } from "@/components/Analytics";
import "./globals.css";

// Self-hosted at build time by next/font — no runtime CDN (CLAUDE.md §1).
const fraunces = Fraunces({ variable: "--font-fraunces", subsets: ["latin"], weight: ["400", "500", "600", "700"] });
const inter = Inter({ variable: "--font-inter", subsets: ["latin"], weight: ["400", "500", "600", "700"] });
const jetbrains = JetBrains_Mono({ variable: "--font-jetbrains", subsets: ["latin"], weight: ["400", "500", "600"] });

const SITE = "https://agents.devs-core.com";

export const metadata: Metadata = {
  metadataBase: new URL(SITE),
  title: "Cadenza — AI agents, working in concert · by Devs Core",
  description:
    "Watch a team of AI agents research, debate, and fact-check a market-research brief live in your browser. A Devs Core showcase of custom-coded, production-grade agentic systems — owned by you, shipped in weeks not quarters.",
  keywords: [
    "custom AI agent development",
    "AI agent development cost",
    "custom-coded AI agents",
    "AI workflow automation",
    "multi-agent systems",
    "LangGraph",
    "agentic AI",
  ],
  alternates: { canonical: SITE },
  openGraph: {
    type: "website",
    url: SITE,
    title: "Cadenza — AI agents, working in concert",
    description:
      "A live, in-browser showcase of production-grade multi-agent systems by Devs Core. Bring your own model & key.",
    siteName: "Cadenza by Devs Core",
  },
  twitter: {
    card: "summary_large_image",
    title: "Cadenza — AI agents, working in concert",
    description: "Watch real AI agents research, debate, and fact-check — live in your browser.",
  },
};

const JSON_LD = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      name: "Devs Core",
      url: "https://devs-core.com",
      description:
        "Custom-coded AI agents & workflow automation for US businesses. We build it, you own it.",
      areaServed: "US",
    },
    {
      "@type": "SoftwareApplication",
      name: "Cadenza",
      applicationCategory: "BusinessApplication",
      operatingSystem: "Web",
      url: SITE,
      description:
        "An interactive showcase that runs a real multi-agent AI Market Research Brief workflow live in the browser.",
      offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
      publisher: { "@type": "Organization", name: "Devs Core", url: "https://devs-core.com" },
    },
  ],
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${fraunces.variable} ${inter.variable} ${jetbrains.variable}`}>
      <body>
        <GtmNoScript />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD) }}
        />
        {children}
        <Analytics />
      </body>
    </html>
  );
}
