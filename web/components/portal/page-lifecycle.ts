/** Clear personal values before page caching; restored pages must re-fetch them. */
export function listenForProfilePageLifecycle(
  target: EventTarget,
  clear: () => void,
  reload: () => void,
): () => void {
  const hide = () => clear();
  const show = (event: Event) => {
    if ('persisted' in event && event.persisted === true) {
      clear();
      reload();
    }
  };
  target.addEventListener('pagehide', hide);
  target.addEventListener('pageshow', show);
  return () => {
    target.removeEventListener('pagehide', hide);
    target.removeEventListener('pageshow', show);
  };
}
