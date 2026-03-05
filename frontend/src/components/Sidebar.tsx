import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Database, FlaskConical, Crosshair, Activity } from 'lucide-react';

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/datasets', label: 'Datasets', icon: Database },
  { to: '/experiments', label: 'Experiments', icon: FlaskConical },
  { to: '/predict', label: 'Predict', icon: Crosshair },
];

export default function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 bottom-0 w-64 bg-[#0d1321] border-r border-slate-800/60 flex flex-col z-50">
      <div className="p-6 border-b border-slate-800/60">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-brand-600 flex items-center justify-center">
            <Activity size={20} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white tracking-tight">RiskPredict</h1>
            <p className="text-[11px] text-slate-500 font-mono tracking-wider uppercase">ML Platform</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? 'bg-brand-600/15 text-brand-400 border border-brand-500/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-slate-800/60">
        <p className="text-xs text-slate-600 text-center font-mono">v1.0.0</p>
      </div>
    </aside>
  );
}
