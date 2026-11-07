import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { SupabaseClient } from '@supabase/supabase-js';
import CustomerQuote from '../features/quotes/components/CustomerQuote';
import MyProjects from '../features/projects/components/MyProjects';
import { api } from '../services/api';
vi.mock('../services/api', () => ({ api: vi.fn() }));
const mockedApi=vi.mocked(api);
const client={} as SupabaseClient;
const L='/projekti/p1/ponudbe',D=L+'/q1/odlocitev';
const line=(more={})=>({zaporedje:1,naziv:'Rušenje estriha',opis:'Odvoz',vrsta_dela:'Rušenje',enota:'m2',cena_na_enoto:'100.0000',kolicina:'2.0000',popust:'0.100000',stopnja_ddv:'0.220000',neto:'180.00',ddv:'39.60',koncna_cena:'219.60',...more});
const quote=(more={})=>({id:'q1',stevilka:'P-2026-001',razlicica:1,stanje:'poslana',poslano_ob:'2026-11-06T09:00:00Z',odgovorjeno_ob:null,velja_do:'2099-12-31',nadomescena:false,neto:'180.00',ddv:'39.60',skupaj:'219.60',podjetje_naziv:'Mojster Novak d.o.o.',postavke:[line()],ddv_po_stopnjah:[{stopnja_ddv:'0.220000',osnova:'180.00',ddv:'39.60'}],...more});
let list:unknown[];let failure:Error|null;let loadError:Error|null;
beforeEach(()=>{vi.clearAllMocks();failure=null;loadError=null;list=[quote()];
 mockedApi.mockImplementation(async(_c,path,method)=>{
  if(method==='POST'){if(failure)throw failure;list=[quote({stanje:'sprejeta',odgovorjeno_ob:'2026-11-07T10:00:00Z'})];return list[0];}
  if(path===L){if(loadError)throw loadError;return list;}
  return [];
 });
});
const open=()=>render(<CustomerQuote client={client} projectId="p1"/>);
const decisions=()=>['Sprejmi ponudbo','Zavrni ponudbo'].map(name=>screen.queryByRole('button',{name}));
describe('Ponudba za stranko',()=>{
 it('poslana ponudba pokaže izvajalca, številko, postavke in vsote v evrih',async()=>{
  open();expect(await screen.findByRole('heading',{name:/P-2026-001/})).toBeTruthy();expect(screen.getAllByText(/Mojster Novak d\.o\.o\./).length).toBeGreaterThan(0);
  expect(screen.getByText('Rušenje estriha')).toBeTruthy();
  const totals=screen.getByRole('group',{name:'Vsote ponudbe'});
  expect(totals.textContent).toMatch(/180,00\s?€/);expect(totals.textContent).toMatch(/39,60\s?€/);expect(totals.textContent).toMatch(/219,60\s?€/);
  expect(mockedApi).toHaveBeenCalledWith(client,L);
 });
 it('poslana ponudba ponuja sprejem in zavrnitev, ne pa urejanja',async()=>{
  open();await screen.findByText('Rušenje estriha');expect(decisions().every(Boolean)).toBe(true);
  expect(screen.queryByRole('button',{name:/Pošlji stranki|Dodaj|Odstrani|Pripravi novo/})).toBeNull();
 });
 it('sprejem zahteva potrditev in šele nato pošlje odločitev',async()=>{
  open();await userEvent.click(await screen.findByRole('button',{name:'Sprejmi ponudbo'}));
  expect(mockedApi.mock.calls.some(c=>c[2]==='POST')).toBe(false);
  await userEvent.click(await screen.findByRole('button',{name:'Potrdi sprejem'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,D,'POST',{sprejmi:true}));
 });
 it('zavrnitev zahteva potrditev in pošlje sprejmi false',async()=>{
  open();await userEvent.click(await screen.findByRole('button',{name:'Zavrni ponudbo'}));
  expect(mockedApi.mock.calls.some(c=>c[2]==='POST')).toBe(false);
  await userEvent.click(await screen.findByRole('button',{name:'Potrdi zavrnitev'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,D,'POST',{sprejmi:false}));
 });
 it('preklic potrditve ne pošlje ničesar',async()=>{
  open();await userEvent.click(await screen.findByRole('button',{name:'Sprejmi ponudbo'}));
  await userEvent.click(await screen.findByRole('button',{name:'Prekliči'}));
  expect(mockedApi.mock.calls.some(c=>c[2]==='POST')).toBe(false);expect(screen.queryByRole('button',{name:'Potrdi sprejem'})).toBeNull();expect(screen.getByRole('button',{name:'Sprejmi ponudbo'})).toBeTruthy();
 });
 it('po sprejemu ponudbo osveži in pokaže sprejeto stanje brez gumbov',async()=>{
  open();await userEvent.click(await screen.findByRole('button',{name:'Sprejmi ponudbo'}));await userEvent.click(await screen.findByRole('button',{name:'Potrdi sprejem'}));
  expect((await screen.findAllByText('Sprejeta')).length).toBeGreaterThan(0);expect(decisions()).toEqual([null,null]);
  expect(screen.queryByRole('button',{name:/Potrdi/})).toBeNull();
 });
 it('napaka odločitve se pokaže in ponudba ostane odprta',async()=>{
  failure=new Error('O tej ponudbi ni več mogoče odločati.');
  open();await userEvent.click(await screen.findByRole('button',{name:'Zavrni ponudbo'}));await userEvent.click(await screen.findByRole('button',{name:'Potrdi zavrnitev'}));
  expect((await screen.findByRole('alert')).textContent).toContain('O tej ponudbi ni več mogoče odločati.');expect(screen.queryByText('Zavrnjena')).toBeNull();
 });
 it('sprejeta in zavrnjena ponudba nimata gumbov za odločitev',async()=>{
  for(const [stanje,label] of [['sprejeta','Sprejeta'],['zavrnjena','Zavrnjena']]){
   list=[quote({stanje,odgovorjeno_ob:'2026-11-07T10:00:00Z'})];const view=open();
   expect((await screen.findAllByText(label)).length).toBeGreaterThan(0);expect(decisions()).toEqual([null,null]);view.unmount();
  }
 });
 it('nadomeščena ponudba nima gumbov in opozori na novejšo različico',async()=>{
  list=[quote({nadomescena:true})];open();await screen.findByText('Rušenje estriha');
  expect(screen.getAllByText(/nadomeščena/i).length).toBeGreaterThan(0);expect(decisions()).toEqual([null,null]);
 });
 it('ob več različicah je za odločanje odprta najnovejša',async()=>{
  list=[quote({nadomescena:true}),quote({id:'q2',razlicica:2,postavke:[line({naziv:'Nova postavka'})]})];open();
  expect(await screen.findByText('Nova postavka')).toBeTruthy();expect(screen.queryByText('Rušenje estriha')).toBeNull();expect(screen.getAllByText(/različica 2/i).length).toBeGreaterThan(0);
  await userEvent.click(screen.getByRole('button',{name:'Sprejmi ponudbo'}));await userEvent.click(await screen.findByRole('button',{name:'Potrdi sprejem'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,L+'/q2/odlocitev','POST',{sprejmi:true}));
 });
 it('potekla ponudba nima gumbov in to pove',async()=>{
  list=[quote({velja_do:'2020-01-01'})];open();await screen.findByText('Rušenje estriha');
  expect(screen.getAllByText(/potekla/i).length).toBeGreaterThan(0);expect(decisions()).toEqual([null,null]);
 });
 it('brez poslane ponudbe pove, da je še ni',async()=>{
  list=[];open();expect((await screen.findAllByText(/še ni poslalo ponudbe/i)).length).toBeGreaterThan(0);expect(decisions()).toEqual([null,null]);
 });
 it('napaka pri nalaganju ne pokaže praznega stanja',async()=>{
  loadError=new Error('Podatkovna baza trenutno ni na voljo.');open();
  expect((await screen.findByRole('alert')).textContent).toContain('Podatkovna baza trenutno ni na voljo.');expect(screen.queryByText(/še ni poslalo ponudbe/i)).toBeNull();
 });
 it('materialov in notranjih podatkov ne prikazuje',async()=>{
  open();await screen.findByText('Rušenje estriha');expect(screen.queryByText(/Material/)).toBeNull();
 });
});
describe('Moji projekti: ponudba',()=>{
 const own=(id:string,naziv:string,faza:string)=>({id,naziv,opis:'O',lokacija_izvedbe:'Maribor',faza,podjetje_naziv:'Mojster Novak d.o.o.',termin_od:null,termin_do:null});
 it('gumb Ponudba je pri projektih od faze ponudba naprej in odpre ponudbo stranke',async()=>{
  mockedApi.mockImplementation(async(_c,path)=>path==='/projekti'?[own('p0','Obnova kopalnice','pregled'),own('p1','Menjava oken','ponudba'),own('p2','Nov estrih','izvedba')]:path===L?[quote()]:[]);
  render(<MyProjects client={client} renderQuote={p=>(<CustomerQuote client={client} projectId={p.id}/>)}/>);
  expect(await screen.findByText('Menjava oken')).toBeTruthy();
  expect(screen.queryByRole('button',{name:'Ponudba Obnova kopalnice'})).toBeNull();expect(screen.getByRole('button',{name:'Ponudba Nov estrih'})).toBeTruthy();
  await userEvent.click(screen.getByRole('button',{name:'Ponudba Menjava oken'}));
  expect(await screen.findByRole('heading',{name:/P-2026-001/})).toBeTruthy();expect(mockedApi).toHaveBeenCalledWith(client,L);
 });
});
// Model v3: stranka vidi izmere poslane različice (izmera_ponudbe), nikoli dela, ur, delavcev ali materialov.
describe('Ponudba za stranko: izmere',()=>{
 const m=(zaporedje:number,odstej:boolean,dolzina:string,visina:string,vrednost:string)=>({zaporedje,odstej,kosi:'1.0000',dolzina,visina,sirina:null,vrednost});
 const v3=(more={})=>line({naziv:'Polaganje keramike',vrsta_dela:'Keramika',enota:'m2',cena_na_enoto:'10.0000',kolicina:'1.0000',popust:'0.100000',neto:'540.00',ddv:'118.80',koncna_cena:'658.80',izmera_skupaj:'20.0000',
  izmere:[m(1,false,'5.0000','4.0000','20.0000'),m(2,false,'2.0000','1.0000','2.0000'),m(3,true,'1.0000','2.0000','2.0000')],...more});
 const send=(more={})=>quote({neto:'540.00',ddv:'118.80',skupaj:'658.80',postavke:[v3(more)],ddv_po_stopnjah:[{stopnja_ddv:'0.220000',osnova:'540.00',ddv:'118.80'}]});
 it('pri postavki našteje izmere z znakom + ali − in pokaže skupno izmero',async()=>{
  list=[send()];open();await screen.findByText('Polaganje keramike');
  const items=within(screen.getByRole('list',{name:'Izmere Polaganje keramike'})).getAllByRole('listitem');expect(items).toHaveLength(3);
  expect(items[0].textContent).toMatch(/\+\s?20\s?m²/);expect(items[0].textContent).toMatch(/5\s?×\s?4/);expect(items[1].textContent).toMatch(/\+\s?2\s?m²/);expect(items[2].textContent).toMatch(/−\s?2\s?m²/);
  expect(screen.getByText(/Skupaj izmer/).parentElement!.textContent).toMatch(/20\s?m²/);
 });
 it('vsote ostanejo 540,00 / 118,80 / 658,80 € in zunanji klic je samo seznam ponudb',async()=>{
  list=[send()];open();await screen.findByText('Polaganje keramike');const t=screen.getByRole('group',{name:'Vsote ponudbe'}).textContent!;
  for(const a of ['540,00','118,80','658,80'])expect(t).toMatch(new RegExp(a.replace('.','\\.')+'\\s?€'));expect(mockedApi.mock.calls.map(c=>c[1])).toEqual([L]);
 });
 it('tudi če strežnik po pomoti vrne podatke dela ali materiale, jih ne izpiše',async()=>{
  list=[send({urna_postavka:'25.0000',stevilo_ur:'8.0000',stevilo_delavcev:2,cena_dela:'400.00',materiali:[{naziv:'Lepilo za ploščice',cena_na_enoto:'2.5000'}],vrsta_dela_id:'secret-id'})];open();await screen.findByText('Polaganje keramike');
  const main=document.body.textContent!;expect(main).not.toMatch(/Lepilo/);expect(main).not.toMatch(/25,00\s?€/);expect(main).not.toMatch(/400,00\s?€/);expect(main).not.toMatch(/delavc|Urna postavka|Število ur|Cena dela|secret-id/i);
 });
 it('postavka brez izmer (starejša poslana ponudba) ne pokaže praznega seznama izmer',async()=>{
  list=[quote()];open();await screen.findByText('Rušenje estriha');expect(screen.queryByRole('list',{name:/^Izmere /})).toBeNull();
 });
});
