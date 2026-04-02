import { useNavigate } from 'react-router-dom'
import { Tag, Wine, Leaf, Droplets, Box, Package } from 'lucide-react'
import { ARTE_NAVY } from '../components/CitrusIcon'

const CATEGORIES = [
  {
    key: 'label',
    label: 'Labels',
    icon: Tag,
    bg: 'bg-blue-50',
    iconBg: 'bg-blue-100',
    iconColor: 'text-blue-600',
    border: 'border-blue-100',
    arrowColor: '#2563eb',
  },
  {
    key: 'bottle',
    label: 'Bottles',
    icon: Wine,
    bg: 'bg-violet-50',
    iconBg: 'bg-violet-100',
    iconColor: 'text-violet-600',
    border: 'border-violet-100',
    arrowColor: '#7c3aed',
  },
  {
    key: 'raw',
    label: 'Raw Ingredients',
    icon: Leaf,
    bg: 'bg-green-50',
    iconBg: 'bg-green-100',
    iconColor: 'text-green-600',
    border: 'border-green-100',
    arrowColor: '#16a34a',
  },
  {
    key: 'juice',
    label: 'Juices',
    icon: Droplets,
    bg: 'bg-orange-50',
    iconBg: 'bg-orange-100',
    iconColor: 'text-orange-600',
    border: 'border-orange-100',
    arrowColor: '#ea580c',
  },
  {
    key: 'box',
    label: 'Boxes',
    icon: Box,
    bg: 'bg-amber-50',
    iconBg: 'bg-amber-100',
    iconColor: 'text-amber-700',
    border: 'border-amber-100',
    arrowColor: '#b45309',
  },
  {
    key: 'misc',
    label: 'Miscellaneous',
    icon: Package,
    bg: 'bg-slate-50',
    iconBg: 'bg-slate-100',
    iconColor: 'text-slate-500',
    border: 'border-slate-100',
    arrowColor: '#64748b',
  },
]

export default function Home() {
  const navigate = useNavigate()

  return (
    <div className="max-w-4xl mx-auto">
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight" style={{ color: ARTE_NAVY }}>
          Inventory
        </h1>
        <p className="text-stone-400 text-sm mt-1">Select a category to view and manage stock</p>
      </div>

      {/* 3×2 category grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {CATEGORIES.map(({ key, label, icon: Icon, bg, iconBg, iconColor, border, arrowColor }) => (
          <button
            key={key}
            onClick={() => navigate(`/brand/all?cat=${key}`)}
            className={`group relative ${bg} border ${border} rounded-2xl p-6 text-left transition-all duration-200 hover:shadow-md hover:scale-[1.02] active:scale-[0.98] cursor-pointer`}
          >
            <div className={`w-12 h-12 ${iconBg} rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-200`}>
              <Icon size={24} className={iconColor} />
            </div>
            <h3 className="text-base font-bold text-stone-800">{label}</h3>
            <p className="text-xs text-stone-400 mt-1 font-medium">View &amp; manage stock</p>

            {/* Arrow on hover */}
            <div className="absolute bottom-5 right-5 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={arrowColor} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
