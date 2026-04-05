type BrandTheme = 'light' | 'dark';

function BrandIconSvg({ className = '' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 100 100"
      className={className}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <rect x="12" y="15" width="20" height="70" rx="10" fill="currentColor" />
      <rect x="68" y="15" width="20" height="70" rx="10" fill="currentColor" />
      <path d="M36 36L64 64" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
      <circle cx="50" cy="50" r="7.5" fill="currentColor" />
    </svg>
  );
}

export function BrandMark({
  size = 40,
  rounded = 'rounded-xl',
  className = '',
  theme,
}: {
  size?: number;
  rounded?: string;
  className?: string;
  theme?: BrandTheme;
}) {
  const themeClass = theme === 'dark' ? 'text-white' : theme === 'light' ? 'text-black dark:text-white' : 'text-foreground';

  return (
    <div
      className={`${rounded} ${themeClass} ${className}`}
      style={{ width: size, height: size }}
      aria-label="NexRag logo"
      role="img"
    >
      <BrandIconSvg className="h-full w-full" />
    </div>
  );
}

export function BrandWordmark({
  className = '',
  theme,
}: {
  className?: string;
  theme?: BrandTheme;
}) {
  const themeClass = theme === 'dark' ? 'text-white' : theme === 'light' ? 'text-black dark:text-white' : 'text-foreground';

  return (
    <div className={`flex items-center gap-3 ${themeClass} ${className}`}>
      <BrandIconSvg className="h-10 w-10 flex-shrink-0" />
      <span className="text-2xl leading-none tracking-tight">
        <span className="font-extrabold">Nex</span>
        <span className="font-light">RAG</span>
      </span>
    </div>
  );
}
