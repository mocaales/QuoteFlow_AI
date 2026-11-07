export type InvoiceLine = { zaporedje: number; naziv: string; opis: string; vrsta_dela: string; enota: string; cena_na_enoto: string; kolicina: string; popust: string; stopnja_ddv: string; neto: string; ddv: string; koncna_cena: string };
export type Invoice = {
 stevilka: string | null; stanje_dokumenta: string; stanje_placila: string;
 izdajatelj_naziv: string | null; izdajatelj_naslov: string | null; izdajatelj_davcna: string | null; prejemnik_naziv: string | null; prejemnik_naslov: string | null;
 izdan_ob: string | null; poslan_ob: string | null; zapade_dne: string | null; placano_ob: string | null;
 ponudba: { stevilka: string; razlicica: number }; postavke: InvoiceLine[]; ddv_po_stopnjah: { stopnja_ddv: string; osnova: string; ddv: string }[]; neto: string; ddv: string; skupaj: string;
};
