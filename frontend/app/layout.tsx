import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "InterviewSense",
  description: "Communication analytics using facial landmark geometry and behavioral vision.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="app-wrapper fade-in">
          <nav style={{ padding: '24px 48px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontWeight: 700, fontSize: '1.5rem', letterSpacing: '-0.5px' }}>
              <span style={{ color: 'var(--text-primary)' }}>Interview</span>
              <span style={{ color: 'var(--accent-primary)' }}>Sense</span>
            </div>
          </nav>
          <main style={{ padding: '0 48px 48px 48px', maxWidth: '1440px', margin: '0 auto' }}>
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
