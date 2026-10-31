// Development-only tool: no questions, transcripts or personal fields sent to API.
export const FIXTURE_CODES = ["1.001146", "1.003326", "1.003342", "1.000771"];
export const FIXTURE_TOOLS = [{type:"function", name:"inspect_test_document",
  description:"Inspect document identity in the fictional API for a connection demo, not legal requirements. Use only when the caller requests a document connection test and specifies a catalog procedure. Provincial extension: 1.001146; central extension: 1.003326; central visa issuance: 1.003342; visa-exemption extension: 1.000771. Ask if ambiguous.",
  parameters:{type:"object", properties:{procedure_code:{type:"string", enum:FIXTURE_CODES}}, required:["procedure_code"], additionalProperties:false}}];
export const FIXTURE_INSTRUCTIONS = "\n\nFICTIONAL API CONNECTION TEST MODE. You have exactly one development tool, inspect_test_document. This overrides only the earlier statement that no document test tool is connected. Official retrieval and legal advice remain unavailable. When asked to test or show a document, call this tool using the explicitly requested procedure variant; ask a short clarification if unclear. Do not claim you fetched anything before a successful result. After the result, say this is a fictional API test, identify the document in the caller's language, and mention its captured section heading/count. These are unreviewed document identity metadata, not requirements or advice. Do not invent, quote or summarize requirements, fees, deadlines or form editions. Do not read URLs/citation codes aloud. The source is displayed as text in the test transcript. For failure say the test API is unavailable. Do not invoke the tool again after receiving its result unless the caller requests another document. Do not send personal information or transcripts to it.";

export async function inspectFixtureDocument(argumentsText, signal) {
  let args;
  try { args = JSON.parse(argumentsText); } catch { return {error:"invalid_arguments"}; }
  if (!args || Object.keys(args).length !== 1 || !FIXTURE_CODES.includes(args.procedure_code)) return {error:"invalid_arguments"};
  const response = await fetch("/api/voice/fixture-document", {method:"POST", credentials:"same-origin",
    headers:{"Content-Type":"application/json"}, body:JSON.stringify(args), signal});
  if (!response.ok || response.headers.get("X-HoSo-Synthetic-Fixture") !== "1") throw new Error("fixture_unavailable");
  const text = await response.text();
  if (text.length > 5000) throw new Error("invalid_fixture_response");
  const result = JSON.parse(text);
  if (result.synthetic !== true || result.procedure_code !== args.procedure_code || typeof result.document_title !== "string" || result.document_title.length > 500 || typeof result.section_heading !== "string" || result.section_heading.length > 500 || !Number.isInteger(result.section_count) || result.section_count < 1 || result.section_count > 100) throw new Error("invalid_fixture_response");
  const source = new URL(result.source_url);
  if (source.protocol !== "https:" || source.hostname !== "vpcp.dichvucong.gov.vn" || source.searchParams.get("ma_thu_tuc") !== args.procedure_code) throw new Error("invalid_fixture_source");
  // Deliberately exclude raw excerpt, instructions and all unexpected API fields.
  return {synthetic:true, procedure_code:args.procedure_code, document_title:result.document_title,
    section_heading:result.section_heading, section_count:result.section_count, source_url:source.href};
}
