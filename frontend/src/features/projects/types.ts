export type ProjectInput = { naziv: string; opis: string; lokacija_izvedbe: string };
export type ProjectCreate = ProjectInput & { e_posta_stranke: string };
export type Project = ProjectInput & { id: string; faza: string; stranka_ime: string; stranka_priimek: string; stranka_e_posta: string; termin_od: string | null; termin_do: string | null };
export type OwnProject = ProjectInput & { id: string; faza: string; podjetje_naziv: string; termin_od: string | null; termin_do: string | null };
export const phases: [string, string][] = [['pregled', 'Pregled'], ['ogled', 'Ogled'], ['ponudba', 'Ponudba'], ['termin', 'Termin'], ['izvedba', 'Izvedba'], ['obracun', 'Obračun'], ['zakljucen', 'Zaključen']];
