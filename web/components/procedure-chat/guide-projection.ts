import sourceCopy from '../../../docs/demo-guide-01-source-copy.json';
import type { Locale } from '@/components/ui/locale-text';
import type { Candidate, ProcedureDetail } from './model';

export type Bilingual = { vi: string; en: string };
type SourceRef = { json_pointer: string; quote_vi: string };
export type GuideItem = { id: string; kind: 'document' | 'submission_instruction'; title: Bilingual; text: Bilingual; condition: Bilingual | null; originals: number | null; copies: number | null; source_ref: SourceRef };
export type ProcedureGuideCopy = { procedure_code: string; title: Bilingual; source: { url: string; sha256: string; retrieved_at: string }; checklist: GuideItem[]; steps: { id: string; title: Bilingual; text: Bilingual; source_ref: SourceRef }[]; conditions: { text: Bilingual; source_ref: SourceRef }[]; notes: Bilingual[] };

export const guideCopy = sourceCopy.procedures as Record<string, ProcedureGuideCopy>;

export function guideFor(detail: ProcedureDetail): ProcedureGuideCopy | null {
  if (detail.fixture) return null;
  const guide = guideCopy[detail.candidate.code];
  return guide?.procedure_code === detail.candidate.code && guide.source.sha256 === detail.sourceVersion ? guide : null;
}
export function candidateLabel(candidate: Candidate, locale: Locale): string {
  if (locale === 'vi') return candidate.name;
  return candidate.nameEn || guideCopy[candidate.code]?.title.en || candidate.name;
}
export const guideText = (text: Bilingual, locale: Locale) => text[locale];
