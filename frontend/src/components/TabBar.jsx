const TABS = [
  { id: 'chat', label: 'Chat' },
  { id: 'debug', label: 'Debug' },
]

export default function TabBar({ activeTab, onTabChange }) {
  return (
    <div className="flex gap-1.5 border-b border-slate-200/80 px-2.5 pb-2.5 pt-1">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          className={`group min-w-0 flex-1 h-9 rounded-lg border border-transparent bg-transparent px-2 text-xs font-semibold transition-all duration-200 focus:outline-none ${
            activeTab === tab.id
              ? 'border-white/30 bg-gradient-to-r from-violet-300/36 via-indigo-300/30 to-sky-300/28 text-white shadow-[0_4px_10px_rgba(20,24,40,0.22)]'
              : 'text-white/80 hover:border-white/25 hover:bg-white/12 hover:text-white'
          }`}
          onClick={() => onTabChange(tab.id)}
        >
          <span className="inline-flex items-center gap-1.5">
            <span
              className={`h-1.5 w-1.5 rounded-full transition-colors duration-200 ${
                activeTab === tab.id ? 'bg-white' : 'bg-white/40 group-hover:bg-white/70'
              }`}
            />
            {tab.label}
          </span>
        </button>
      ))}
    </div>
  )
}
