import { NavLink } from "react-router-dom";
import AlertBell from "./AlertBell";
import PipelineStatus from "./PipelineStatus";
import { cx } from "./ui";

const nav = [
  { to: "/", label: "Signals" },
  { to: "/dashboard", label: "Dashboard" },
  { to: "/alerts", label: "Alerts" },
  { to: "/reports", label: "Reports" },
];

function LogoMark() {
  return (
    <div className="h-10 w-10 rounded-2xl bg-gradient-to-br from-cyan-300 via-violet-300 to-emerald-300 p-[1px] shadow-[0_12px_40px_rgba(34,211,238,0.18)]">
      <div className="h-full w-full rounded-2xl bg-[#060915] flex items-center justify-center">
        <div className="h-4 w-4 rounded-full bg-white shadow-[0_0_0_3px_rgba(167,139,250,0.25)]" />
      </div>
    </div>
  );
}

export default function Navbar() {
  return (
    <header className="sticky top-0 z-30 border-b border-white/10 bg-[#060915]/70 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-6">
        <div className="flex items-center gap-3 min-w-0">
          <LogoMark />
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="font-display text-base sm:text-[17px] font-semibold text-white truncate leading-tight">
                Trend Analyzer
              </h1>
              <span className="hidden sm:inline text-[11px] font-medium text-white/60 rounded-full border border-white/10 px-2 py-0.5">
                beta
              </span>
            </div>
            <p className="hidden sm:block text-[12px] text-white/60 truncate">
              Finds early signals before they go mainstream
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 sm:gap-4">
          <PipelineStatus className="hidden md:flex" />
          <AlertBell />
          <nav className="flex items-center justify-center rounded-2xl border border-white/10 bg-white/5 p-1 shadow-[0_10px_30px_rgba(0,0,0,0.3)]">
            {nav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  cx(
                    "h-9 px-3 sm:px-4 rounded-2xl text-[13px] font-semibold tracking-[0.01em] transition-colors flex items-center",
                    isActive
                      ? "bg-gradient-to-r from-white/16 to-white/10 text-white shadow-[0_8px_26px_rgba(0,0,0,0.25)]"
                      : "text-white/75 hover:bg-white/5"
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </div>
    </header>
  );
}

