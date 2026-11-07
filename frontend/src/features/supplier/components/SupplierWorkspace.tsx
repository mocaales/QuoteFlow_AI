import { useCallback, useEffect, useRef, useState } from 'react';
import type { SupabaseClient } from '@supabase/supabase-js';
import Drawer from '../../../components/Drawer';
import IconButton from '../../../components/IconButton';
import Icon from '../../../components/Icon';
import { money, quantity, percent } from '../../../utils/format';
import { getCatalog, getWorkTypes, getMaterials, getMaterialKinds, saveMaterial, saveMaterialKind, removeStock, saveCatalogItem, saveStock } from '../api';
import { type CatalogItem, type Material, type MaterialKind, type Stock, type SupplierTab, type WorkType } from '../types';
import CatalogForm from './CatalogForm';
import MaterialForm from './MaterialForm';
import StockForm from './StockForm';
import WorkTypes from './WorkTypes';

type Editor = { type: 'catalog'; item: CatalogItem | null } | { type: 'material'; item: Material | null } | { type: 'stock'; item: Material; stock?: Stock } | { type: 'kind' };
export default function SupplierWorkspace({ client, companyId, tab, onTab }: { client: SupabaseClient; companyId: string; tab: SupplierTab; onTab?: (tab: SupplierTab) => void }) {
 const [items, setItems] = useState<CatalogItem[]>([]);
 const [materials, setMaterials] = useState<Material[]>([]);
 const [kinds, setKinds] = useState<MaterialKind[]>([]);
 const [trades, setTrades] = useState<WorkType[]>([]);
 const [loading, setLoading] = useState(true);
 const [busy, setBusy] = useState(false);
 const [error, setError] = useState('');
 const [notice, setNotice] = useState('');
 const [search, setSearch] = useState('');
 const [filter, setFilter] = useState('vse');
 const [editor, setEditor] = useState<Editor | null>(null);
 const sequence = useRef(0);
 const load = useCallback(async () => {
  const request = ++sequence.current;
  try {
   const [catalog, stock, categories, works] = await Promise.all([getCatalog(client, companyId), getMaterials(client, companyId), getMaterialKinds(client, companyId), getWorkTypes(client, companyId)]);
   if (request === sequence.current) { setItems(catalog); setMaterials(stock); setKinds(categories); setTrades(works); }
  } finally { if (request === sequence.current) setLoading(false); }
 }, [client, companyId]);
 useEffect(() => { void load().catch(e => setError(e instanceof Error ? e.message : 'Podatki niso na voljo.')); return () => { sequence.current++; }; }, [load]);
 useEffect(() => { setSearch(''); setFilter('vse'); setEditor(null); setError(''); setNotice(''); }, [tab]);
 async function mutate(action: () => Promise<unknown>, message: string) {
  setBusy(true); setError(''); setNotice('');
  try { await action(); await load(); setEditor(null); setNotice(message); }
  catch (e) { setError(e instanceof Error ? e.message : 'Spremembe ni mogoče shraniti.'); }
  finally { setBusy(false); }
 }
 const title = tab === 'cenik' ? 'Cenik' : tab === 'vrste-dela' ? 'Vrste dela' : tab === 'materiali' ? 'Materiali' : 'Zaloge';
 const match = (naziv: string) => naziv.toLocaleLowerCase('sl').includes(search.toLocaleLowerCase('sl'));
 const catalog = items.filter(item => match(item.naziv) && (filter === 'vse' || (filter === 'aktivne' ? item.aktivna : !item.aktivna)));
 const stock = materials.filter(item => match(`${item.naziv} ${item.sifra}`) && (filter === 'vse' || (filter === 'aktivne' ? item.aktiven : !item.aktiven)));
 function open(next: Editor) { setError(''); setNotice(''); setEditor(next); }
 return <section className="supplier-view" aria-busy={loading}>
  <div className="page-title"><div><h1>{title}</h1><p>{tab === 'cenik' ? 'Postavke dela in storitev za pripravo ponudb.' : tab === 'vrste-dela' ? 'Vrste dela določajo urno postavko, ure in delavce ter interne materiale.' : tab === 'materiali' ? 'Materiali, njihove vrste, šifre in cene.' : 'Količine materialov po lokacijah.'}</p></div><div className="title-actions">
   {tab === 'materiali' && <button className="secondary" disabled={loading || busy} onClick={() => open({ type: 'kind' })}><Icon name="plus"/>Nova vrsta</button>}
   {tab !== 'zaloge' && tab !== 'vrste-dela' && <button disabled={loading || busy || (tab === 'materiali' && !kinds.length)} onClick={() => open(tab === 'cenik' ? { type: 'catalog', item: null } : { type: 'material', item: null })}><Icon name="plus"/>{tab === 'cenik' ? 'Nova postavka' : 'Nov material'}</button>}
  </div></div>
  {error && !editor && <p role="alert" className="alert">{error}<IconButton icon="refresh" label="Poskusi znova" className="on-alert" onClick={() => { setError(''); void load().catch(e => setError(e.message)); }}/></p>}
  {notice && <p role="status" className="notice"><Icon name="check"/>{notice}</p>}
  {onTab && (tab === 'cenik' || tab === 'vrste-dela') && <div className="tabs" role="tablist" aria-label="Področje cenika">{([['cenik', 'Storitve'], ['vrste-dela', 'Vrste dela']] as const).map(([id, label]) => <button key={id} role="tab" className="tab" aria-selected={tab === id} onClick={() => onTab(id)}>{label}</button>)}</div>}
  {loading ? <div className="loading-state" role="status">Nalagam podatke podjetja …</div> : tab === 'vrste-dela' ? <WorkTypes client={client} companyId={companyId} workTypes={trades} materials={materials} failed={!!error} busy={busy} onChange={load}/> : <>
   <div className="tabs" role="tablist" aria-label="Stanje postavk">{[['vse','Vse'],['aktivne','Aktivne'],['neaktivne','Neaktivne']].map(([id,label]) => <button key={id} role="tab" className="tab" aria-selected={filter === id} onClick={() => setFilter(id)}>{label}</button>)}</div>
   <div className="data-toolbar"><label className="search-field"><Icon name="search"/><span className="sr-only">Išči po nazivu</span><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Išči po nazivu …"/></label><span className="result-count">{tab === 'cenik' ? catalog.length : stock.length} postavk</span></div>
   <div className="table-wrap"><table className="data-table"><caption className="sr-only">{title} izbranega podjetja</caption><thead><tr><th>Postavka</th>{tab === 'cenik' ? <><th className="num">Cena / enoto</th><th className="num">DDV</th><th>Stanje</th></> : tab === 'materiali' ? <><th>Vrsta</th><th className="num">Cena / enoto</th><th>Stanje</th></> : <><th>Lokacija</th><th className="num">Količina</th></>}<th><span className="sr-only">Dejanja</span></th></tr></thead><tbody>
    {tab === 'cenik' ? catalog.map(item => <tr key={item.id}><td><strong>{item.naziv}</strong><span className="cell-detail">{trades.find(trade => trade.id === item.vrsta_dela_id)?.naziv ?? '–'} · {item.enota}</span></td><td className="num">{money(item.cena_na_enoto)}</td><td className="num">{percent(item.stopnja_ddv)}</td><td><span className={`status-badge ${item.aktivna ? 'confirmed' : 'inactive'}`}>{item.aktivna ? 'Aktivna' : 'Neaktivna'}</span></td><td><IconButton icon="pen" label={`Uredi ${item.naziv}`} tip="Uredi" disabled={busy} onClick={() => open({ type:'catalog', item })}/></td></tr>) : stock.flatMap(item => tab === 'materiali' ? [<tr key={item.id}><td><strong>{item.naziv}</strong><span className="cell-detail">{item.sifra} · {item.enota}</span></td><td>{kinds.find(kind => kind.id === item.vrsta_materiala_id)?.naziv}</td><td className="num">{money(item.cena_na_enoto)}</td><td><span className={`status-badge ${item.aktiven ? 'confirmed' : 'inactive'}`}>{item.aktiven ? 'Aktiven' : 'Neaktiven'}</span></td><td><IconButton icon="pen" label={`Uredi ${item.naziv}`} tip="Uredi" disabled={busy} onClick={() => open({type:'material',item})}/></td></tr>] : [
     ...(item.zaloge ?? []).map(location => <tr key={`${item.id}-${location.lokacija}`}><td><strong>{item.naziv}</strong><span className="cell-detail">{item.sifra}</span></td><td>{location.lokacija}</td><td className="num">{quantity(location.kolicina)} {item.enota}</td><td><IconButton icon="pen" label={`Zaloga za ${item.naziv}: ${location.lokacija}`} tip="Uredi zalogo" disabled={busy} onClick={() => open({type:'stock',item,stock:location})}/></td></tr>),
     <tr key={`${item.id}-add`}><td><strong>{item.naziv}</strong></td><td colSpan={2} className="muted">{item.zaloge?.length ? 'Dodaj drugo lokacijo' : 'Brez evidence zaloge'}</td><td><IconButton icon="plus" label={`Dodaj zalogo za ${item.naziv}`} tip="Nova lokacija" disabled={busy} onClick={() => open({type:'stock',item})}/></td></tr>
    ])}
   </tbody></table></div>
   {!error && (tab === 'cenik' ? !catalog.length : !stock.length) && <div className="full-empty"><Icon name={tab === 'zaloge' ? 'stock' : 'list'}/><h2>{tab === 'cenik' && !items.length ? 'Dodajte prvo postavko' : 'Ni postavk za prikaz'}</h2><p>{tab === 'cenik' ? 'Dodajte postavko dela ali spremenite iskanje.' : 'Najprej v zavihku Materiali dodajte vrsto in material.'}</p></div>}
   {tab === 'materiali' && <p className="table-footnote">Vrste materiala: {kinds.map(kind => kind.naziv).join(', ') || 'Vrste še niso določene.'}</p>}
  </>}
  {editor && <Drawer title={editor.type === 'catalog' ? editor.item ? 'Uredi postavko' : 'Nova postavka' : editor.type === 'material' ? editor.item ? 'Uredi material' : 'Nov material' : editor.type === 'kind' ? 'Nova vrsta materiala' : 'Uredi zalogo'} onClose={() => { if (!busy) setEditor(null); }}>
   {error && <p role="alert" className="alert">{error}</p>}
   {editor.type === 'catalog' && <CatalogForm item={editor.item} trades={trades} busy={busy} onSave={data => mutate(() => saveCatalogItem(client, companyId, data, editor.item?.id), 'Postavka je shranjena.')}/>}
   {editor.type === 'material' && <MaterialForm item={editor.item} kinds={kinds} busy={busy} onSave={data => mutate(() => saveMaterial(client, companyId, data, editor.item?.id), 'Material je shranjen.')}/>}
   {editor.type === 'kind' && <form className="editor-form" onSubmit={event => { event.preventDefault(); const name = String(new FormData(event.currentTarget).get('naziv')).trim(); void mutate(() => saveMaterialKind(client, companyId, name), 'Vrsta je shranjena.'); }}><label>Naziv vrste<input name="naziv" required maxLength={200} autoFocus/></label><button disabled={busy}><Icon name="check"/>Shrani vrsto</button></form>}
   {editor.type === 'stock' && <StockForm item={editor.item} stock={editor.stock} busy={busy} onSave={(location,q) => mutate(() => saveStock(client, companyId, editor.item.id, location,q), 'Zaloga je shranjena.')} onRemove={() => mutate(() => removeStock(client, companyId, editor.item.id, editor.stock!.lokacija), 'Lokacija je odstranjena.')}/>}
  </Drawer>}
 </section>;
}
