import type { SupabaseClient } from '@supabase/supabase-js';
import { api } from '../../services/api';
import type { CatalogOption, WorkTypeOption, CatalogItemInput, ItemsOverview, ItemInput, ItemSaved, Measure, MeasureInput } from './types';
const base = (company: string, project: string) => `/podjetja/${company}/projekti/${project}/postavke`;
// Red test pins { postavke, neto, ddv, skupaj }; backend GET currently returns Item[] (drift, reported)
export const getItems = (client: SupabaseClient, company: string, project: string) => api<ItemsOverview>(client, base(company, project));
export const createItem = (client: SupabaseClient, company: string, project: string, data: ItemInput) => api<ItemSaved>(client, base(company, project), 'POST', data);
export const addItemFromCatalog = (client: SupabaseClient, company: string, project: string, data: CatalogItemInput) => api<ItemSaved>(client, base(company, project) + '/iz-cenika', 'POST', data);
export const updateItem = (client: SupabaseClient, company: string, project: string, id: string, data: ItemInput) => api<ItemSaved>(client, `${base(company, project)}/${id}`, 'PUT', data);
export const deleteItem = (client: SupabaseClient, company: string, project: string, id: string) => api(client, `${base(company, project)}/${id}`, 'DELETE');
export const addMeasure = (client: SupabaseClient, company: string, project: string, item: string, data: MeasureInput) => api<Measure>(client, `${base(company, project)}/${item}/izmere`, 'POST', data);
export const updateMeasure = (client: SupabaseClient, company: string, project: string, item: string, id: string, data: MeasureInput) => api<Measure>(client, `${base(company, project)}/${item}/izmere/${id}`, 'PUT', data);
export const deleteMeasure = (client: SupabaseClient, company: string, project: string, item: string, id: string) => api(client, `${base(company, project)}/${item}/izmere/${id}`, 'DELETE');
// Read-only pickers for the item forms (same endpoints as the supplier feature; features do not import each other)
export const getWorkTypes = (client: SupabaseClient, company: string) => api<WorkTypeOption[]>(client, `/podjetja/${company}/vrste-dela`);
export const getCatalogOptions = (client: SupabaseClient, company: string) => api<CatalogOption[]>(client, `/podjetja/${company}/cenik`);
