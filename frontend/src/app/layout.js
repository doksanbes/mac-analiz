import './globals.css'

export const metadata = {
  title: 'Ma\u00e7 Analiz - G\u00fcn\u00fcn Futbol Ma\u00e7lar\u0131',
  description: 'Futbol ma\u00e7 analiz platformu - g\u00fcncel ma\u00e7lar ve canl\u0131 skorlar',
}

export default function RootLayout({ children }) {
  return (
    <html lang="tr">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800;900&family=Manrope:wght@400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-surface-base text-white antialiased min-h-screen">
        <Header />
        <main className="pt-16">
          {children}
        </main>
      </body>
    </html>
  )
}

function Header() {
  return (
    <header
      data-testid="app-header"
      className="fixed top-0 w-full z-50 bg-black/60 backdrop-blur-xl border-b border-white/10"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center">
        <a href="/" data-testid="logo-link" className="flex items-center gap-3 group">
          <div className="w-9 h-9 rounded-xl bg-emerald-500 flex items-center justify-center transition-colors group-hover:bg-emerald-400">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
              <path d="M2 12h20" />
            </svg>
          </div>
          <span className="text-lg font-bold tracking-tight font-outfit text-white group-hover:text-emerald-400 transition-colors">
            Ma&#231; Analiz
          </span>
        </a>
      </div>
    </header>
  )
}
