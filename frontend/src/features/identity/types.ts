export type Vloga = { id: string; podjetje_id: string | null; vloga: 'admin' | 'stranka' | 'mojster' | 'delavec'; naziv: string | null };
export type Profil = { id: string; e_posta: string; ime: string; priimek: string; vloge: Vloga[] };
export type Podjetje = { id: string; lastnik_id: string; naziv: string; maticna_stevilka: string; davcna_stevilka: string | null; naslov: string; aktivno: boolean };
export type Uporabnik = { id: string; e_posta: string; ime: string; priimek: string };
export type Dodelitev = Vloga & { uporabnik_id: string; e_posta: string; aktivna: boolean };
export type Prosnja = { id: string; uporabnik_id: string; naziv_podjetja: string; maticna_stevilka: string; davcna_stevilka: string | null; naslov_podjetja: string; stanje: 'oddana' | 'odobrena' | 'zavrnjena'; podjetje_id: string | null; oddano_ob: string; odloceno_ob: string | null };
export type ProsnjaVnos = Pick<Prosnja, 'naziv_podjetja' | 'maticna_stevilka' | 'davcna_stevilka' | 'naslov_podjetja'>;
export type ProsnjaAdmin = Prosnja & { e_posta: string; ime: string; priimek: string };
