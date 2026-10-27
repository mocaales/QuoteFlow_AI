import type { SupabaseClient } from '@supabase/supabase-js';
import { api } from '../../services/api';
import type { Podjetje, Uporabnik, Dodelitev } from '../identity/types';

export const getUsers = (client: SupabaseClient) => api<Uporabnik[]>(client, '/admin/uporabniki');
export const getRoles = (client: SupabaseClient) => api<Dodelitev[]>(client, '/admin/vloge');
export const saveCompany = (client: SupabaseClient, company: Podjetje | null, name: string, status: Podjetje['stanje']) =>
 api(client, company ? `/admin/podjetja/${company.id}` : '/admin/podjetja', company ? 'PUT' : 'POST', company ? { naziv: name, stanje: status } : { naziv: name });
export const assignRole = (client: SupabaseClient, data: Record<string, FormDataEntryValue>) => api(client, '/admin/vloge', 'POST', data);
export const setRoleActive = (client: SupabaseClient, id: string, active: boolean) => api(client, `/admin/vloge/${id}`, 'PATCH', { aktivna: active });
