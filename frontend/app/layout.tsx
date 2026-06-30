import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import "./globals.css"
import QueryProvider from "@/components/providers/QueryProvider"
import TopNav from "@/components/layout/TopNav"

const geistSans = Geist({
    variable: "--font-body",
    subsets: ["latin"]
})

const geistMono = Geist_Mono({
    variable: "--font-mono",
    subsets: ["latin"]
})

export const metadata: Metadata = {
    title: "Atlas",
    description: "Trading dashboard"
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full`}>
            <body className="min-h-full bg-bg">
                <div className="hud-grid-bg" />
                <TopNav />
                <div className="max-w-360 mx-auto px-8 py-8">
                    <QueryProvider>{children}</QueryProvider>
                </div>
            </body>
        </html>
    )
}
