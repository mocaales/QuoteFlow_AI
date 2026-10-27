import type { SupabaseClient } from '@supabase/supabase-js';
import { api } from '../../services/api';
import type { Profil, Podjetje } from './types';

export const getProfile = (client: SupabaseClient) => api<Profil>(client, '/me');
export const getCompanies = (client: SupabaseClient) => api<Podjetje[]>(client, '/podjetja');
