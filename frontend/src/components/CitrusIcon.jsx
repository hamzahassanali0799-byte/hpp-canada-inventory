// === BRAND COLOR MAPS ===
// All brands now have real bottle images

const COLORS = {
  // Arte
  'arte-orange':     { label: 'Orange',          bottleImg: '/bottles/orange.png',          labelColor: '#F47B20', cardBg: '#FFF7ED', accent: '#F47B20' },
  'arte-lime':       { label: 'Lime',            bottleImg: '/bottles/lime.png',            labelColor: '#B5CC3B', cardBg: '#F7FAE8', accent: '#8DB62B' },
  'arte-lemon':      { label: 'Lemon',           bottleImg: '/bottles/lemon.png',           labelColor: '#F2CC3A', cardBg: '#FFFDE7', accent: '#F2CC3A' },
  'arte-grapefruit': { label: 'Grapefruit',      bottleImg: '/bottles/grapefruit.png',      labelColor: '#E86BA0', cardBg: '#FFF0F5', accent: '#E86BA0' },
  // Quirkies — real bottle images
  'quirk-blueberry': { label: 'Blueberry Blend',  bottleImg: '/bottles/quirk-blueberry.png', labelColor: '#6B6BC7', cardBg: '#F0F0FF', accent: '#6B6BC7' },
  'quirk-sunshine':  { label: 'Sunshine',          bottleImg: '/bottles/quirk-sunshine.png',  labelColor: '#F5A623', cardBg: '#FFF8EB', accent: '#F5A623' },
  'quirk-apple':     { label: '100% Apple',        bottleImg: '/bottles/quirk-apple.png',     labelColor: '#E54B4B', cardBg: '#FFF0F0', accent: '#E54B4B' },
  'quirk-tropical':  { label: 'Tropical Twist',    bottleImg: '/bottles/quirk-tropical.png',  labelColor: '#F5C842', cardBg: '#FFFCE8', accent: '#F5C842' },
  // Joosy — real bottle images
  'joosy-tropical':  { label: 'Tropical Pulse',    bottleImg: '/bottles/joosy-tropical.png',  labelColor: '#3BB5D6', cardBg: '#EBF9FF', accent: '#3BB5D6' },
  'joosy-mandarin':  { label: 'Mandarin Juice',    bottleImg: '/bottles/joosy-mandarin.png',  labelColor: '#F5A623', cardBg: '#FFF8EB', accent: '#F5A623' },
  'joosy-blueberry': { label: 'Blueberry Bliss',   bottleImg: '/bottles/joosy-blueberry.png', labelColor: '#2C3E6B', cardBg: '#EDF0F7', accent: '#2C3E6B' },
  'joosy-apple':     { label: '100% Apple',         bottleImg: '/bottles/joosy-apple.png',     labelColor: '#E5394B', cardBg: '#FFF0F1', accent: '#E5394B' },
  // Box
  'box':             { label: 'Box',               bottleImg: null,                           labelColor: '#8B7355', cardBg: '#FAF5EF', accent: '#8B7355', emoji: '📦' },
}

export const ARTE_NAVY = '#1B2A4A'
export const QUIRK_RED = '#E54B4B'
export const JOOSY_GOLD = '#F5A623'

export function getCitrus(colorId) {
  return COLORS[colorId] || { label: colorId, bottleImg: null, labelColor: '#999', cardBg: '#f5f5f5', accent: '#999', emoji: '🧃' }
}

const BRAND_COLORS = {
  'Quirkies':    '#E54B4B',
  'Joosy':       '#F5A623',
  'General':     '#8B7355',
  'Drink Arte':  '#1B2A4A',
  'Arte':        '#1B2A4A',
  'HPPC':        '#2D6A4F',
  'Well Juicery':'#52796F',
  'Squoze':      '#E07B39',
  'Notch':       '#3D405B',
  'Singh':       '#9B2226',
  'Bestropic':   '#0077B6',
}

export function getBrandColor(brand) {
  return BRAND_COLORS[brand] || ARTE_NAVY
}

export default function BottleImage({ colorId, size = 'md' }) {
  const c = getCitrus(colorId)
  const heights = { sm: 'h-12', md: 'h-24', lg: 'h-40' }
  const pxMap = { sm: 48, md: 96, lg: 160 }

  if (c.bottleImg) {
    return <img src={c.bottleImg} alt={c.label} className={`${heights[size]} object-contain drop-shadow-lg`} />
  }

  const px = pxMap[size]
  return (
    <div
      className="rounded-2xl flex items-center justify-center"
      style={{ width: px * 0.7, height: px, backgroundColor: c.cardBg, border: `2px solid ${c.labelColor}` }}
    >
      <span style={{ fontSize: px * 0.35 }}>{c.emoji || '🧃'}</span>
    </div>
  )
}
