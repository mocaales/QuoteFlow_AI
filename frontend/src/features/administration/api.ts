import type { SupabaseClient } from '@supabase/supabase-js';
import { api } from '../../services/api';
import type { Podjetje, ProsnjaAdmin } from '../identity/types';
import type { AdminRole, AdminUser, RoleInput } from './types';
export const getUsers = (client: SupabaseClient) => api<AdminUser[]>(client, '/admin/uporabniki');
export const getRoles = (client: SupabaseClient) => api<AdminRole[]>(client, '/admin/vloge');
export type CompanyInput = Omit<Podjetje, 'id'>;
export const saveCompany = (client: SupabaseClient, company: Podjetje | null, data: CompanyInput) => {
 const { lastnik_id, aktivno, ...details } = data;
 return api(client, company ? `/admin/podjetja/${company.id}` : '/admin/podjetja', company ? 'PUT' : 'POST', company ? { ...details, aktivno } : { ...details, lastnik_id });
};
export const assignRole = (client: SupabaseClient, data: RoleInput) => api(client, '/admin/vloge', 'POST', data);
export const setRoleActive = (client: SupabaseClient, id: string, active: boolean) => api(client, `/admin/vloge/${id}`, 'PATCH', { aktivna: active });
export const getApplications = (client: SupabaseClient) => api<ProsnjaAdmin[]>(client, '/admin/prosnje');
export const decideApplication = (client: SupabaseClient, id: string, approve: boolean) => api(client, `/admin/prosnje/${id}/odlocitev`, 'POST', { odobri: approve });
