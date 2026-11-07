import type { SupabaseClient } from '@supabase/supabase-js';
import { api } from '../../services/api';
import type { CatalogInput, CatalogItem, Material, MaterialInput, MaterialKind, Stock, WorkType, WorkTypeInput, WorkTypeMaterial, WorkTypeSaved } from './types';
const base = (company: string) => `/podjetja/${company}`;
export const getCatalog = (client: SupabaseClient, company: string) => api<CatalogItem[]>(client, base(company) + '/cenik');
export const saveCatalogItem = (client: SupabaseClient, company: string, data: CatalogInput, id?: string) => api<CatalogItem>(client, base(company) + '/cenik' + (id ? `/${id}` : ''), id ? 'PUT' : 'POST', data);
export const getMaterialKinds = (client: SupabaseClient, company: string) => api<MaterialKind[]>(client, base(company) + '/vrste-materiala');
export const saveMaterialKind = (client: SupabaseClient, company: string, naziv: string) => api(client, base(company) + '/vrste-materiala', 'POST', { naziv });
export const getMaterials = async (client: SupabaseClient, company: string) => {
 const materials = await api<Material[]>(client, base(company) + '/materiali');
 return Promise.all(materials.map(async material => ({ ...material, zaloge: await api<Stock[]>(client, base(company) + `/materiali/${material.id}/zaloga`) })));
};
export const saveMaterial = (client: SupabaseClient, company: string, data: MaterialInput, id?: string) => api(client, base(company) + '/materiali' + (id ? `/${id}` : ''), id ? 'PUT' : 'POST', data);
export const saveStock = (client: SupabaseClient, company: string, id: string, lokacija: string, kolicina: string) => api(client, base(company) + `/materiali/${id}/zaloga`, 'PUT', { lokacija, kolicina });
export const removeStock = (client: SupabaseClient, company: string, id: string, lokacija: string) => api(client, base(company) + `/materiali/${id}/zaloga?lokacija=${encodeURIComponent(lokacija)}`, 'DELETE');
export const getWorkTypes = (client: SupabaseClient, company: string) => api<WorkType[]>(client, base(company) + '/vrste-dela');
export const saveWorkType = (client: SupabaseClient, company: string, data: WorkTypeInput, id?: string) => api<WorkTypeSaved>(client, base(company) + '/vrste-dela' + (id ? `/${id}` : ''), id ? 'PUT' : 'POST', data);
export const saveWorkTypeMaterial = (client: SupabaseClient, company: string, work: string, material: string, kolicina_na_enoto: string) => api<WorkTypeMaterial>(client, base(company) + `/vrste-dela/${work}/materiali/${material}`, 'PUT', { kolicina_na_enoto });
export const removeWorkTypeMaterial = (client: SupabaseClient, company: string, work: string, material: string) => api(client, base(company) + `/vrste-dela/${work}/materiali/${material}`, 'DELETE');
