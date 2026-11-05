import type { SupabaseClient } from '@supabase/supabase-js';
import { api } from '../../services/api';
import type { Profil, Podjetje, Prosnja, ProsnjaVnos } from './types';

export const getProfile = (client: SupabaseClient) => api<Profil>(client, '/me');
export const getCompanies = (client: SupabaseClient) => api<Podjetje[]>(client, '/podjetja');
export const getApplications = (client: SupabaseClient) => api<Prosnja[]>(client, '/prosnje');
export const submitApplication = (client: SupabaseClient, data: ProsnjaVnos) => api<Prosnja>(client, '/prosnje', 'POST', data);
