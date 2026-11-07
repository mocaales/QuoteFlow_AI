import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { SupabaseClient } from '@supabase/supabase-js';
import InvoicePanel from '../features/invoices/components/InvoicePanel';
import CustomerInvoice from '../features/invoices/components/CustomerInvoice';
import { api, ApiError } from '../services/api';
vi.mock('../services/api', async importOriginal => ({ ...(await importOriginal<typeof import('../services/api')>()), api: vi.fn() }));
const mockedApi=vi.mocked(api);
const client={} as SupabaseClient;
const M='/podjetja/a/projekti/p3/racun',O='/projekti/p3/racun';
const line=()=>({zaporedje:1,naziv:'Polaganje keramike',opis:'Priprava podlage',vrsta_dela:'Keramika',enota:'m2',cena_na_enoto:'100.0000',kolicina:'2.0000',popust:'0.100000',stopnja_ddv:'0.220000',neto:'180.00',ddv:'39.60',koncna_cena:'219.60'});
const invoice=(more={})=>({stevilka:null,stanje_dokumenta:'osnutek',stanje_placila:'neplacan',izdajatelj_naziv:null,izdajatelj_naslov:null,izdajatelj_davcna:null,prejemnik_naziv:null,prejemnik_naslov:null,izdan_ob:null,poslan_ob:null,zapade_dne:null,placano_ob:null,
 ponudba:{stevilka:'P-2026-001',razlicica:1},postavke:[line()],ddv_po_stopnjah:[{stopnja_ddv:'0.220000',osnova:'180.00',ddv:'39.60'}],neto:'180.00',ddv:'39.60',skupaj:'219.60',...more});
const issued=(more={})=>invoice({stevilka:'R-2026-001',stanje_dokumenta:'izdan',izdajatelj_naziv:'Mojster Novak d.o.o.',izdajatelj_naslov:'Cesta 1, Maribor',izdajatelj_davcna:'SI12345678',prejemnik_naziv:'Janez Kranjc',prejemnik_naslov:'Ptuj, Slovenska 3',izdan_ob:'2026-11-06T10:00:00Z',poslan_ob:'2026-11-06T10:00:00Z',zapade_dne:'2026-11-14',...more});
let current:unknown;let failure:Error|null;let loadError:Error|null;
beforeEach(()=>{vi.clearAllMocks();failure=null;loadError=null;current=invoice();
 mockedApi.mockImplementation(async(_c,path,method)=>{
  if(method){if(failure)throw failure;if(path.endsWith('/izdaj'))current=issued();else current=issued({stanje_placila:'placan',placano_ob:'2026-11-20T09:00:00Z'});return current;}
  if(loadError)throw loadError;if(current===null)throw new ApiError('Zapis ni na voljo.',404);return current;
 });
});
afterEach(()=>{vi.useRealTimers();});
const panel=(done=true)=>render(<InvoicePanel client={client} companyId="a" projectId="p3" izvedbaKoncana={done} prejemnik="Janez Kranjc" naslov="Ptuj, Slovenska 3"/>);
const confirmIssue=async()=>{await userEvent.click(await screen.findByRole('button',{name:'Izdaj račun'}));await userEvent.click(await screen.findByRole('button',{name:'Potrdi izdajo'}));};
describe('Račun mojstra',()=>{
 it('osnutek pokaže postavke in vsote v evrih brez številke',async()=>{
  panel();expect(await screen.findByRole('heading',{name:/Osnutek računa/})).toBeTruthy();expect(mockedApi).toHaveBeenCalledWith(client,M);
  expect(screen.getByText('Polaganje keramike')).toBeTruthy();
  const totals=screen.getByRole('group',{name:'Vsote računa'});expect(totals.textContent).toMatch(/180,00\s?€/);expect(totals.textContent).toMatch(/39,60\s?€/);expect(totals.textContent).toMatch(/219,60\s?€/);
  expect(screen.queryByText(/R-20/)).toBeNull();expect(screen.queryByRole('button',{name:'Evidentiraj plačilo'})).toBeNull();
 });
 it('izdaja je onemogočena, dokler izvedba ni zaključena, in to pojasni',async()=>{
  panel(false);const button=await screen.findByRole('button',{name:'Izdaj račun'}) as HTMLButtonElement;
  expect(button.disabled).toBe(true);expect(screen.getAllByText(/po zaključeni izvedbi/i).length).toBeGreaterThan(0);
  await userEvent.click(button);expect(mockedApi.mock.calls.some(c=>c[2]==='POST')).toBe(false);
 });
 it('rok plačila je privzeto čez 8 dni od danes',async()=>{
  vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date(2026,10,6,10,0,0));
  panel();expect((await screen.findByLabelText('Rok plačila') as HTMLInputElement).value).toBe('2026-11-14');
 });
 it('izdaja pošlje prejemnika, naslov in rok plačila ter pokaže izdan račun s številko',async()=>{
  vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date(2026,10,6,10,0,0));
  panel();const date=await screen.findByLabelText('Rok plačila');
  fireDate(date as HTMLInputElement,'2026-11-20');await confirmIssue();
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,M+'/izdaj','POST',{prejemnik_naziv:'Janez Kranjc',prejemnik_naslov:'Ptuj, Slovenska 3',zapade_dne:'2026-11-20'}));
  expect(await screen.findByRole('heading',{name:/R-2026-001/})).toBeTruthy();expect(screen.queryByRole('button',{name:'Izdaj račun'})).toBeNull();expect(screen.getByRole('button',{name:'Evidentiraj plačilo'})).toBeTruthy();
 });
 it('napaka izdaje (npr. brez davčne številke) se pokaže in račun ostane osnutek',async()=>{
  failure=new Error('Podjetje nima davčne številke. Dopolnite podatke podjetja pred izdajo računa.');panel();
  await confirmIssue();expect((await screen.findByRole('alert')).textContent).toContain('davčne številke');
  expect(screen.getByRole('heading',{name:/Osnutek računa/})).toBeTruthy();expect(screen.getByRole('button',{name:'Izdaj račun'})).toBeTruthy();
 });
 it('izdan neplačan račun pokaže izdajatelja, prejemnika, rok in gumb za plačilo brez izdaje',async()=>{
  current=issued();panel();expect(await screen.findByRole('heading',{name:/R-2026-001/})).toBeTruthy();
  for(const text of ['Mojster Novak d.o.o.','Cesta 1, Maribor','SI12345678','Janez Kranjc','Ptuj, Slovenska 3'])expect(screen.getAllByText(new RegExp(text.replace(/[.]/g,'\\.'))).length).toBeGreaterThan(0);
  expect(screen.getAllByText('Neplačan').length).toBeGreaterThan(0);expect(screen.queryByRole('button',{name:'Izdaj račun'})).toBeNull();expect(screen.queryByLabelText('Rok plačila')).toBeNull();
  expect(screen.getAllByText(/14\.\s*(nov\.|11\.)\s*2026/).length).toBeGreaterThan(0);
 });
 it('evidentiranje plačila pošlje POST brez telesa in pokaže plačan, zaključen račun',async()=>{
  current=issued();panel();await userEvent.click(await screen.findByRole('button',{name:'Evidentiraj plačilo'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,M+'/placilo','POST'));
  expect((await screen.findAllByText('Plačan')).length).toBeGreaterThan(0);expect(screen.queryByRole('button',{name:'Evidentiraj plačilo'})).toBeNull();expect(screen.queryByRole('button',{name:'Izdaj račun'})).toBeNull();
 });
 it('plačan račun nima nobenega gumba za dejanje',async()=>{
  current=issued({stanje_placila:'placan',placano_ob:'2026-11-20T09:00:00Z'});panel();expect((await screen.findAllByText('Plačan')).length).toBeGreaterThan(0);
  expect(screen.queryAllByRole('button')).toEqual([]);
 });
 it('napaka plačila se pokaže in račun ostane neplačan',async()=>{
  current=issued();failure=new Error('V tej fazi projekta to dejanje ni dovoljeno.');panel();await userEvent.click(await screen.findByRole('button',{name:'Evidentiraj plačilo'}));
  expect((await screen.findByRole('alert')).textContent).toContain('V tej fazi');expect(screen.getByRole('button',{name:'Evidentiraj plačilo'})).toBeTruthy();expect(screen.queryByText('Plačan')).toBeNull();
 });
 it('brez računa (404) pove, da bo pripravljen po sprejeti ponudbi',async()=>{
  current=null;panel();expect((await screen.findAllByText(/po sprejeti ponudbi/i)).length).toBeGreaterThan(0);expect(screen.queryByRole('button',{name:'Izdaj račun'})).toBeNull();expect(screen.queryByRole('alert')).toBeNull();
 });
 it('druga napaka nalaganja ne pokaže praznega stanja',async()=>{
  loadError=new ApiError('Podatkovna baza trenutno ni na voljo.',503);panel();expect((await screen.findByRole('alert')).textContent).toContain('Podatkovna baza trenutno ni na voljo.');expect(screen.queryByText(/po sprejeti ponudbi/i)).toBeNull();
 });
});
function fireDate(input:HTMLInputElement,value:string){
 const setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!;setter.call(input,value);input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true}));
}
describe('Račun za stranko',()=>{
 const open=()=>render(<CustomerInvoice client={client} projectId="p3"/>);
 it('izdan račun pokaže številko, izdajatelja, prejemnika, datuma, postavke in vsote',async()=>{
  current=issued();open();expect(await screen.findByRole('heading',{name:/R-2026-001/})).toBeTruthy();expect(mockedApi).toHaveBeenCalledWith(client,O);
  for(const text of ['Mojster Novak d.o.o.','SI12345678','Janez Kranjc','Ptuj, Slovenska 3','Polaganje keramike'])expect(screen.getAllByText(new RegExp(text.replace(/[.]/g,'\\.'))).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/6\.\s*(nov\.|11\.)\s*2026/).length).toBeGreaterThan(0);expect(screen.getAllByText(/14\.\s*(nov\.|11\.)\s*2026/).length).toBeGreaterThan(0);expect(screen.getAllByText(/P-2026-001/).length).toBeGreaterThan(0);
  const totals=screen.getByRole('group',{name:'Vsote računa'});expect(totals.textContent).toMatch(/180,00\s?€/);expect(totals.textContent).toMatch(/39,60\s?€/);expect(totals.textContent).toMatch(/219,60\s?€/);
 });
 it('stranka nima nobenega dejanja in ne vidi materialov',async()=>{
  current=issued();open();await screen.findByRole('heading',{name:/R-2026-001/});expect(screen.queryAllByRole('button')).toEqual([]);expect(screen.queryByText(/Material/)).toBeNull();
 });
 it('plačan račun to pove',async()=>{
  current=issued({stanje_placila:'placan',placano_ob:'2026-11-20T09:00:00Z'});open();expect((await screen.findAllByText('Plačan')).length).toBeGreaterThan(0);expect(screen.queryByText('Neplačan')).toBeNull();
 });
 it('neplačan račun to pove',async()=>{
  current=issued();open();expect((await screen.findAllByText('Neplačan')).length).toBeGreaterThan(0);
 });
 it('račun, ki še ni izdan (404), pove, da ga še ni',async()=>{
  current=null;open();expect((await screen.findAllByText(/še ni izdan/i)).length).toBeGreaterThan(0);expect(screen.queryByRole('alert')).toBeNull();
 });
 it('druga napaka nalaganja ne pokaže praznega stanja',async()=>{
  loadError=new ApiError('Podatkovna baza trenutno ni na voljo.',503);open();expect((await screen.findByRole('alert')).textContent).toContain('Podatkovna baza trenutno ni na voljo.');expect(screen.queryByText(/še ni izdan/i)).toBeNull();
 });
});
