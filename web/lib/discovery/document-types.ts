export type JsonObject = Record<string, unknown>;
export type DiscoveryChatRequest = {
  message: string;
  procedure_code?: string | null;
  history?: { role: 'user' | 'assistant'; content: string }[];
  retrieval_state?: string | null;
  clarification_answer?: string | null;
};
export type DiscoveryOriginal = { bytes: Uint8Array; contentType: string; filename: string };
export type DiscoveryDocumentValues = { values: Record<string, string>; template_version: string };
export type DiscoveryDocumentDownload = DiscoveryDocumentValues & { review_token: string; confirmed: true };
export type DiscoveryDocumentPages = JsonObject & { template_version: string; pages: { page_number: number; image_data_url: string }[] };
export type DiscoveryDocumentPreview = { data?: DiscoveryDocumentPages; bytes?: Uint8Array; contentType: string; reviewToken: string };
export type DiscoveryFormAction = JsonObject & {
  document_id: string; form_id: string; procedure_code: string;
  template_sha256: string; template_version: string; revision: string; review_status: string;
  applicability: string; download_available: boolean;
  schema_url: string; template_url: string; template_pages_url: string; validate_url: string;
  preview_url: string; preview_pages_url: string; download_url: string;
};
export type DiscoveryDocumentSchema = JsonObject & {
  document_id: string; form_id: string; procedure_code: string; name: string; revision: string;
  effective_from: string | null; review_status: string; applicability: string; download_available: boolean;
  template_sha256: string; template_version: string; page_count: number;
  fields: JsonObject[]; fixed_values: Record<string, string>; date_order: string[][];
};
export type DiscoveryClient = {
  search(query: string): Promise<JsonObject>;
  procedure(code: string): Promise<JsonObject>;
  profile(code: string): Promise<JsonObject>;
  analysis(code: string, sha: string): Promise<JsonObject>;
  original(code: string, sha: string): Promise<DiscoveryOriginal>;
  schema(code: string, sha: string): Promise<JsonObject>;
  chat(body: DiscoveryChatRequest): Promise<JsonObject>;
  setup(): Promise<JsonObject>;
  documents(code: string): Promise<JsonObject>;
  documentSchema(id: string): Promise<DiscoveryDocumentSchema>;
  documentTemplate(id: string): Promise<DiscoveryOriginal>;
  documentPages(id: string): Promise<DiscoveryDocumentPages>;
  documentValidate(id: string, body: DiscoveryDocumentValues): Promise<JsonObject>;
  documentPreview(id: string, body: DiscoveryDocumentValues, pages: boolean): Promise<DiscoveryDocumentPreview>;
  documentDownload(id: string, body: DiscoveryDocumentDownload): Promise<DiscoveryOriginal>;
};
