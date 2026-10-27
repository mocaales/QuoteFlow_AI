export type Vloga = { id: string; podjetje_id: string | null; vloga: 'administrator' | 'nabavnik' | 'ponudnik'; naziv: string | null };
export type Profil = { id: string; e_posta: string; vloge: Vloga[] };
export type Podjetje = { id: string; naziv: string; stanje: 'aktivno' | 'neaktivno' };
export type Uporabnik = { id: string; e_posta: string };
export type Dodelitev = Vloga & { uporabnik_id: string; e_posta: string; aktivna: boolean };
