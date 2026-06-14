import { Analytics } from '@vercel/analytics/next'
import type { Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import './globals.css'
import '@/components/taxonomy/motion.css'
import { AppSidebar } from '@/components/app-sidebar'
import { MobileNav } from '@/components/mobile-nav'

const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] })
const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
})

export const metadata: Metadata = {
  title: 'EukaryoBase — Eukaryote Genomics & Biodiversity Atlas',
  description:
    'Explore genomics metadata across Eukaryotes: geographic distribution, IUCN conservation status, and assembly metrics aggregated by taxon.',
  generator: 'v0.app',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className={`dark ${geistSans.variable} ${geistMono.variable} bg-background`}>
      <body className="font-sans antialiased">
        <div className="flex min-h-screen">
          <AppSidebar />
          <div className="flex min-w-0 flex-1 flex-col">
            <MobileNav />
            <main className="flex min-w-0 flex-1 flex-col overflow-x-hidden">{children}</main>
          </div>
        </div>
      </body>
    </html>
  )
}
