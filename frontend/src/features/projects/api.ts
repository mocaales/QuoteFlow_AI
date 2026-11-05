import type { SupabaseClient } from '@supabase/supabase-js';
import { api } from '../../services/api';
import type { OwnProject, Project, ProjectCreate, ProjectInput } from './types';
const base = (company: string) => `/podjetja/${company}/projekti`;
export const getProjects = (client: SupabaseClient, company: string) => api<Project[]>(client, base(company));
export const createProject = (client: SupabaseClient, company: string, data: ProjectCreate) => api<Project>(client, base(company), 'POST', data);
export const updateProject = (client: SupabaseClient, company: string, id: string, data: ProjectInput) => api<Project>(client, `${base(company)}/${id}`, 'PUT', data);
export const requestSurvey = (client: SupabaseClient, company: string, id: string) => api(client, `${base(company)}/${id}/ogled`, 'POST');
export const getOwnProjects = (client: SupabaseClient) => api<OwnProject[]>(client, '/projekti');
