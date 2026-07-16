import React from 'react'

const POSITIONS = [
  { key: 'p10', label: 'P10', caption: 'Worst case — plan budgets you can survive even here.' },
  { key: 'p50', label: 'P50', caption: 'Expected case — the tribunal\'s single best estimate.' },
  { key: 'p90', label: 'P90', caption: 'Best case — what a strong month looks like.' },
]

export default function RiskDial({ level, onChange }) {
  const active = POSITIONS.find((p) => p.key === level) ?? POSITIONS[1]

  return (
    <div className="flex items-center gap-3">
      <div className="flex rounded-lg border border-neutral-700 overflow-hidden text-sm">
        {POSITIONS.map((p) => (
          <button
            key={p.key}
            onClick={() => onChange(p.key)}
            className={`px-3 py-1.5 font-semibold ${
              level === p.key ? 'bg-series-blue text-white' : 'bg-neutral-900 text-neutral-300'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>
      <p className="text-xs text-neutral-400 max-w-xs">{active.caption}</p>
    </div>
  )
}
