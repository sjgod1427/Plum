import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "Plum Claims",
  description: "OPD Insurance Claim Adjudication",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Navbar />
        <main className="pt-14 min-h-screen">
          <div className="max-w-6xl mx-auto px-6 py-8">{children}</div>
        </main>
      </body>
    </html>
  );
}
