import { useCallback, useEffect, useRef, useState } from 'react';
import type { SupabaseClient } from '@supabase/supabase-js';
import Drawer from '../../../components/Drawer';
import IconButton from '../../../components/IconButton';
import Icon from '../../../components/Icon';
import { dateTime, money, quantity, percent } from '../../../utils/format';
import { confirmCatalogItem, createRules, getCatalog, getRules, removeStock, saveCatalogItem, saveStock } from '../api';
import type { CatalogItem, SalesRules, SupplierTab } from '../types';
import CatalogForm from './CatalogForm';
import StockForm from './StockForm';
import RulesForm from './RulesForm';

// List states: catalogue confirmation on Cenik, the stock record on Zaloge.
function matches(item: CatalogItem, filter: string) {
 const stock = item.razpolozljiva_kolicina;
 return filter === 'vse' || (filter === 'potrjene' ? item.aktivna && !!item.potrjeno_ob : filter === 'nepotrjene' ? item.aktivna && !item.potrjeno_ob : filter === 'neaktivne' ? !item.aktivna
  : filter === 'zaloga' ? stock !== null && Number(stock) > 0 : filter === 'prazno' ? stock !== null && Number(stock) === 0 : stock === null);
}
type Editor = { type: 'catalog'; item: CatalogItem | null } | { type: 'stock'; item: CatalogItem } | { type: 'rules' };
export default function SupplierWorkspace({ client, companyId, tab }: { client: SupabaseClient; companyId: string; tab: SupplierTab }) {
 const [items, setItems] = useState<CatalogItem[]>([]);
 const [rules, setRules] = useState<SalesRules[]>([]);
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
   const [catalog, versions] = await Promise.all([getCatalog(client, companyId), getRules(client, companyId)]);
   if (request === sequence.current) { setItems(catalog); setRules(versions); }
  } catch (e) {
   if (request === sequence.current) { setItems([]); setRules([]); }
   throw e;
  } finally { if (request === sequence.current) setLoading(false); }
 }, [client, companyId]);
 useEffect(() => {
  void load().catch(e => setError(e instanceof Error ? e.message : 'Podatki niso na voljo.'));
  return () => { sequence.current++; };
 }, [load]);
 useEffect(() => { setSearch(''); setFilter('vse'); setEditor(null); setError(''); setNotice(''); }, [tab]);
 async function mutate(action: () => Promise<unknown>, message: string) {
  setBusy(true); setError(''); setNotice('');
  try { await action(); await load(); setEditor(null); setNotice(message); }
  catch (e) { setError(e instanceof Error ? e.message : 'Spremembe ni mogoče shraniti.'); }
  finally { setBusy(false); }
 }
 const goods = items.filter(item => item.vrsta === 'blago');
 const candidates = tab === 'zaloge' ? goods : items;
 const visible = candidates.filter(item => item.opis.toLocaleLowerCase('sl').includes(search.toLocaleLowerCase('sl')) &&
  matches(item, filter));
 const now = Date.now();
 const current = rules.find(rule => new Date(rule.velja_od).getTime() <= now && (!rule.velja_do || new Date(rule.velja_do).getTime() > now));
 const next = rules.filter(rule => new Date(rule.velja_od).getTime() > now).sort((a, b) => a.velja_od.localeCompare(b.velja_od))[0];
 const active = items.filter(item => item.aktivna), confirmed = active.filter(item => item.potrjeno_ob).length;
 const tracked = goods.filter(item => item.razpolozljiva_kolicina !== null), empty = tracked.filter(item => Number(item.razpolozljiva_kolicina) === 0).length;
 const states = (tab === 'zaloge' ? [['vse', 'Vse'], ['zaloga', 'Na zalogi'], ['prazno', 'Brez zaloge'], ['nevodi', 'Brez evidence']] : [['vse', 'Vse'], ['potrjene', 'Potrjene'], ['nepotrjene', 'Čakajo potrditev'], ['neaktivne', 'Neaktivne']])
  .map(([id, label]) => [id, label, candidates.filter(item => matches(item, id)).length] as const);
 const title = tab === 'cenik' ? 'Cenik' : tab === 'zaloge' ? 'Zaloge' : 'Prodajna pravila';
 const finding = loading || error ? null : tab === 'cenik' ? active.length ? <><strong>{confirmed} od {active.length}</strong> aktivnih postavk je potrjenih in na voljo za ponudbe.{active.length > confirmed && ` Potrditev čaka še ${active.length - confirmed}.`}</> : 'Blago in storitve, ki jih uporabljate v ponudbah.'
  : tab === 'zaloge' ? goods.length ? <>Zaloga je potrjena za <strong>{tracked.length} od {goods.length}</strong> artiklov blaga.{empty > 0 && ` Brez zaloge: ${empty}.`}</> : 'Potrjene količine blaga. Podatek o zalogi je neobvezen.'
  : next ? `Naslednja različica velja od ${dateTime(next.velja_od)}.` : 'Pogoji prodaje in zgodovina njihove veljavnosti.';
 function open(next: Editor) { setError(''); setNotice(''); setEditor(next); }
 const failed = !!error && !editor && !items.length && !rules.length;
 return <section className="supplier-view" aria-busy={loading}>
  <div className="page-title"><div><h1>{title}</h1>{finding && <p>{finding}</p>}</div>
   {tab !== 'zaloge' && <div className="title-actions"><button disabled={loading || busy || !!error} onClick={() => open(tab === 'cenik' ? { type: 'catalog', item: null } : { type: 'rules' })}><Icon name="plus"/>{tab === 'cenik' ? 'Nova postavka' : 'Nova različica'}</button></div>}
  </div>
  {error && !editor && <p role="alert" className="alert">{error}<IconButton icon="refresh" label="Poskusi znova" className="on-alert" onClick={() => { setError(''); void load().catch(e => setError(e.message)); }}/></p>}
  {notice && <p role="status" className="notice"><Icon name="check"/>{notice}</p>}
  {loading ? <div className="loading-state" role="status">Nalagam podatke ponudnika …</div> : failed ? null : <>
  {tab !== 'pravila' ? <>
   <div className="tabs" role="tablist" aria-label="Stanje postavk">{states.map(([id, label, count]) => <button key={id} role="tab" className="tab" aria-selected={filter === id} onClick={() => setFilter(id)}>{label} <span className="count">{count}</span></button>)}</div>
   <div className="data-toolbar"><label className="search-field"><Icon name="search"/><span className="sr-only">Išči po opisu</span><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Išči po opisu …"/></label>
    <span className="result-count">{visible.length === candidates.length ? `${candidates.length} postavk` : `${visible.length} od ${candidates.length} postavk`}</span>
   </div>
   <div className="table-wrap"><table className="data-table"><caption className="sr-only">{title} izbranega podjetja</caption><thead><tr><th>Postavka</th>{tab === 'cenik' ? <><th className="num">Cena / enoto</th><th className="num">Interni strošek</th><th className="num">Dobava</th><th>Stanje</th></> : <><th className="num">Razpoložljivo</th><th className="num">Potrjeno</th></>}<th><span className="sr-only">Dejanja</span></th></tr></thead><tbody>
    {visible.map(item => <tr key={item.id}><td><strong>{item.opis}</strong><span className="cell-detail">{item.vrsta === 'blago' ? 'Blago' : 'Storitev'} · {item.enota}</span></td>
     {tab === 'cenik' ? <><td className="num">{money(item.cena_na_enoto)}</td><td className="num muted" data-label="Strošek">{money(item.strosek_na_enoto)}</td><td className="num" data-label="Dobava">{item.dobavni_rok_dni === null ? <span className="muted" title="Dobavni rok ni določen">—</span> : `${item.dobavni_rok_dni} dni`}</td><td><span className={`status-badge ${!item.aktivna ? 'inactive' : item.potrjeno_ob ? 'confirmed' : 'pending'}`}>{!item.aktivna ? 'Neaktivna' : item.potrjeno_ob ? 'Potrjena' : 'Čaka potrditev'}</span></td></> : <><td className="num">{item.razpolozljiva_kolicina === null ? <span className="muted">Se ne vodi</span> : `${quantity(item.razpolozljiva_kolicina)} ${item.enota}`}</td><td className="num muted" data-label="Potrjeno">{dateTime(item.zaloga_potrjeno_ob)}</td></>}
     <td><div className="row-actions">{tab === 'cenik' ? <>
      {item.aktivna && !item.potrjeno_ob && <IconButton icon="check" label="Potrdi" className="confirm" disabled={busy} onClick={() => void mutate(() => confirmCatalogItem(client, companyId, item.id), 'Postavka je potrjena.')}/>}
      <IconButton icon="pen" label={`Uredi ${item.opis}`} tip="Uredi" disabled={busy} onClick={() => open({ type: 'catalog', item })}/>
     </> : <IconButton icon="pen" label={`Zaloga za ${item.opis}`} tip="Uredi zalogo" disabled={busy || (!item.aktivna && item.razpolozljiva_kolicina === null)} onClick={() => open({ type: 'stock', item })}/>}</div></td></tr>)}
   </tbody></table></div>
   {!visible.length && <div className="full-empty"><Icon name={tab === 'zaloge' ? 'stock' : 'list'}/><h2>{candidates.length ? 'Ni ujemajočih se postavk' : tab === 'zaloge' ? 'Blaga še ni v ceniku' : 'Dodajte prvo postavko'}</h2><p>{candidates.length ? 'Spremenite iskanje ali izbrano stanje.' : tab === 'zaloge' ? 'Zalogo lahko vodite za blago, ki ga najprej dodate v cenik.' : 'Vnesite blago ali storitev, nato preverite podatke in postavko potrdite.'}</p></div>}
   <p className="table-footnote">{tab === 'cenik' ? 'Za pripravo osnutkov so uporabne samo aktivne in potrjene postavke. Zneski so brez DDV.' : 'Neznana zaloga ni enaka ničelni zalogi. Storitve nimajo zaloge.'}</p>
  </> : <>
   {current ? <dl className="kpi-strip" aria-label="Trenutno veljavna pravila"><div><dt>Najmanjša marža</dt><dd>{percent(current.najmanjsa_marza)}</dd></div><div><dt>Največji popust</dt><dd>{percent(current.najvecji_popust)}</dd></div><div><dt>Najdaljši dobavni rok</dt><dd>{current.najdaljsi_rok_dni}<small>dni</small></dd></div><div><dt>Velja od</dt><dd>{new Intl.DateTimeFormat('sl-SI', { dateStyle: 'medium' }).format(new Date(current.velja_od))}</dd></div></dl>
    : rules.length > 0 && <p className="form-note">Trenutno ni veljavnih pravil. Dodajte različico ali preverite obdobje veljavnosti.</p>}
   <div className="section-heading"><h2>Različice pravil</h2><span className="muted">{rules.length} različic</span></div>
   <div className="table-wrap"><table className="data-table rules-table"><caption className="sr-only">Različice prodajnih pravil</caption><thead><tr><th>Velja od</th><th className="num">Velja do</th><th className="num">Najmanjša marža</th><th className="num">Največji popust</th><th className="num">Najdaljša dobava</th><th>Stanje</th></tr></thead><tbody>{rules.map(rule => <tr key={rule.id}><td>{dateTime(rule.velja_od)}</td><td className="num muted" data-label="Do">{rule.velja_do ? dateTime(rule.velja_do) : 'Brez konca'}</td><td className="num" data-label="Marža">{percent(rule.najmanjsa_marza)}</td><td className="num" data-label="Popust">{percent(rule.najvecji_popust)}</td><td className="num" data-label="Dobava">{rule.najdaljsi_rok_dni} dni</td><td><span className={`status-badge ${current?.id === rule.id ? 'confirmed' : new Date(rule.velja_od).getTime() > now ? 'pending' : 'inactive'}`}>{current?.id === rule.id ? 'Veljavna' : new Date(rule.velja_od).getTime() > now ? 'Načrtovana' : 'Pretekla'}</span></td></tr>)}</tbody></table></div>
   {!rules.length && <div className="full-empty"><Icon name="rules"/><h2>Pravila še niso določena</h2><p>Ustvarite različico s prodajnimi pogoji svojega podjetja.</p></div>}
   <p className="table-footnote">Različice ostanejo v zgodovini. Za isti trenutek velja največ ena različica pravil.</p>
  </>}
  </>}
  {editor && <Drawer title={editor.type === 'catalog' ? editor.item ? 'Uredi postavko' : 'Nova postavka' : editor.type === 'stock' ? 'Potrditev zaloge' : 'Nova različica pravil'} onClose={() => { if (!busy) setEditor(null); }}>
   {error && <p role="alert" className="alert">{error}</p>}
   {editor.type === 'catalog' && <CatalogForm item={editor.item} busy={busy} onSave={data => mutate(() => saveCatalogItem(client, companyId, data, editor.item?.id), 'Postavka je shranjena. Preverite jo in potrdite.')}/>}
   {editor.type === 'stock' && <StockForm item={editor.item} busy={busy} onSave={q => mutate(() => saveStock(client, companyId, editor.item.id, q), 'Zaloga je potrjena.')} onRemove={() => mutate(() => removeStock(client, companyId, editor.item.id), 'Podatek o zalogi je odstranjen.')}/>}
   {editor.type === 'rules' && <RulesForm current={current} busy={busy} onSave={data => mutate(() => createRules(client, companyId, data), 'Nova različica pravil je shranjena.')}/>}
  </Drawer>}
 </section>;
}
