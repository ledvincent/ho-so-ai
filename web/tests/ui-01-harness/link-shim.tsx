import { forwardRef, type AnchorHTMLAttributes, type MouseEvent } from 'react';
import { record } from './state';

type Props = Omit<AnchorHTMLAttributes<HTMLAnchorElement>, 'href'> & {
  href: string | { pathname?: string; hash?: string };
  prefetch?: boolean | 'auto' | null;
  replace?: boolean;
  scroll?: boolean;
};
const Link = forwardRef<HTMLAnchorElement, Props>(function HarnessLink({ href, prefetch: _prefetch, replace: _replace, scroll: _scroll, onClick, ...props }, ref) {
  const destination = typeof href === 'string' ? href : `${href.pathname ?? '/'}${href.hash ?? ''}`;
  function stayInHarness(event: MouseEvent<HTMLAnchorElement>) {
    event.preventDefault();
    record(`NAVIGATION blocked in test harness → ${destination}`);
    onClick?.(event);
  }
  return <a {...props} ref={ref} href={destination} onClick={stayInHarness} />;
});
export default Link;
