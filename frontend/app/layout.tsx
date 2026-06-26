import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import "./globals.css"
import QueryProvider from "@/components/providers/QueryProvider"
import Sidebar from "@/components/layout/Sidebar"

const geistSans = Geist({
    variable: "--font-geist-sans",
    subsets: ["latin"]
})

const geistMono = Geist_Mono({
    variable: "--font-geist-mono",
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
                <Sidebar />
                <main className="ml-56 min-h-screen p-8">
                    <QueryProvider>{children}</QueryProvider>
                </main>
            </body>
        </html>
    )
}
