import './globals.css'
import { Globe } from 'lucide-react'

export const metadata = {
  title: 'Ma\u00e7 Analiz - G\u00fcn\u00fcn Futbol Ma\u00e7lar\u0131',
  description: 'Futbol ma\u00e7 analiz platformu - g\u00fcncel ma\u00e7lar ve canl\u0131 skorlar',
}

export default function RootLayout({ children }) {
  return (
    <html lang="tr">
      <body className="bg-surface-base text-white antialiased min-h-screen">
        <Header />
        <main className="pt-16">
          {children}
        </main>
        <footer className="px-4 py-6 text-center text-sm text-zinc-400">
          <a href="https://www.football-data.org/" rel="noreferrer" className="underline">
            Football data provided by the Football-Data.org API
          </a>
        </footer>
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
            <Globe size={18} color="white" strokeWidth={2.5} aria-hidden="true" />
          </div>
          <span className="text-lg font-bold tracking-tight font-outfit text-white group-hover:text-emerald-400 transition-colors">
            Ma&#231; Analiz
          </span>
        </a>
      </div>
    </header>
  )
}
