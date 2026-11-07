import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { SupabaseClient } from '@supabase/supabase-js';
import InvoicePanel from '../features/invoices/components/InvoicePanel';
import { api, ApiError } from '../services/api';
vi.mock('../services/api', async importOriginal => ({ ...(await importOriginal<typeof import('../services/api')>()), api: vi.fn() }));
const mockedApi=vi.mocked(api);
const client={} as SupabaseClient;
const M='/podjetja/a/projekti/p3/racun';
const draft={stevilka:null,stanje_dokumenta:'osnutek',stanje_placila:'neplacan',izdajatelj_naziv:null,izdajatelj_naslov:null,izdajatelj_davcna:null,prejemnik_naziv:null,prejemnik_naslov:null,izdan_ob:null,poslan_ob:null,zapade_dne:null,placano_ob:null,
 ponudba:{stevilka:'P-2026-001',razlicica:1},postavke:[{zaporedje:1,naziv:'Polaganje',opis:'',vrsta_dela:'K',enota:'m2',cena_na_enoto:'100.0000',kolicina:'2.0000',popust:'0.100000',stopnja_ddv:'0.220000',neto:'180.00',ddv:'39.60',koncna_cena:'219.60'}],ddv_po_stopnjah:[{stopnja_ddv:'0.220000',osnova:'180.00',ddv:'39.60'}],neto:'180.00',ddv:'39.60',skupaj:'219.60'};
let current:unknown;
beforeEach(()=>{vi.clearAllMocks();current=draft;
 mockedApi.mockImplementation(async(_c,path,method)=>{
  if(method){current={...draft,stevilka:'R-2026-001',stanje_dokumenta:'izdan',izdajatelj_naziv:'A',izdajatelj_naslov:'B',izdajatelj_davcna:'SI1',prejemnik_naziv:'X',prejemnik_naslov:'Y',izdan_ob:'2026-11-06T10:00:00Z',poslan_ob:'2026-11-06T10:00:00Z',zapade_dne:'2026-11-20'};return current;}
  if(current===null)throw new ApiError('Zapis ni na voljo.',404);return current;
 });
});
afterEach(()=>{vi.useRealTimers();});
const panel=(more={})=>render(<InvoicePanel client={client} companyId="a" projectId="p3" izvedbaKoncana prejemnik="Janez Kranjc" naslov="Ptuj, Slovenska 3" {...more}/>);
const posts=()=>mockedApi.mock.calls.filter(c=>c[2]==='POST');
const setDate=(input:HTMLElement,value:string)=>{const setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!;setter.call(input,value);input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true}));};
describe('Obrazec za izdajo računa: prejemnik in naslov (M-1)',()=>{
 it('polji Prejemnik in Naslov prejemnika sta predizpolnjeni iz projekta',async()=>{
  panel();expect((await screen.findByLabelText('Prejemnik') as HTMLInputElement).value).toBe('Janez Kranjc');expect((screen.getByLabelText('Naslov prejemnika') as HTMLInputElement).value).toBe('Ptuj, Slovenska 3');
 });
 it('mojster lahko popravi prejemnika in naslov, poslano je natanko vneseno (obrezano)',async()=>{
  panel();const name=await screen.findByLabelText('Prejemnik'),addr=screen.getByLabelText('Naslov prejemnika');
  await userEvent.clear(name);await userEvent.type(name,'  Gradnje d.o.o.  ');await userEvent.clear(addr);await userEvent.type(addr,'Celje, Cesta 5');setDate(screen.getByLabelText('Rok plačila'),'2026-11-25');
  await userEvent.click(screen.getByRole('button',{name:'Izdaj račun'}));await userEvent.click(await screen.findByRole('button',{name:'Potrdi izdajo'}));
  await waitFor(()=>expect(mockedApi).toHaveBeenCalledWith(client,M+'/izdaj','POST',{prejemnik_naziv:'Gradnje d.o.o.',prejemnik_naslov:'Celje, Cesta 5',zapade_dne:'2026-11-25'}));
 });
 it('prazna lokacija projekta pusti naslov prazen in izdaja brez naslova ni mogoča',async()=>{
  panel({naslov:''});const addr=await screen.findByLabelText('Naslov prejemnika') as HTMLInputElement;expect(addr.value).toBe('');
  await userEvent.click(screen.getByRole('button',{name:'Izdaj račun'}));expect(screen.queryByRole('button',{name:'Potrdi izdajo'})).toBeNull();expect(posts().length).toBe(0);
 });
 it.each(['Prejemnik','Naslov prejemnika'])('prazno polje %s ne dovoli potrditve in ne pošlje zahtevka',async label=>{
  panel();const field=await screen.findByLabelText(label);await userEvent.clear(field);await userEvent.type(field,'   ');
  await userEvent.click(screen.getByRole('button',{name:'Izdaj račun'}));
  expect(screen.queryByRole('button',{name:'Potrdi izdajo'})).toBeNull();expect(posts().length).toBe(0);
 });
 it('polji imata omejitev dolžine 200 in 300 znakov',async()=>{
  panel();expect((await screen.findByLabelText('Prejemnik') as HTMLInputElement).maxLength).toBe(200);expect((screen.getByLabelText('Naslov prejemnika') as HTMLInputElement).maxLength).toBe(300);
 });
 it('e-pošte stranke nikoli ne pošlje kot prejemnika, ko mojster ne spremeni polja',async()=>{
  panel();await userEvent.click(await screen.findByRole('button',{name:'Izdaj račun'}));await userEvent.click(await screen.findByRole('button',{name:'Potrdi izdajo'}));
  await waitFor(()=>expect(posts().length).toBe(1));expect(JSON.stringify(posts()[0][3])).not.toContain('@');
 });
});
describe('Potrditev izdaje računa (nepovratno)',()=>{
 it('klik na Izdaj račun zahteva potrditev in ne pošlje ničesar',async()=>{
  panel();await userEvent.click(await screen.findByRole('button',{name:'Izdaj račun'}));
  expect(await screen.findByRole('button',{name:'Potrdi izdajo'})).toBeTruthy();expect(screen.getByRole('button',{name:'Prekliči'})).toBeTruthy();expect(posts().length).toBe(0);
 });
 it('Potrdi izdajo pošlje natanko en POST in pokaže izdan račun',async()=>{
  panel();await userEvent.click(await screen.findByRole('button',{name:'Izdaj račun'}));await userEvent.click(await screen.findByRole('button',{name:'Potrdi izdajo'}));
  expect(await screen.findByRole('heading',{name:/R-2026-001/})).toBeTruthy();expect(posts().length).toBe(1);
 });
 it('Prekliči zapre potrditev brez zahtevka, obrazec ostane izpolnjen',async()=>{
  panel();await userEvent.click(await screen.findByRole('button',{name:'Izdaj račun'}));await userEvent.click(await screen.findByRole('button',{name:'Prekliči'}));
  expect(screen.queryByRole('button',{name:'Potrdi izdajo'})).toBeNull();expect((screen.getByLabelText('Prejemnik') as HTMLInputElement).value).toBe('Janez Kranjc');expect(posts().length).toBe(0);
 });
 it('potrditev pove, da izdanega računa ni mogoče spremeniti',async()=>{
  panel();await userEvent.click(await screen.findByRole('button',{name:'Izdaj račun'}));const confirm=await screen.findByRole('button',{name:'Potrdi izdajo'});
  expect(confirm.closest('[role="dialog"],[role="alertdialog"],section,form,div')!.textContent).toMatch(/ne bo(ste)? (več )?mogoče (več )?(urejati|spreminjati|popraviti)|nespremenljiv|nepreklicn/i);
 });
});
