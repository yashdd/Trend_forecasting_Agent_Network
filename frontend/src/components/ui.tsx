import * as React from "react";

export function cx(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(" ");
}

export function Card(props: React.PropsWithChildren<{ className?: string }>) {
  return (
    <div
      className={cx(
        "rounded-3xl border border-white/10 bg-white/5 shadow-[0_10px_40px_rgba(0,0,0,0.35)] backdrop-blur-xl",
        props.className
      )}
    >
      {props.children}
    </div>
  );
}

export function CardHeader(props: React.PropsWithChildren<{ className?: string }>) {
  return (
    <div className={cx("px-6 pt-6 pb-5 border-b border-white/10", props.className)}>
      {props.children}
    </div>
  );
}

export function CardBody(props: React.PropsWithChildren<{ className?: string }>) {
  return <div className={cx("px-6 py-5", props.className)}>{props.children}</div>;
}

export function Button(
  props: React.ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: "primary" | "secondary" | "ghost";
    size?: "sm" | "md";
  }
) {
  const { variant = "primary", size = "md", className, ...rest } = props;
  const base =
    "inline-flex items-center justify-center rounded-xl font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed";
  const sizes = size === "sm" ? "h-9 px-3 text-sm" : "h-10 px-4 text-sm";
  const variants =
    variant === "primary"
      ? "bg-gradient-to-r from-cyan-400 via-violet-400 to-emerald-400 text-slate-950 hover:brightness-110 shadow-[0_10px_30px_rgba(34,211,238,0.18)]"
      : variant === "secondary"
        ? "bg-white/10 hover:bg-white/14 text-white border border-white/10"
        : "bg-transparent hover:bg-white/5 text-white/80";
  return <button className={cx(base, sizes, variants, className)} {...rest} />;
}

export function Badge(
  props: React.PropsWithChildren<{ tone?: "emerald" | "sky" | "amber" | "slate"; className?: string }>
) {
  const tone = props.tone ?? "slate";
  const tones: Record<string, string> = {
    emerald: "bg-emerald-400/15 text-emerald-200 border-emerald-400/20",
    sky: "bg-cyan-400/15 text-cyan-200 border-cyan-400/20",
    amber: "bg-amber-400/15 text-amber-200 border-amber-400/20",
    slate: "bg-white/8 text-white/80 border-white/10",
  };
  return (
    <span
      className={cx(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        tones[tone],
        props.className
      )}
    >
      {props.children}
    </span>
  );
}

export function Spinner(props: { className?: string; label?: string }) {
  return (
    <div className={cx("inline-flex items-center gap-2 text-white/70", props.className)}>
      <span className="h-4 w-4 rounded-full border-2 border-white/20 border-t-cyan-300 animate-spin" />
      {props.label ? <span className="text-sm">{props.label}</span> : null}
    </div>
  );
}

export function SegmentedTabs<T extends string>(props: {
  value: T;
  onChange: (v: T) => void;
  options: Array<{ value: T; label: string }>;
  className?: string;
}) {
  return (
    <div className={cx("inline-flex rounded-2xl bg-white/6 p-1 border border-white/10", props.className)}>
      {props.options.map((o) => {
        const active = o.value === props.value;
        return (
          <button
            key={o.value}
            type="button"
            onClick={() => props.onChange(o.value)}
            className={cx(
              "px-3 h-9 rounded-lg text-sm font-medium transition-colors",
              active
                ? "bg-gradient-to-r from-white/16 to-white/10 text-white shadow-[0_8px_26px_rgba(0,0,0,0.25)]"
                : "text-white/70 hover:text-white"
            )}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

