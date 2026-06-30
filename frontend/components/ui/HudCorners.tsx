export default function HudCorners({ color = "var(--color-accent)", opacity = 0.5 }: { color?: string; opacity?: number }) {
    const base = "absolute w-3 h-3 pointer-events-none"
    return (
        <>
            <span className={`${base} top-0 left-0 border-t-2 border-l-2 rounded-tl-sm`} style={{ borderColor: color, opacity }} />
            <span className={`${base} top-0 right-0 border-t-2 border-r-2 rounded-tr-sm`} style={{ borderColor: color, opacity }} />
            <span className={`${base} bottom-0 left-0 border-b-2 border-l-2 rounded-bl-sm`} style={{ borderColor: color, opacity }} />
            <span className={`${base} bottom-0 right-0 border-b-2 border-r-2 rounded-br-sm`} style={{ borderColor: color, opacity }} />
        </>
    )
}
