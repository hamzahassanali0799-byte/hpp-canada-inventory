import { useNavigate } from 'react-router-dom'
import { ARTE_NAVY, QUIRK_RED, JOOSY_GOLD } from '../components/CitrusIcon'

const BRANDS = [
  {
    key: 'Arte',
    name: 'Drink Arte',
    subtitle: 'Premium Cold-Pressed Juice',
    color: ARTE_NAVY,
    gradient: 'from-[#1B2A4A] to-[#2d4a7a]',
    bottles: ['orange', 'lime', 'lemon', 'grapefruit'],
    textColor: 'text-white',
  },
  {
    key: 'Quirkies',
    name: 'Quirkies',
    subtitle: 'Bold & Quirky Blends',
    color: QUIRK_RED,
    gradient: 'from-[#E54B4B] to-[#f06565]',
    bottles: ['quirk-blueberry', 'quirk-sunshine', 'quirk-apple', 'quirk-tropical'],
    textColor: 'text-white',
  },
  {
    key: 'Joosy',
    name: 'Joosy',
    subtitle: 'Fresh & Fruity',
    color: JOOSY_GOLD,
    gradient: 'from-[#F5A623] to-[#f7bc55]',
    bottles: ['joosy-tropical', 'joosy-mandarin', 'joosy-blueberry', 'joosy-apple'],
    textColor: 'text-white',
  },
]

export default function Home() {
  const navigate = useNavigate()

  return (
    <div className="min-h-[80vh] flex flex-col items-center justify-center px-4">
      {/* Header */}
      <div className="text-center mb-10">
        <img src="/hpp-logo.png" alt="HPP Canada" className="h-16 w-16 object-contain mx-auto mb-4" />
        <h1 className="text-3xl font-bold tracking-tight" style={{ color: ARTE_NAVY }}>
          HPP Canada
        </h1>
        <p className="text-stone-400 text-sm mt-1 uppercase tracking-[0.2em] font-semibold">
          Inventory Management
        </p>
      </div>

      {/* Brand Tabs */}
      <div className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-3 gap-5">
        {BRANDS.map((brand) => (
          <button
            key={brand.key}
            onClick={() => navigate(`/brand/${brand.key}`)}
            className={`group relative overflow-hidden rounded-3xl bg-gradient-to-br ${brand.gradient} p-8 min-h-[220px] flex flex-col justify-between text-left transition-all duration-300 hover:scale-[1.03] hover:shadow-2xl shadow-lg active:scale-[0.98]`}
          >
            {/* Decorative circles */}
            <div className="absolute -top-8 -right-8 w-32 h-32 rounded-full bg-white/10 group-hover:scale-110 transition-transform duration-500" />
            <div className="absolute -bottom-6 -left-6 w-24 h-24 rounded-full bg-white/5" />

            {/* Brand name */}
            <div className="relative z-10">
              <h2 className={`text-2xl font-bold ${brand.textColor}`}>
                {brand.name}
              </h2>
              <p className="text-white/70 text-sm mt-1 font-medium">
                {brand.subtitle}
              </p>
            </div>

            {/* Bottle images */}
            <div className="relative z-10 flex items-end gap-1 mt-4">
              {brand.bottles.map((b) => (
                <img
                  key={b}
                  src={`/bottles/${b}.png`}
                  alt={b}
                  className="h-16 object-contain drop-shadow-lg opacity-90 group-hover:opacity-100 transition-opacity"
                />
              ))}
            </div>

            {/* Arrow indicator */}
            <div className="absolute bottom-6 right-6 w-10 h-10 rounded-full bg-white/20 flex items-center justify-center group-hover:bg-white/30 transition-colors">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </div>
          </button>
        ))}
      </div>

      {/* Quick links */}
      <div className="mt-8 flex gap-4">
        <button
          onClick={() => navigate('/scan')}
          className="px-6 py-3 rounded-xl bg-white border border-stone-200 text-stone-600 font-semibold text-sm hover:bg-stone-50 hover:border-stone-300 transition shadow-sm"
        >
          Scan Invoice
        </button>
        <button
          onClick={() => navigate('/brand/all')}
          className="px-6 py-3 rounded-xl text-white font-semibold text-sm hover:opacity-90 transition shadow-sm"
          style={{ backgroundColor: ARTE_NAVY }}
        >
          View All Inventory
        </button>
      </div>
    </div>
  )
}
