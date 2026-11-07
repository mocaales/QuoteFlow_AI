export type QuoteSummary = { id: string; stevilka: string; razlicica: number; stanje: string; poslano_ob: string | null; odgovorjeno_ob: string | null; velja_do: string | null; nadomescena: boolean; neto: string; ddv: string; skupaj: string };
export type QuoteMaterial = { material_id: string; naziv: string; enota: string; kolicina_na_enoto: string; cena_na_enoto: string; kolicina_skupaj: string };
export type QuoteLine = { id: string; zaporedje: number; naziv: string; opis: string; vrsta_dela: string; enota: string; cena_na_enoto: string; kolicina: string; popust: string; stopnja_ddv: string; izmera_skupaj: string; neto: string; ddv: string; koncna_cena: string; materiali: QuoteMaterial[] };
export type VatTotal = { stopnja_ddv: string; osnova: string; ddv: string };
export type Quote = QuoteSummary & { postavke: QuoteLine[]; ddv_po_stopnjah: VatTotal[] };
export type QuoteInput = { velja_do?: string | null };
// Customer view: no ids of lines, no materials, no labour fields
export type CustomerMeasure = { zaporedje: number; enota: string; odstej: boolean; kosi: string; dolzina: string | null; visina: string | null; sirina: string | null; vrednost: string };
export type CustomerQuoteLine = Omit<QuoteLine, 'id' | 'materiali'> & { izmere: CustomerMeasure[] };
export type CustomerQuote = QuoteSummary & { podjetje_naziv: string; postavke: CustomerQuoteLine[]; ddv_po_stopnjah: VatTotal[] };
export const stateLabels: Record<string, string> = { osnutek: 'Osnutek', poslana: 'Poslana', sprejeta: 'Sprejeta', zavrnjena: 'Zavrnjena' };
