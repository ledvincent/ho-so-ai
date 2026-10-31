import 'server-only';
import { verifiedSession } from './session';
import { createDiscoveryHandler, createRequestLimiter } from '../discovery/handler';
import { createDiscoveryClient } from '../discovery/upstream';
import workflow from '../../../api/hoso_api/chat/assets/na5-workflow.json';

export const proxyDiscovery = createDiscoveryHandler({
  verifySession: verifiedSession,
  provider: () => process.env.HOSO_AUTH_PROVIDER,
  deploymentMode: () => process.env.HOSO_DEPLOYMENT_MODE,
  publicOrigin: () => process.env.HOSO_PUBLIC_ORIGIN,
  client: () => createDiscoveryClient({ baseUrl: process.env.HOSO_VINCENT_API_URL, workflow }),
  limit: createRequestLimiter(),
});
