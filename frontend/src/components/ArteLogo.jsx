export default function ArteLogo({ size = 'md' }) {
  const sizes = {
    sm: { w: 80, h: 40 },
    md: { w: 120, h: 56 },
    lg: { w: 160, h: 72 },
  }
  const s = sizes[size]

  return (
    <svg viewBox="0 0 120 56" width={s.w} height={s.h} className="block">
      {/* "DRINK" small text */}
      <text
        x="78" y="16"
        fontFamily="'DM Sans', sans-serif"
        fontSize="10"
        fontWeight="600"
        letterSpacing="2"
        fill="#1B2A4A"
      >
        DRINK
      </text>
      {/* "AR" top row */}
      <text
        x="4" y="36"
        fontFamily="'DM Serif Display', Georgia, serif"
        fontSize="32"
        fontWeight="700"
        fill="#1B2A4A"
      >
        AR
      </text>
      {/* "TE" bottom row, offset right */}
      <text
        x="52" y="54"
        fontFamily="'DM Serif Display', Georgia, serif"
        fontSize="32"
        fontWeight="700"
        fill="#1B2A4A"
      >
        TE
      </text>
    </svg>
  )
}

export function ArteStamp({ color = '#1B2A4A', size = 48 }) {
  return (
    <svg viewBox="0 0 80 80" width={size} height={size}>
      {/* Outer circle */}
      <circle cx="40" cy="40" r="38" fill="none" stroke={color} strokeWidth="1.5" />
      <circle cx="40" cy="40" r="34" fill="none" stroke={color} strokeWidth="0.5" />
      {/* AR / TE stacked */}
      <text x="40" y="36" textAnchor="middle" fontFamily="'DM Sans', sans-serif" fontSize="14" fontWeight="700" fill={color}>AR</text>
      <text x="40" y="52" textAnchor="middle" fontFamily="'DM Sans', sans-serif" fontSize="14" fontWeight="700" fill={color}>TE</text>
      {/* Circular text */}
      <defs>
        <path id="topArc" d="M 12,40 a 28,28 0 0,1 56,0" />
        <path id="bottomArc" d="M 68,40 a 28,28 0 0,1 -56,0" />
      </defs>
      <text fontSize="5" fontFamily="'DM Sans', sans-serif" fontWeight="500" fill={color} letterSpacing="1.5">
        <textPath href="#topArc" startOffset="50%" textAnchor="middle">COLD PRESSED</textPath>
      </text>
      <text fontSize="5" fontFamily="'DM Sans', sans-serif" fontWeight="500" fill={color} letterSpacing="1">
        <textPath href="#bottomArc" startOffset="50%" textAnchor="middle">FRESH JUICES &amp; MIXERS</textPath>
      </text>
    </svg>
  )
}
