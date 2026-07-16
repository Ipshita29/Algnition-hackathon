import Papa from 'papaparse'
import React, { useEffect, useMemo, useState } from 'react'
import BattleView from './components/BattleView'
import ChannelCommandCenter from './components/ChannelCommandCenter'
import RiskDial from './components/RiskDial'
import TribunalVerdictPanel from './components/TribunalVerdictPanel'
import { aggregateByChannel, coerceRow } from './utils/forecast'

const TABS = [
  { key: 'command', label: 'Channel Command Center' },
  { key: 'verdict', label: 'Tribunal Verdict Panel' },
  { key: 'battle', label: 'Battle View' },
]

const PERIODS = [30, 60, 90]

export default function App() {
  const [rows, setRows] = useState([])
  const [loadError, setLoadError] = useState(null)
  const [level, setLevel] = useState('p50')
  const [periodDays, setPeriodDays] = useState(30)
  const [budgetOverrides, setBudgetOverrides] = useState({})
  const [activeTab, setActiveTab] = useState('command')

  useEffect(() => {
    fetch('/predictions.csv')
      .then((res) => {
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
        return res.text()
      })
      .then((text) => {
        const { data } = Papa.parse(text, { header: true, skipEmptyLines: true })
        setRows(data.map(coerceRow))
      })
      .catch((err) => setLoadError(err.message))
  }, [])

  function handleFileUpload(e) {
    const file = e.target.files?.[0]
    if (!file) return
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        setRows(results.data.map(coerceRow))
        setBudgetOverrides({})
        setLoadError(null)
      },
    })
  }

  const filteredRows = useMemo(() => rows.filter((r) => r.period_days === periodDays), [rows, periodDays])
  const channels = useMemo(
    () => aggregateByChannel(filteredRows, budgetOverrides, level),
    [filteredRows, budgetOverrides, level]
  )

  function handleChannelBudgetChange(channel, newTotalBudget) {
    const current = channels.find((c) => c.channel === channel)
    if (!current || current.budget <= 0) return
    const scale = newTotalBudget / current.budget

    setBudgetOverrides((prev) => {
      const next = { ...prev }
      for (const campaign of current.campaigns) {
        next[campaign.campaign_name] = campaign.budget * scale
      }
      return next
    })
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6 md:p-8">
      <header className="mb-6">
        <h1 className="text-2xl font-bold mb-1">War Room — AIgnition 3.0</h1>
        <p className="text-gray-400 text-sm">Probabilistic revenue forecasting across Google, Meta, and Microsoft Ads</p>
      </header>

      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <RiskDial level={level} onChange={setLevel} />

        <div className="flex items-center gap-3">
          <div className="flex rounded-lg border border-neutral-700 overflow-hidden text-sm">
            {PERIODS.map((p) => (
              <button
                key={p}
                onClick={() => setPeriodDays(p)}
                className={`px-3 py-1.5 ${
                  periodDays === p ? 'bg-white text-gray-950 font-semibold' : 'bg-neutral-900 text-neutral-300'
                }`}
              >
                {p}d
              </button>
            ))}
          </div>

          <label className="text-sm text-neutral-300 cursor-pointer rounded-lg border border-neutral-700 px-3 py-1.5 hover:bg-neutral-900">
            Load predictions.csv
            <input type="file" accept=".csv" className="hidden" onChange={handleFileUpload} />
          </label>
        </div>
      </div>

      {loadError && (
        <div className="mb-6 rounded-lg border border-status-critical/40 bg-status-critical/10 px-4 py-2 text-sm text-status-critical">
          Couldn't load default predictions.csv ({loadError}). Run ./run.sh, then use "Load predictions.csv" above.
        </div>
      )}

      <nav className="flex gap-1 mb-6 border-b border-neutral-800">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
              activeTab === tab.key
                ? 'border-series-blue text-white'
                : 'border-transparent text-neutral-400 hover:text-neutral-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <main>
        {activeTab === 'command' && (
          <ChannelCommandCenter channels={channels} level={level} onBudgetChange={handleChannelBudgetChange} />
        )}
        {activeTab === 'verdict' && (
          <TribunalVerdictPanel rows={filteredRows} horizonDays={periodDays} />
        )}
        {activeTab === 'battle' && (
          <BattleView rows={filteredRows} />
        )}
      </main>
    </div>
  )
}
