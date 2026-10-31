'use client';

/** UI chrome is rendered inside the authenticated workspace.
 * This wrapper is presentation only; AUTH-02 owns server authorization. */
export function SiteShell({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}