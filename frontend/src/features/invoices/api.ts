import type { SupabaseClient } from '@supabase/supabase-js';
import { api } from '../../services/api';
import type { Invoice } from './types';
const base = (company: string, project: string) => `/podjetja/${company}/projekti/${project}/racun`;
export const getInvoice = (client: SupabaseClient, company: string, project: string) => api<Invoice>(client, base(company, project));
export const issueInvoice = (client: SupabaseClient, company: string, project: string, data: { prejemnik_naziv: string; prejemnik_naslov: string; zapade_dne: string }) => api<Invoice>(client, `${base(company, project)}/izdaj`, 'POST', data);
export const payInvoice = (client: SupabaseClient, company: string, project: string) => api<Invoice>(client, `${base(company, project)}/placilo`, 'POST');
export const getCustomerInvoice = (client: SupabaseClient, project: string) => api<Invoice>(client, `/projekti/${project}/racun`);
