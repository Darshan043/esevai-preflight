import type { Metadata } from "next";
import { Noto_Sans, Noto_Sans_Tamil } from "next/font/google";
import { Suspense } from "react";
import "./globals.css";

import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";

const noto = Noto_Sans({
  subsets: ["latin"],
  variable: "--font-noto",
  display: "swap",
});

const notoTamil = Noto_Sans_Tamil({
  subsets: ["tamil"],
  variable: "--font-tamil",
  display: "swap",
});

export const metadata: Metadata = {
  title: "e-Sevai Pre-Flight",
  description: "AI-powered government document readiness assistant",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${noto.variable} ${notoTamil.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <Suspense fallback={null}>
          <SiteHeader />
        </Suspense>
        <div id="content" className="flex-1">{children}</div>
        <SiteFooter />
      </body>
    </html>
  );
}
