import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { SupabaseClient } from '@supabase/supabase-js';
import ProjectProgress from '../features/projects/components/ProjectProgress';
import ProjectsWorkspace from '../features/projects/components/ProjectsWorkspace';
import MyProjects from '../features/projects/components/MyProjects';
import { api } from '../services/api';
vi.mock('../services/api', () => ({ api: vi.fn() }));
const mockedApi=vi.mocked(api);
const client={} as SupabaseClient;
const M='/podjetja/a/projekti/p3';
const project=(more={})=>({id:'p3',naziv:'Nov estrih',opis:'Estrih 40 m2',lokacija_izvedbe:'Ptuj, Slovenska 3',faza:'termin',stranka_ime:'Janez',stranka_priimek:'Kranjc',stranka_e_posta:'janez@example.test',termin_od:null,termin_do:null,izvedba_koncana_ob:null,zakljuceno_ob:null,...more});
const scheduled=(more={})=>project({faza:'izvedba',termin_od:'2030-01-10T08:00:00Z',termin_do:'2030-01-12T16:00:00Z',...more});
let failure:Error|null;let onChange:ReturnType<typeof vi.fn<() => void>>;
beforeEach(()=>{vi.clearAllMocks();failure=null;onChange=vi.fn<() => void>();
 mockedApi.mockImplementation(async(_c,path,method)=>{
  if(method){if(failure)throw failure;return path.endsWith('/izvedba')?scheduled({izvedba_koncana_ob:'2030-01-12T16:30:00Z'}):scheduled();}
  return [];
 });
});
const open=(p=project())=>render(<ProjectProgress client={client} companyId="a" project={p} onChange={onChange}/>);
const fill=async(od:string,do_:string)=>{
 const start=screen.getByLabelText('Začetek termina'),end=screen.getByLabelText('Konec termina');
 await userEvent.clear(start);await userEvent.type(start,od);await userEvent.clear(end);await userEvent.type(end,do_);
};
describe('Potek projekta: termin in izvedba',()=>{
 it('pokaže vse faze in označi trenutno',()=>{
  open(scheduled());const steps=within(screen.getByRole('list',{name:'Faze projekta'})).getAllByRole('listitem');
  expect(steps.map(s=>s.textContent)).toEqual(['Pregled','Ogled','Ponudba','Termin','Izvedba','Obračun','Zaključen'].map(t=>expect.stringContaining(t)));
  expect(steps.filter(s=>s.getAttribute('aria-current')==='step').map(s=>s.textContent)).toEqual([expect.stringContaining('Izvedba')]);
 });
 it('v fazi termin ponudi obrazec za termin brez zaključka izvedbe',()=>{
  open();expect(screen.getByLabelText('Začetek termina')).toBeTruthy();expect(screen.getByLabelText('Konec termina')).toBeTruthy();
  expect(screen.getByRole('button',{name:'Potrdi termin'})).toBeTruthy();expect(screen.queryByRole('button',{name:'Zaključi izvedbo'})).toBeNull();
 });
 it('potrditev termina pošlje PUT z ISO časoma, osveži in sporoči nadrejenemu',async()=>{
  open();await fill('2030-01-10T08:00','2030-01-12T16:00');await userEvent.click(screen.getByRole('button',{name:'Potrdi termin'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,M+'/termin','PUT',{termin_od:new Date('2030-01-10T08:00').toISOString(),termin_do:new Date('2030-01-12T16:00').toISOString()}));
  expect(await screen.findByRole('button',{name:'Zaključi izvedbo'})).toBeTruthy();expect(onChange).toHaveBeenCalled();
 });
 it('konec pred začetkom ali enak začetku se zavrne brez klica',async()=>{
  open();for(const end of ['2030-01-10T08:00','2030-01-09T08:00']){
   await fill('2030-01-10T08:00',end);await userEvent.click(screen.getByRole('button',{name:'Potrdi termin'}));
   expect((await screen.findByRole('alert')).textContent).toContain('Konec termina mora biti po začetku.');
  }
  expect(mockedApi.mock.calls.some(c=>c[2]==='PUT')).toBe(false);
 });
 it('prazen termin se zavrne brez klica',async()=>{
  open();await userEvent.click(screen.getByRole('button',{name:'Potrdi termin'}));expect(mockedApi.mock.calls.some(c=>c[2]==='PUT')).toBe(false);
 });
 it('napaka strežnika se pokaže in faza ostane termin',async()=>{
  failure=new Error('Termin se ne sme začeti v preteklosti.');open();await fill('2020-01-10T08:00','2020-01-12T16:00');await userEvent.click(screen.getByRole('button',{name:'Potrdi termin'}));
  expect((await screen.findByRole('alert')).textContent).toContain('Termin se ne sme začeti v preteklosti.');expect(screen.queryByRole('button',{name:'Zaključi izvedbo'})).toBeNull();expect(onChange).not.toHaveBeenCalled();
 });
 it('v izvedbi je termin predizpolnjen in ga je mogoče prestaviti',async()=>{
  open(scheduled());expect((screen.getByLabelText('Začetek termina') as HTMLInputElement).value).not.toBe('');
  await fill('2030-02-01T08:00','2030-02-02T16:00');await userEvent.click(screen.getByRole('button',{name:'Potrdi termin'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,M+'/termin','PUT',expect.objectContaining({termin_od:new Date('2030-02-01T08:00').toISOString()})));
 });
 it('zaključek izvedbe pošlje POST brez telesa in skrije obrazce',async()=>{
  open(scheduled());await userEvent.click(screen.getByRole('button',{name:'Zaključi izvedbo'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,M+'/izvedba','POST'));
  expect((await screen.findAllByText(/Izvedba je zaključena/)).length).toBeGreaterThan(0);
  for(const name of ['Zaključi izvedbo','Potrdi termin'])expect(screen.queryByRole('button',{name})).toBeNull();expect(screen.queryByLabelText('Začetek termina')).toBeNull();expect(onChange).toHaveBeenCalled();
 });
 it('napaka pri zaključku (termin še ni začel) se pokaže in izvedba ostane odprta',async()=>{
  failure=new Error('Izvedbe ni mogoče zaključiti pred začetkom termina.');open(scheduled());await userEvent.click(screen.getByRole('button',{name:'Zaključi izvedbo'}));
  expect((await screen.findByRole('alert')).textContent).toContain('pred začetkom termina');expect(screen.getByRole('button',{name:'Zaključi izvedbo'})).toBeTruthy();
 });
 it('že zaključena izvedba nima obrazcev',()=>{
  open(scheduled({izvedba_koncana_ob:'2030-01-12T16:30:00Z'}));expect(screen.getAllByText(/Izvedba je zaključena/).length).toBeGreaterThan(0);
  expect(screen.queryByRole('button',{name:'Zaključi izvedbo'})).toBeNull();expect(screen.queryByRole('button',{name:'Potrdi termin'})).toBeNull();
 });
 it.each(['pregled','ogled','ponudba'])('v fazi %s termina še ni mogoče določiti',faza=>{
  open(project({faza}));expect(screen.queryByLabelText('Začetek termina')).toBeNull();expect(screen.queryByRole('button',{name:'Potrdi termin'})).toBeNull();expect(screen.getAllByText(/po sprejeti ponudbi/i).length).toBeGreaterThan(0);
 });
 it.each(['obracun','zakljucen'])('v fazi %s je termin samo za branje',faza=>{
  open(scheduled({faza,izvedba_koncana_ob:'2030-01-12T16:30:00Z'}));
  for(const name of ['Potrdi termin','Zaključi izvedbo'])expect(screen.queryByRole('button',{name})).toBeNull();expect(screen.queryByLabelText('Začetek termina')).toBeNull();
 });
});
describe('Sestava: potek in račun v delovnem prostoru mojstra',()=>{
 const list=[project({id:'p1',naziv:'Obnova kopalnice',faza:'pregled'}),scheduled({id:'p3',naziv:'Nov estrih'}),project({id:'p4',naziv:'Beljenje',faza:'obracun',termin_od:'2030-01-10T08:00:00Z',termin_do:'2030-01-11T08:00:00Z',izvedba_koncana_ob:'2030-01-11T09:00:00Z'})];
 beforeEach(()=>{mockedApi.mockImplementation(async(_c,path)=>path==='/podjetja/a/projekti'?list:[]);});
 const view=()=>render(<ProjectsWorkspace client={client} companyId="a" renderProgress={(p,refresh)=><button type="button" onClick={refresh}>Potek {p.naziv}</button>} renderInvoice={p=><p>Račun projekta {p.naziv}</p>}/>);
 it('gumb Izvedba je pri projektih od faze termin naprej in odpre potek',async()=>{
  view();expect(await screen.findByText('Nov estrih')).toBeTruthy();
  expect(screen.queryByRole('button',{name:'Izvedba Obnova kopalnice'})).toBeNull();
  await userEvent.click(screen.getByRole('button',{name:'Izvedba Nov estrih'}));
  expect(await screen.findByRole('button',{name:'Potek Nov estrih'})).toBeTruthy();expect(screen.getByRole('button',{name:'Nazaj na projekte'})).toBeTruthy();
 });
 it('gumb Račun je pri projektih od faze termin naprej in odpre račun',async()=>{
  view();await screen.findByText('Beljenje');expect(screen.queryByRole('button',{name:'Račun Obnova kopalnice'})).toBeNull();
  await userEvent.click(screen.getByRole('button',{name:'Račun Beljenje'}));expect(await screen.findByText('Račun projekta Beljenje')).toBeTruthy();
 });
 it('osvežitev iz poteka znova naloži projekte',async()=>{
  view();await userEvent.click(await screen.findByRole('button',{name:'Izvedba Nov estrih'}));const before=mockedApi.mock.calls.filter(c=>c[1]==='/podjetja/a/projekti').length;
  await userEvent.click(await screen.findByRole('button',{name:'Potek Nov estrih'}));
  await waitFor(()=>expect(mockedApi.mock.calls.filter(c=>c[1]==='/podjetja/a/projekti').length).toBeGreaterThan(before));
 });
});
describe('Moji projekti: račun in termin stranke',()=>{
 const own=(id:string,naziv:string,faza:string,more={})=>({id,naziv,opis:'O',lokacija_izvedbe:'Maribor',faza,podjetje_naziv:'Mojster Novak d.o.o.',termin_od:null,termin_do:null,izvedba_koncana_ob:null,zakljuceno_ob:null,...more});
 beforeEach(()=>{mockedApi.mockImplementation(async(_c,path)=>path==='/projekti'?[own('p1','Menjava oken','ponudba'),own('p2','Nov estrih','izvedba',{termin_od:'2030-01-10T08:00:00Z',termin_do:'2030-01-12T16:00:00Z'}),own('p3','Beljenje','obracun'),own('p4','Parket','zakljucen')]:[]);});
 it('termin je viden v tabeli',async()=>{
  render(<MyProjects client={client}/>);const row=(await screen.findByText('Nov estrih')).closest('tr')!;expect(row.textContent).toMatch(/2030/);
  expect(within(screen.getByText('Menjava oken').closest('tr')!).getByText('—')).toBeTruthy();
 });
 it('gumb Račun je samo pri izdanih računih (obračun, zaključen) in odpre račun',async()=>{
  render(<MyProjects client={client} renderInvoice={p=><p>Račun stranke {p.naziv}</p>}/>);await screen.findByText('Nov estrih');
  for(const n of ['Menjava oken','Nov estrih'])expect(screen.queryByRole('button',{name:`Račun ${n}`})).toBeNull();
  expect(screen.getByRole('button',{name:'Račun Parket'})).toBeTruthy();
  await userEvent.click(screen.getByRole('button',{name:'Račun Beljenje'}));expect(await screen.findByText('Račun stranke Beljenje')).toBeTruthy();expect(screen.getByRole('button',{name:'Nazaj na projekte'})).toBeTruthy();
 });
 it('brez renderInvoice gumba Račun ni',async()=>{
  render(<MyProjects client={client}/>);await screen.findByText('Beljenje');expect(screen.queryByRole('button',{name:/^Račun /})).toBeNull();
 });
});
