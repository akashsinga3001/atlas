import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import "./globals.css"
import QueryProvider from "@/components/providers/QueryProvider"
import ThemeProvider from "@/components/providers/ThemeProvider"
import Sidebar from "@/components/layout/Sidebar"
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
        <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full`} suppressHydrationWarning>
            <body className="min-h-full bg-bg">
                <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
                    <QueryProvider>
                        <div className="flex min-h-full">
                            <Sidebar />
                            <div className="flex-1 flex flex-col min-w-0">
                                <TopNav />
                                <main className="max-w-360 mx-auto w-full px-8 py-8">{children}</main>
                            </div>
                        </div>
                    </QueryProvider>
                </ThemeProvider>
            </body>
        </html>
    )
}
