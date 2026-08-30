import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AppStateProvider } from "@/lib/app-state";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "NYC Dining Concierge",
  description: "AI concierge for your saved NYC restaurants and bars",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <TooltipProvider>
          <AppStateProvider>{children}</AppStateProvider>
        </TooltipProvider>
      </body>
    </html>
  );
}
