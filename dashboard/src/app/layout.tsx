import type { Metadata } from "next";
import localFont from "next/font/local";
import Link from "next/link";
import "./globals.css";

const geistSans = localFont({ src: "../fonts/GeistVF.woff2", variable: "--font-geist-sans" });
const geistMono = localFont({ src: "../fonts/GeistMonoVF.woff2", variable: "--font-geist-mono" });

export const metadata: Metadata = {
  title: "D2C Global Market Intelligence",
  description: "LG Electronics D2C Weekly Intelligence Dashboard",
};

const NAV_ITEMS = [
  { href: "/", label: "Dashboard" },
  { href: "/reports", label: "Reports" },
  { href: "/regions", label: "Regions" },
  { href: "/explore", label: "Explore" },
  { href: "/search", label: "Search" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <header className="sticky top-0 z-50 border-b border-[var(--card-border)] bg-[var(--card)]/80 backdrop-blur-sm">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="flex h-14 items-center justify-between">
              <Link href="/" className="flex items-center gap-2 font-bold text-lg">
                <span className="text-[var(--accent)]">D2C</span>
                <span>Global Intelligence</span>
              </Link>
              <nav className="flex items-center gap-1">
                {NAV_ITEMS.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="rounded-md px-3 py-1.5 text-sm font-medium text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--background)] transition-colors"
                  >
                    {item.label}
                  </Link>
                ))}
              </nav>
            </div>
          </div>
        </header>
        <main className="flex-1">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6">{children}</div>
        </main>
        <footer className="border-t border-[var(--card-border)] py-4 text-center text-xs text-[var(--muted)]">
          D2C Global Market Intelligence - LG Electronics - Confidential
        </footer>
      </body>
    </html>
  );
}
