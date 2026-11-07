// Mirrors backend routers/postavke.py; Decimal as string
export type Unit = 'm' | 'm2' | 'm3' | 'kos';
export type Measure = { id: string; zaporedje: number; odstej: boolean; kosi: string; dolzina: string | null; visina: string | null; sirina: string | null; vrednost: string };
export type MeasureInput = { odstej: boolean; kosi: string; dolzina?: string; visina?: string; sirina?: string };
export type ItemInput = { naziv: string; opis: string; vrsta_dela_id: string; enota: Unit; cena_na_enoto: string; kolicina: string; popust: string; stopnja_ddv: string; urna_postavka?: string | null; stevilo_ur?: string | null; stevilo_delavcev?: number | null };
export type CatalogItemInput = { postavka_cenika_id: string; kolicina: string; popust: string };
// PostavkaSaved (POST/PUT response)
export type ItemSaved = { id: string; zaporedje: number; postavka_cenika_id: string | null; vrsta_dela_id: string; naziv: string; opis: string; enota: Unit; cena_na_enoto: string; kolicina: string; popust: string; stopnja_ddv: string; urna_postavka: string; stevilo_ur: string; stevilo_delavcev: number; izmera_skupaj: string; cena_dela: string; neto: string; koncna_cena: string };
// PostavkaRow (GET)
export type Item = ItemSaved & { ddv: string; izmere: Measure[]; vrsta_dela?: string };
export type ItemsOverview = { postavke: Item[]; neto: string; ddv: string; skupaj: string };
export type WorkTypeOption = { id: string; naziv: string; urna_postavka: string; stevilo_ur: string; stevilo_delavcev: number; aktivna: boolean };
export type CatalogOption = { id: string; naziv: string; opis: string; vrsta_dela_id: string; enota: Unit; cena_na_enoto: string; aktivna: boolean };
