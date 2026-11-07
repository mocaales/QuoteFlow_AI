import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { Session, SupabaseClient } from '@supabase/supabase-js';
import WorkspacePage from '../pages/WorkspacePage';
import { api, ApiError } from '../services/api';
vi.mock('../services/api', async importOriginal => ({ ...await importOriginal<typeof import('../services/api')>(), api: vi.fn() }));
const mockedApi=vi.mocked(api);
const client={} as SupabaseClient;
const session={access_token:'t',user:{email:'ana@example.test'}} as Session;
const inv={id:'p1',podjetje_id:'a',podjetje_naziv:'Gradnje d.o.o.',povabil:'Boris Kos',poslano_ob:'2026-11-06T09:00:00Z'};
let open:typeof inv[];let profileCalls:number;let failure:Error|null;
beforeEach(()=>{vi.clearAllMocks();open=[inv];profileCalls=0;failure=null;
 mockedApi.mockImplementation(async(_c,path,method)=>{
  if(path==='/me'){profileCalls++;return {id:'u1',e_posta:'ana@example.test',ime:'Ana',priimek:'Novak',vloge:[{id:'r0',naziv:null,vloga:'stranka',podjetje_id:null},...(open.length?[]:[{id:'r1',naziv:null,vloga:'delavec',podjetje_id:'a'}])]};}
  if(path==='/podjetja')return open.length?[]:[{id:'a',naziv:'Gradnje d.o.o.',aktivno:true}];
  if(path==='/povabila')return open;
  if(path==='/povabila/p1/odlocitev'){if(failure)throw failure;open=[];return {id:'p1',stanje:method==='POST'?'sprejeto':''};}
  return [];
 });
});
const show=async()=>{render(<WorkspacePage client={client} session={session}/>);return screen.findByRole('heading',{name:'Povabila v podjetja'});};
describe('Povabila v podjetja (Pregled)',()=>{
 it('kartica pokaže podjetje in povabitelja',async()=>{
  await show();expect(screen.getByText(/vas vabi kot delavca · povabil Boris Kos/)).toBeTruthy();expect(screen.getByText('Gradnje d.o.o.',{selector:'strong'})).toBeTruthy();
 });
 it('brez odprtih povabil kartice ni',async()=>{
  open=[];render(<WorkspacePage client={client} session={session}/>);await waitFor(()=>expect(screen.queryByText('Preverjam dostop …')).toBeNull());expect(screen.queryByText('Povabila v podjetja')).toBeNull();
 });
 it('sprejem pošlje sprejmi true in osveži pravice',async()=>{
  await show();await userEvent.click(screen.getByRole('button',{name:'Sprejmi povabilo podjetja Gradnje d.o.o.'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,'/povabila/p1/odlocitev','POST',{sprejmi:true}));
  await waitFor(()=>expect(profileCalls).toBeGreaterThan(1));expect((await screen.findByRole('status')).textContent).toContain('sprejeto');expect(screen.queryByText(/vas vabi/)).toBeNull();
 });
 it('zavrnitev najprej vpraša in šele nato pošlje sprejmi false',async()=>{
  await show();await userEvent.click(screen.getByRole('button',{name:'Zavrni povabilo podjetja Gradnje d.o.o.'}));
  expect(mockedApi.mock.calls.filter(c=>c[2]==='POST')).toHaveLength(0);
  await userEvent.click(within(screen.getByText(/Zavrnem povabilo/).parentElement!).getByRole('button',{name:'Zavrni povabilo'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,'/povabila/p1/odlocitev','POST',{sprejmi:false}));expect(profileCalls).toBe(1);
 });
 it('QFP34 sporočilo se prikaže',async()=>{
  failure=new ApiError('Povabila ni mogoče sprejeti.',409);await show();await userEvent.click(screen.getByRole('button',{name:'Sprejmi povabilo podjetja Gradnje d.o.o.'}));
  expect((await screen.findByRole('alert')).textContent).toBe('Povabila ni mogoče sprejeti.');
 });
});
