export type CatalogInput = {
 vrsta: 'blago' | 'storitev'; opis: string; enota: string;
 cena_na_enoto: string; strosek_na_enoto: string; dobavni_rok_dni: number | null; aktivna: boolean;
};
export type CatalogItem = CatalogInput & {
 id: string; podjetje_id: string; potrjeno_ob: string | null;
 razpolozljiva_kolicina: string | null; zaloga_potrjeno_ob: string | null;
};
export type SalesRules = {
 id: string; podjetje_id: string; najmanjsa_marza: string; najvecji_popust: string;
 najdaljsi_rok_dni: number; velja_od: string; velja_do: string | null;
};
export type RulesInput = Omit<SalesRules, 'id' | 'podjetje_id' | 'velja_od'> & { velja_od: string | null };
export type SupplierTab = 'cenik' | 'zaloge' | 'pravila';
