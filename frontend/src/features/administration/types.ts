import type { Dodelitev, Uporabnik } from '../identity/types';
// Mirrors backend AdminRoleRow (v3 adds ime, priimek, je_lastnik, dodeljeno_ob)
export type AdminRole = Dodelitev & { ime: string; priimek: string; je_lastnik: boolean; dodeljeno_ob: string };
export type RoleInput = { uporabnik_id: string; podjetje_id: string | null; vloga: 'stranka' | 'mojster' | 'delavec' };
export type AdminUser = Uporabnik & { potrjen?: boolean };
export const roleNames: Record<Dodelitev['vloga'], string> = { admin: 'Skrbnik', stranka: 'Stranka', mojster: 'Mojster', delavec: 'Delavec' };
export const fullName = (p: { ime?: string; priimek?: string; e_posta: string }) => [p.ime, p.priimek].filter(Boolean).join(' ') || p.e_posta;
