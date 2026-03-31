import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Script from "next/script";

import { ControlSurfaceProvider } from "@/components/control-surface-provider";
import { ThemeHydration } from "@/components/theme-hydration";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Aurnom",
  description: "Frontend for the Evennia-powered Aurnom world",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full min-h-svh antialiased`}
      suppressHydrationWarning
    >
      <body className="min-h-svh">
        <Script id="aurnom-theme-init" strategy="beforeInteractive">
          {`(function(){try{var s=localStorage.getItem('theme');var d=window.matchMedia('(prefers-color-scheme: dark)').matches;var dark=s==='dark'||(s!=='light'&&d);document.documentElement.classList.toggle('dark',dark);}catch(e){}})();`}
        </Script>
        <ThemeHydration />
        <ControlSurfaceProvider>{children}</ControlSurfaceProvider>
      </body>
    </html>
  );
}
