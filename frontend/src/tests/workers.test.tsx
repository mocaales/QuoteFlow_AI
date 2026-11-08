import { beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, screen, waitFor, within } from '@testing-library/react';
import { render, expectToast } from './render';
import userEvent from '@testing-library/user-event';
import type { Session, SupabaseClient } from '@supabase/supabase-js';
import Workers from '../features/workers/components/Workers';
import WorkspacePage from '../pages/WorkspacePage';
import { api, ApiError } from '../services/api';
vi.mock('../services/api', async importOriginal => ({ ...await importOriginal<typeof import('../services/api')>(), api: vi.fn() }));
const mockedApi=vi.mocked(api);
const client={} as SupabaseClient;
const L='/podjetja/a/delavci';
const w=(id:string,uporabnik_id:string,ime:string,priimek:string,e_posta:string,aktivna=true)=>({id,uporabnik_id,e_posta,ime,priimek,aktivna,dodeljeno_ob:'2026-11-03T09:00:00Z'});
const initial=()=>[w('w1','u2','Boris','Kos','boris@mail.si'),w('w2','u1','Ana','Novak','ana@gradnje.si'),w('w3','u3','Cene','Zor','cene@mail.si',false)];
let list:ReturnType<typeof initial>;let failure:Error|null;let loadError:Error|null;let invites:{id:string;e_posta:string;stanje:string;poslano_ob:string}[];
beforeEach(()=>{vi.clearAllMocks();list=initial();failure=null;loadError=null;invites=[];
 mockedApi.mockImplementation(async(_c,path,method,body)=>{
  if(path===L&&!method){if(loadError)throw loadError;return list;}
  if(path===L+'/povabila'&&!method)return invites;
  if(failure)throw failure;
  if(path===L+'/povabila'&&method==='POST'){const row={id:'p9',e_posta:(body as {e_posta:string}).e_posta,stanje:'povabljen',poslano_ob:'2026-11-07T09:00:00Z'};invites=[...invites,row];return row;}
  if(path.endsWith('/preklic')){const id=path.split('/').at(-2);invites=invites.map(x=>x.id===id?{...x,stanje:'preklicano'}:x);return {};}
  if(method==='PATCH'){const id=path.split('/').at(-1);list=list.map(x=>x.id===id?{...x,aktivna:(body as {aktivna:boolean}).aktivna}:x);return {};}
  return [];
 });
});
const open=async()=>{render(<Workers client={client} companyId="a" companyName="Gradnje d.o.o." userId="u1"/>);await screen.findByRole('table',{name:'Delavci podjetja'});};
const writes=()=>mockedApi.mock.calls.filter(c=>c[2]);
const add=async(email:string)=>{await userEvent.type(screen.getByLabelText('E-pošta delavca'),email);await userEvent.click(screen.getByRole('button',{name:'Povabi delavca'}));};
const rowOf=(email:string)=>within(screen.getByRole('table',{name:'Delavci podjetja'})).getByRole('row',{name:new RegExp(email.replace('.','\\.'))});

describe('Delavci: seznam',()=>{
 it('naslov s podjetjem, obrazec za dodajanje in pomoč',async()=>{
  await open();expect(screen.getByRole('heading',{level:1,name:'Delavci'})).toBeTruthy();expect(screen.getByText('Sodelavci podjetja Gradnje d.o.o.')).toBeTruthy();
  const input=screen.getByLabelText('E-pošta delavca') as HTMLInputElement;expect(input.type).toBe('email');expect(input.getAttribute('autocomplete')).toBe('off');
  expect(screen.getByText('Delavec mora biti že registriran in imeti potrjeno e-pošto.')).toBeTruthy();expect(screen.getByRole('button',{name:'Povabi delavca'}).querySelector('svg')).toBeTruthy();
  expect(mockedApi).toHaveBeenCalledWith(client,L);
 });
 it('privzeto pokaže samo aktivne delavce z imenom in e-pošto ter značko Vi pri lastni vrstici',async()=>{
  await open();const table=within(screen.getByRole('table',{name:'Delavci podjetja'}));
  expect(table.getByText('Boris Kos')).toBeTruthy();expect(table.getByText('boris@mail.si')).toBeTruthy();expect(table.queryByText('cene@mail.si')).toBeNull();
  expect(within(rowOf('ana@gradnje.si')).getByText('Vi')).toBeTruthy();expect(within(rowOf('boris@mail.si')).queryByText('Vi')).toBeNull();
  expect(within(rowOf('boris@mail.si')).getByText('Aktiven')).toBeTruthy();expect(screen.getByText('2 delavca')).toBeTruthy();
 });
 it('filter Odvzeti in Vsi ter iskanje samo zožijo naloženi seznam',async()=>{
  await open();await userEvent.selectOptions(screen.getByLabelText('Stanje'),'Odvzeti');
  expect(within(rowOf('cene@mail.si')).getByText('Odvzet')).toBeTruthy();expect(screen.getByText('1 delavec')).toBeTruthy();
  await userEvent.selectOptions(screen.getByLabelText('Stanje'),'Vsi');expect(screen.getByText('3 delavci')).toBeTruthy();
  await userEvent.type(screen.getByLabelText('Poišči delavca'),'ZOR');expect(screen.getByText('1 delavec')).toBeTruthy();
  expect(mockedApi.mock.calls.filter(c=>!c[2]).map(c=>c[1])).toEqual([L,L+'/povabila']);
 });
 it('brez ujemanja pove, da ni delavcev, in počisti filtre',async()=>{
  await open();await userEvent.type(screen.getByLabelText('Poišči delavca'),'nihče');
  expect(screen.getByText('Ni delavcev, ki ustrezajo iskanju.')).toBeTruthy();await userEvent.click(screen.getByRole('button',{name:'Počisti filtre'}));
  expect(screen.getByText('boris@mail.si')).toBeTruthy();
 });
 it('brez delavcev pokaže prazno stanje, obrazec za dodajanje ostane',async()=>{
  list=[];render(<Workers client={client} companyId="a" companyName="Gradnje d.o.o." userId="u1"/>);
  expect(await screen.findByText('V podjetju še ni delavcev.')).toBeTruthy();expect(screen.getByText('Povabite prvega delavca z njegovo e-pošto.')).toBeTruthy();expect(screen.getByRole('button',{name:'Povabi delavca'})).toBeTruthy();
 });
 it('med nalaganjem pokaže stanje, ob napaki opozorilo in poskusi znova',async()=>{
  loadError=new Error('Podatkovna baza trenutno ni na voljo.');render(<Workers client={client} companyId="a" companyName="Gradnje d.o.o." userId="u1"/>);
  expect(screen.getAllByRole('status').map(s=>s.textContent).join(' ')).toContain('Nalagam delavce …');
  expect((await screen.findByRole('alert')).textContent).toContain('Podatkovna baza trenutno ni na voljo.');expect(screen.queryByText('V podjetju še ni delavcev.')).toBeNull();
  loadError=null;await userEvent.click(screen.getByRole('button',{name:'Poskusi znova'}));expect(await screen.findByText('boris@mail.si')).toBeTruthy();
 });
});

describe('Delavci: povabila',()=>{
 const sent='Povabilo je poslano. Delavec ga mora sprejeti v svojem računu.';
 it('pošlje samo e_posta na povabila, počisti polje in vedno pokaže isto sporočilo',async()=>{
  await open();await add('novi@mail.si');
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,L+'/povabila','POST',{e_posta:'novi@mail.si'}));
  await expectToast(sent);expect((screen.getByLabelText('E-pošta delavca') as HTMLInputElement).value).toBe('');
  expect(await screen.findByRole('heading',{name:'Povabila'})).toBeTruthy();expect(screen.queryByText('Delavec je dodan.')).toBeNull();
  expect(writes().every(c=>c[1]!==L)).toBe(true);
 });
 it('tabela povabil kaže e-pošto, stanje in datum; preklic le pri odprtih in šele po potrditvi',async()=>{
  invites=[{id:'p1',e_posta:'caka@mail.si',stanje:'povabljen',poslano_ob:'2026-11-05T09:00:00Z'},{id:'p2',e_posta:'ne@mail.si',stanje:'zavrnjeno',poslano_ob:'2026-11-01T09:00:00Z'},{id:'p3',e_posta:'ok@mail.si',stanje:'sprejeto',poslano_ob:'2026-11-01T09:00:00Z'},{id:'p4',e_posta:'staro@mail.si',stanje:'poteklo',poslano_ob:'2026-10-01T09:00:00Z'},{id:'p5',e_posta:'pre@mail.si',stanje:'preklicano',poslano_ob:'2026-10-01T09:00:00Z'}];
  await open();const t=within(screen.getByRole('table',{name:'Povabila delavcev'}));
  for(const x of ['Čaka','Zavrnjeno','Sprejeto','Poteklo','Preklicano'])expect(t.getByText(x)).toBeTruthy();
  expect(t.getAllByRole('button',{name:/Prekliči povabilo/})).toHaveLength(1);
  await userEvent.click(t.getByRole('button',{name:'Prekliči povabilo za caka@mail.si'}));expect(writes()).toHaveLength(0);
  await userEvent.click(screen.getByRole('button',{name:'Prekliči povabilo'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,L+'/povabila/p1/preklic','POST'));await expectToast('Povabilo je preklicano.');
  await waitFor(()=>expect(within(screen.getByRole('table',{name:'Povabila delavcev'})).getAllByText('Preklicano')).toHaveLength(2));
 });
 it('napake ne razkrijejo strežnikovega besedila razen pravic in omejitve',async()=>{
  failure=new ApiError('Uporabnik ne obstaja.',404);await open();await add('x@mail.si');
  expect((await screen.findByRole('alert')).textContent).toBe('Povabila ni mogoče poslati. Preverite e-pošto in poskusite znova.');
  failure=new ApiError('Preveč povabil. Poskusite pozneje.',429);await userEvent.clear(screen.getByLabelText('E-pošta delavca'));await add('y@mail.si');await waitFor(()=>expect(screen.getByRole('alert').textContent).toContain('Preveč povabil.'));
  failure=new ApiError('Za to dejanje nimate pravice.',403);await userEvent.clear(screen.getByLabelText('E-pošta delavca'));await add('z@mail.si');await waitFor(()=>expect(screen.getByRole('alert').textContent).toContain('nimate pravice'));
 });
 it('dvojni klik pošlje en sam POST in onemogoči gumb',async()=>{
  let release!:()=>void;const gate=new Promise<void>(r=>{release=r;});
  const base=mockedApi.getMockImplementation()!;mockedApi.mockImplementation(async(c,p,m,b)=>{if(m==='POST')await gate;return base(c,p,m,b);});
  await open();await userEvent.type(screen.getByLabelText('E-pošta delavca'),'novi@mail.si');const button=screen.getByRole('button',{name:'Povabi delavca'}) as HTMLButtonElement;
  await userEvent.click(button);await userEvent.click(button);expect(button.disabled).toBe(true);release();
  await waitFor(()=>expect(button.disabled).toBe(false));expect(writes()).toHaveLength(1);
 });
 it('ne ponuja imenika uporabnikov',async()=>{
  await open();const input=screen.getByLabelText('E-pošta delavca');expect(input.getAttribute('list')).toBeNull();expect(document.querySelector('datalist')).toBeNull();
  await userEvent.type(input,'bo');expect(screen.queryByRole('listbox')).toBeNull();expect(mockedApi.mock.calls.every(c=>String(c[1]).startsWith(L))).toBe(true);
 });
});

describe('Delavci: odvzem in ponovna omogočitev',()=>{
 it('odvzem ima besedilni gumb z imenom osebe in najprej vpraša, kaj se zgodi z drugimi podjetji',async()=>{
  await open();const button=within(rowOf('boris@mail.si')).getByRole('button',{name:/Odvzemi dostop.*boris@mail\.si/});expect(button.textContent).toMatch(/Odvzemi dostop/);expect(button.querySelector('svg')).toBeTruthy();
  await userEvent.click(button);expect(writes()).toHaveLength(0);
  expect(screen.getByText('Odvzamem dostop delavcu boris@mail.si? Njegove vloge pri drugih podjetjih ostanejo nespremenjene.')).toBeTruthy();
  expect(screen.getByRole('button',{name:'Odvzemi dostop'})).toBeTruthy();expect(screen.getByRole('button',{name:'Prekliči'})).toBeTruthy();
 });
 it('prekliči ne pošlje ničesar',async()=>{
  await open();await userEvent.click(within(rowOf('boris@mail.si')).getByRole('button',{name:/Odvzemi dostop/}));await userEvent.click(screen.getByRole('button',{name:'Prekliči'}));
  expect(writes()).toHaveLength(0);expect(screen.queryByText(/Odvzamem dostop/)).toBeNull();
 });
 it('potrjen odvzem pošlje PATCH, osveži in sporoči uspeh',async()=>{
  await open();await userEvent.click(within(rowOf('boris@mail.si')).getByRole('button',{name:/Odvzemi dostop/}));await userEvent.click(screen.getByRole('button',{name:'Odvzemi dostop'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,L+'/w1','PATCH',{aktivna:false}));
  await expectToast('Dostop delavca je odvzet.');await waitFor(()=>expect(screen.queryByText('boris@mail.si')).toBeNull());
 });
 it('ponovna omogočitev odvzetega delavca ne vpraša in pošlje aktivna true',async()=>{
  await open();await userEvent.selectOptions(screen.getByLabelText('Stanje'),'Odvzeti');await userEvent.click(screen.getByRole('button',{name:/Ponovno omogoči.*cene@mail\.si/}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,L+'/w3','PATCH',{aktivna:true}));await expectToast('Dostop delavca je ponovno omogočen.');
 });
 it('napaka pri odvzemu ohrani vrstico in pokaže opozorilo',async()=>{
  await open();failure=new Error('Delavca ni več mogoče spremeniti.');
  await userEvent.click(within(rowOf('boris@mail.si')).getByRole('button',{name:/Odvzemi dostop/}));await userEvent.click(screen.getByRole('button',{name:'Odvzemi dostop'}));
  expect((await screen.findByRole('alert')).textContent).toContain('Delavca ni več mogoče spremeniti.');expect(screen.getByText('boris@mail.si')).toBeTruthy();
 });
 it('mojstrova lastna vloga ni na seznamu in nima dejanj',async()=>{
  await open();expect(screen.queryByText(/Mojster/)).toBeNull();expect(screen.queryByRole('button',{name:/Odvzemi.*mojster/i})).toBeNull();
 });
});

describe('Delavci: navigacija po vlogah',()=>{
 const session={access_token:'t',user:{email:'ana@example.test'}} as Session;
 const profile=(vloge:{vloga:string;podjetje_id:string|null}[])=>({id:'u1',e_posta:'ana@example.test',ime:'Ana',priimek:'Novak',vloge:vloge.map((v,i)=>({id:'r'+i,naziv:null,...v}))});
 const nav=async(vloge:{vloga:string;podjetje_id:string|null}[])=>{
  mockedApi.mockImplementation(async(_c,path)=>path==='/me'?profile(vloge):path==='/podjetja'?[{id:'a',naziv:'Gradnje d.o.o.',aktivno:true}]:path===L?initial():path==='/povabila'?[]:[]);
  render(<WorkspacePage client={client} session={session}/>);await waitFor(()=>expect(screen.queryByText('Preverjam dostop …')).toBeNull());
  return within(screen.getByRole('navigation',{name:'Glavna navigacija'}));
 };
 it('mojster vidi Delavci in odpre seznam delavcev svojega podjetja',async()=>{
  const n=await nav([{vloga:'mojster',podjetje_id:'a'}]);await userEvent.click(await n.findByRole('button',{name:'Delavci'}));
  expect(await screen.findByRole('heading',{level:1,name:'Delavci'})).toBeTruthy();expect(await screen.findByText('boris@mail.si')).toBeTruthy();expect(mockedApi).toHaveBeenCalledWith(client,L);
 });
 it('delavec, stranka in admin brez mojstra ne vidijo Delavci',async()=>{
  for(const vloge of [[{vloga:'delavec',podjetje_id:'a'}],[{vloga:'stranka',podjetje_id:null}],[{vloga:'admin',podjetje_id:null}]]){
   const n=await nav(vloge);expect(n.queryByRole('button',{name:'Delavci'})).toBeNull();expect(n.queryByRole('button',{name:'Projekti'})).toBeNull();cleanup();
  }
 });
});
