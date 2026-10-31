/** Original Folded H geometry from the owner-private Site design, source 9905bc0. */
export function BrandMark({ className }: { className?: string }) {
  return <svg className={className} viewBox="0 0 32 32" fill="currentColor" aria-hidden="true" focusable="false"><path d="M5 5h6v7l10 3V5h6v22h-6v-6l-10-3v9H5Z" /></svg>;
}

export function Brand() {
  return <span className="brand"><BrandMark className="brand-mark" /><span>Hồ Sơ <b>AI</b><small>Rõ ràng từng bước</small></span></span>;
}
