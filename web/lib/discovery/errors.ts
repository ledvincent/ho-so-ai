export class DiscoveryError extends Error {
  constructor(public readonly status: number, public readonly code: string, public readonly retryAfter?: string) {
    super(code);
    this.name = 'DiscoveryError';
  }
}
