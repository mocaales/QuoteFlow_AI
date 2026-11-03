import type { SupabaseClient } from '@supabase/supabase-js';
import { api } from '../../services/api';
import type { CatalogInput, CatalogItem, RulesInput, SalesRules } from './types';
const base = (company: string) => `/podjetja/${company}`;
export const getCatalog = (client: SupabaseClient, company: string) => api<CatalogItem[]>(client, base(company) + '/cenik');
export const getRules = (client: SupabaseClient, company: string) => api<SalesRules[]>(client, base(company) + '/pravila');
export const saveCatalogItem = (client: SupabaseClient, company: string, data: CatalogInput, id?: string) =>
 api<CatalogItem>(client, base(company) + '/cenik' + (id ? `/${id}` : ''), id ? 'PUT' : 'POST', data);
export const confirmCatalogItem = (client: SupabaseClient, company: string, id: string) => api<CatalogItem>(client, base(company) + `/cenik/${id}/potrditev`, 'POST');
export const saveStock = (client: SupabaseClient, company: string, id: string, quantity: string) => api(client, base(company) + `/cenik/${id}/zaloga`, 'PUT', { razpolozljiva_kolicina: quantity });
export const removeStock = (client: SupabaseClient, company: string, id: string) => api(client, base(company) + `/cenik/${id}/zaloga`, 'DELETE');
export const createRules = (client: SupabaseClient, company: string, data: RulesInput) => api<SalesRules>(client, base(company) + '/pravila', 'POST', data);
