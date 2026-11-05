import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { Session, SupabaseClient } from '@supabase/supabase-js';
import WorkspacePage from '../pages/WorkspacePage';
import { api } from '../services/api';
vi.mock('../services/api', () => ({ api: vi.fn() }));
const mockedApi=vi.mocked(api);
const client={} as SupabaseClient;
const session={access_token:'token',user:{email:'ana@example.test'}} as Session;
const p=(id:string,naziv:string,faza:string,more={})=>({id,naziv,opis:'Opis dela',lokacija_izvedbe:'Maribor, Glavni trg 1',faza,stranka_ime:'Janez',stranka_priimek:'Kranjc',stranka_e_posta:'janez@example.test',termin_od:null,termin_do:null,...more});
const mojster={id:'u',e_posta:'ana@example.test',ime:'Ana',priimek:'Novak',vloge:[{id:'r',podjetje_id:'a',vloga:'mojster',naziv:'A'},{id:'s',podjetje_id:null,vloga:'stranka',naziv:null}]};
const stranka={...mojster,vloge:[{id:'s',podjetje_id:null,vloga:'stranka',naziv:null}]};
let me:unknown;let projects:unknown[];let failure:Error|null;
beforeEach(()=>{vi.clearAllMocks();me=mojster;failure=null;
 projects=[p('1','Obnova kopalnice','pregled'),p('2','Menjava oken','ponudba',{lokacija_izvedbe:'Celje, Cesta 5'})];
 mockedApi.mockImplementation(async(_c,path,method)=>{
  if(path==='/me')return me;
  if(path==='/podjetja')return [{id:'a',naziv:'A',aktivno:true}];
  if(path==='/podjetja/a/projekti'&&!method)return projects;
  if(path==='/projekti')return [{id:'1',naziv:'Obnova kopalnice',opis:'x',lokacija_izvedbe:'Ptuj, Slovenska 3',faza:'ogled',podjetje_naziv:'Mojster Novak d.o.o.',termin_od:null,termin_do:null}];
  if(path.startsWith('/podjetja/a/projekti')){if(failure)throw failure;return p('3','Novo','pregled');}
  return [];
 });
});
async function go(name:string){render(<WorkspacePage client={client} session={session}/>);
 const nav=await screen.findByRole('navigation',{name:'Glavna navigacija'});await userEvent.click(await within(nav).findByRole('button',{name}));}
describe('Projekti mojstra',()=>{
 it('seznam združi projekte po fazah in pokaže stranko ter lokacijo',async()=>{
  await go('Projekti');
  expect(await screen.findByRole('heading',{name:'Pregled'})).toBeTruthy();expect(screen.getByRole('heading',{name:'Ponudba'})).toBeTruthy();
  expect(screen.queryByRole('heading',{name:'Izvedba'})).toBeNull();
  expect(screen.getByText('Obnova kopalnice')).toBeTruthy();expect(screen.getAllByText(/janez@example.test/).length).toBe(2);expect(screen.getByText('Celje, Cesta 5')).toBeTruthy();
 });
 it('ustvari projekt s prirezanim telom zahtevka',async()=>{
  await go('Projekti');await screen.findByText('Obnova kopalnice');
  await userEvent.type(screen.getByLabelText('E-pošta stranke'),'  janez@example.test ');await userEvent.type(screen.getByLabelText('Naziv'),'Nov strop');
  await userEvent.type(screen.getByLabelText('Lokacija izvedbe'),'Kranj');await userEvent.type(screen.getByLabelText('Opis'),'Knauf');
  await userEvent.click(screen.getByRole('button',{name:'Ustvari projekt'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,'/podjetja/a/projekti','POST',{e_posta_stranke:'janez@example.test',naziv:'Nov strop',opis:'Knauf',lokacija_izvedbe:'Kranj'}));
 });
 it('pri neregistrirani stranki pokaže napako QFP06',async()=>{
  failure=new Error('Uporabnik s tem e-poštnim naslovom ni registrirana stranka.');
  await go('Projekti');await screen.findByText('Obnova kopalnice');
  await userEvent.type(screen.getByLabelText('E-pošta stranke'),'x@example.test');await userEvent.type(screen.getByLabelText('Naziv'),'Nov');await userEvent.type(screen.getByLabelText('Lokacija izvedbe'),'Kranj');
  await userEvent.click(screen.getByRole('button',{name:'Ustvari projekt'}));
  expect((await screen.findByRole('alert')).textContent).toContain('Uporabnik s tem e-poštnim naslovom ni registrirana stranka.');
 });
 it('uredi projekt in pošlje PUT brez e-pošte stranke',async()=>{
  await go('Projekti');await userEvent.click(await screen.findByRole('button',{name:/Uredi Obnova kopalnice/}));
  const naziv=screen.getByLabelText('Naziv') as HTMLInputElement;expect(naziv.value).toBe('Obnova kopalnice');
  await userEvent.clear(naziv);await userEvent.type(naziv,'Obnova kopalnice 2');
  await userEvent.click(screen.getByRole('button',{name:/Shrani projekt/}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,'/podjetja/a/projekti/1','PUT',{naziv:'Obnova kopalnice 2',opis:'Opis dela',lokacija_izvedbe:'Maribor, Glavni trg 1'}));
 });
 it('zahtevaj ogled je samo pri projektu v fazi pregled in pokliče POST',async()=>{
  await go('Projekti');await screen.findByText('Menjava oken');
  expect(screen.queryByRole('button',{name:'Zahtevaj ogled Menjava oken'})).toBeNull();
  await userEvent.click(screen.getByRole('button',{name:'Zahtevaj ogled Obnova kopalnice'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,'/podjetja/a/projekti/1/ogled','POST'));
 });
 it('pri QFP07 pokaže napako o fazi projekta',async()=>{
  failure=new Error('V tej fazi projekta to dejanje ni dovoljeno.');
  await go('Projekti');await userEvent.click(await screen.findByRole('button',{name:'Zahtevaj ogled Obnova kopalnice'}));
  expect((await screen.findByRole('alert')).textContent).toContain('V tej fazi projekta to dejanje ni dovoljeno.');
 });
});
describe('Moji projekti (stranka)',()=>{
 it('stranka vidi samo bralni seznam brez urejanja in ogleda',async()=>{
  me=stranka;await go('Moji projekti');
  expect(await screen.findByText('Obnova kopalnice')).toBeTruthy();expect(screen.getByText('Mojster Novak d.o.o.')).toBeTruthy();expect(screen.getByText('Ptuj, Slovenska 3')).toBeTruthy();
  expect(screen.getByText('Ogled')).toBeTruthy();
  expect(screen.queryByRole('button',{name:/Uredi|Zahtevaj ogled|Ustvari projekt/})).toBeNull();expect(screen.queryByRole('button',{name:'Projekti'})).toBeNull();
  expect(mockedApi).toHaveBeenCalledWith(client,'/projekti');
 });
});
