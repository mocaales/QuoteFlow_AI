export type CatalogInput = { naziv: string; opis: string; vrsta_dela: string; enota: string; cena_na_enoto: string; stopnja_ddv: string; aktivna: boolean };
export type CatalogItem = CatalogInput & { id: string; podjetje_id: string };
export type MaterialKind = { id: string; podjetje_id: string; naziv: string };
export type Stock = { lokacija: string; kolicina: string };
export type MaterialInput = { vrsta_materiala_id: string; sifra: string; naziv: string; enota: string; cena_na_enoto: string; aktiven: boolean };
export type Material = MaterialInput & { id: string; zaloge: Stock[] };
export type SupplierTab = 'cenik' | 'materiali' | 'zaloge';
