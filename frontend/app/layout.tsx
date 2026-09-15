import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TransformAI — Multi-Deliverable Canonical Knowledge Transformation Engine",
  description: "Transform complex raw intelligence, documents, text, and URLs into canonical knowledge and multi-format executive deliverables with LangGraph state orchestration.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark h-full antialiased">
      <body className="min-h-full flex flex-col bg-[#D8D0C5] text-[#3F0D0C]">
        {children}
      </body>
    </html>
  );
}
