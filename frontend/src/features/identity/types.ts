export type Vloga = { id: string; podjetje_id: string | null; vloga: 'admin' | 'stranka' | 'mojster' | 'delavec'; naziv: string | null };
export type Profil = { id: string; e_posta: string; ime: string; priimek: string; vloge: Vloga[] };
export type Podjetje = { id: string; lastnik_id: string; naziv: string; maticna_stevilka: string; davcna_stevilka: string | null; naslov: string; aktivno: boolean };
export type Uporabnik = { id: string; e_posta: string; ime: string; priimek: string };
export type Dodelitev = Vloga & { uporabnik_id: string; e_posta: string; aktivna: boolean };
