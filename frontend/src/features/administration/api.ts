import type { SupabaseClient } from '@supabase/supabase-js';
import { api } from '../../services/api';
import type { Podjetje, Uporabnik, Dodelitev } from '../identity/types';
export const getUsers = (client: SupabaseClient) => api<Uporabnik[]>(client, '/admin/uporabniki');
export const getRoles = (client: SupabaseClient) => api<Dodelitev[]>(client, '/admin/vloge');
export type CompanyInput = Omit<Podjetje, 'id'>;
export const saveCompany = (client: SupabaseClient, company: Podjetje | null, data: CompanyInput) => {
 const { lastnik_id, aktivno, ...details } = data;
 return api(client, company ? `/admin/podjetja/${company.id}` : '/admin/podjetja', company ? 'PUT' : 'POST', company ? { ...details, aktivno } : { ...details, lastnik_id });
};
export const assignRole = (client: SupabaseClient, data: Record<string, unknown>) => api(client, '/admin/vloge', 'POST', data);
export const setRoleActive = (client: SupabaseClient, id: string, active: boolean) => api(client, `/admin/vloge/${id}`, 'PATCH', { aktivna: active });
