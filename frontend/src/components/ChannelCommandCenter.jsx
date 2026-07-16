import React from 'react'
import { channelMeta, formatCurrency, roasBand, STATUS_CLASSES, UNCERTAINTY_BAND } from '../utils/forecast'

const LEVEL_LABEL = { p10: 'P10 (worst case)', p50: 'P50 (expected)', p90: 'P90 (best case)' }

function RoasHealthBar({ roas }) {
  const band = STATUS_CLASSES[roasBand(roas)]
  const widthPct = Math.max(4, Math.min(100, (roas / 6) * 100))
  return (
    <div>
      <div className="flex items-center justify-between text-xs text-neutral-400 mb-1">
        <span>ROAS health</span>
        <span className={`font-semibold ${band.text}`}>{roas.toFixed(2)}x</span>
      </div>
      <div className="h-2 rounded-full bg-neutral-800 overflow-hidden">
        <div className={`h-full rounded-full ${band.bg}`} style={{ width: `${widthPct}%` }} />
      </div>
    </div>
  )
}

function RevenueRangeBar({ revenueP10, revenueP50, revenueP90, maxRevenue }) {
  const pct = (v) => Math.max(2, Math.min(100, (v / maxRevenue) * 100))
  return (
    <div className="space-y-1.5">
      <div className="text-xs text-neutral-400">Revenue range</div>
      <div className="relative h-6">
        <div
          className="absolute inset-y-0 left-0 rounded bg-series-blue/25"
          style={{ width: `${pct(revenueP90)}%` }}
        />
        <div
          className="absolute inset-y-0 left-0 rounded bg-series-blue/55"
          style={{ width: `${pct(revenueP50)}%` }}
        />
        <div
          className="absolute inset-y-0 left-0 rounded bg-series-blue"
          style={{ width: `${pct(revenueP10)}%` }}
        />
      </div>
      <div className="flex justify-between text-[11px] text-neutral-400 tabular-nums">
        <span>P10 {formatCurrency(revenueP10)}</span>
        <span>P50 {formatCurrency(revenueP50)}</span>
        <span>P90 {formatCurrency(revenueP90)}</span>
      </div>
    </div>
  )
}

function ConfidenceBadge({ uncertaintyLevel }) {
  const status = STATUS_CLASSES[UNCERTAINTY_BAND[uncertaintyLevel] ?? 'warning']
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold ${status.badgeBg} ${status.badgeText}`}>
      {uncertaintyLevel} UNCERTAINTY
    </span>
  )
}

export default function ChannelCommandCenter({ channels, level, onBudgetChange }) {
  if (!channels.length) {
    return <div className="text-neutral-400">No forecast data loaded.</div>
  }

  const maxRevenue = Math.max(...channels.map((c) => c.revenueP90), 1)

  return (
    <div>
      <p className="text-sm text-neutral-400 mb-4">
        Showing <span className="text-white font-medium">{LEVEL_LABEL[level]}</span> revenue at each channel's current
        budget. Edit a budget to simulate a different spend level.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {channels.map((c) => {
          const meta = channelMeta(c.channel)
          return (
            <div key={c.channel} className="rounded-xl border border-neutral-800 bg-neutral-900 p-4 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className={`h-2.5 w-2.5 rounded-full ${meta.dot}`} />
                  <h3 className="font-semibold">{meta.label}</h3>
                </div>
                <ConfidenceBadge uncertaintyLevel={c.uncertaintyLevel} />
              </div>

              <label className="block">
                <span className="text-xs text-neutral-400">Proposed budget</span>
                <div className="mt-1 flex items-center rounded-lg border border-neutral-700 bg-neutral-950 px-2">
                  <span className="text-neutral-500 text-sm">$</span>
                  <input
                    type="number"
                    className="w-full bg-transparent px-2 py-1.5 text-sm tabular-nums focus:outline-none"
                    value={Math.round(c.budget)}
                    min={0}
                    onChange={(e) => onBudgetChange(c.channel, Number(e.target.value))}
                  />
                </div>
              </label>

              <RoasHealthBar roas={c.roas} />
              <RevenueRangeBar
                revenueP10={c.revenueP10}
                revenueP50={c.revenueP50}
                revenueP90={c.revenueP90}
                maxRevenue={maxRevenue}
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}
