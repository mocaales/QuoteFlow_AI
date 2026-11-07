import { useCallback, useEffect, useRef, useState } from 'react';
import type { SupabaseClient } from '@supabase/supabase-js';
import ActionAlert from '../../../components/ActionAlert';
import Drawer from '../../../components/Drawer';
import Icon from '../../../components/Icon';
import IconButton from '../../../components/IconButton';
import { money, quantity } from '../../../utils/format';
import { addItemFromCatalog, addMeasure, createItem, deleteItem, deleteMeasure, getCatalogOptions, getItems, getWorkTypes, updateItem } from '../api';
import { unitLabels } from '../../../utils/units';
import { type CatalogOption, type Item, type ItemsOverview, type WorkTypeOption } from '../types';
import CatalogPick from './CatalogPick';
import ItemForm from './ItemForm';
import MeasuresPanel from './MeasuresPanel';

type Editor = { type: 'item'; item: Item | null } | { type: 'catalog' } | { type: 'measures'; id: string };
export default function ProjectItems({ client, companyId, projectId, locked = false }: { client: SupabaseClient; companyId: string; projectId: string; locked?: boolean }) {
 const [data, setData] = useState<ItemsOverview | null>(null);
 const [trades, setTrades] = useState<WorkTypeOption[]>([]);
 const [catalog, setCatalog] = useState<CatalogOption[] | null>(null);
 const [loading, setLoading] = useState(true);
 const [busy, setBusy] = useState(false);
 const [error, setError] = useState('');
 const [editor, setEditor] = useState<Editor | null>(null);
 const sequence = useRef(0);
 const load = useCallback(async () => {
  const request = ++sequence.current;
  try { const next = await getItems(client, companyId, projectId); if (request === sequence.current) setData(next); }
  finally { if (request === sequence.current) setLoading(false); }
 }, [client, companyId, projectId]);
 useEffect(() => { void load().catch(e => setError(e instanceof Error ? e.message : 'Postavk ni mogoče naložiti.')); return () => { sequence.current++; }; }, [load]);
 useEffect(() => { let live = true; getWorkTypes(client, companyId).then(next => { if (live) setTrades(next); }, () => undefined); return () => { live = false; }; }, [client, companyId]);
 async function mutate(action: () => Promise<unknown>, close = true) {
  setBusy(true); setError('');
  try { await action(); await load(); if (close) setEditor(null); return true; }
  catch (e) { setError(e instanceof Error ? e.message : 'Spremembe ni mogoče shraniti.'); return false; }
  finally { setBusy(false); }
 }
 function open(next: Editor) {
  setError(''); setEditor(next);
  if (next.type === 'catalog' && !catalog) getCatalogOptions(client, companyId).then(setCatalog, e => setError(e instanceof Error ? e.message : 'Cenika ni mogoče naložiti.'));
 }
 const items = data?.postavke ?? [];
 const tradeName = (item: Item) => item.vrsta_dela ?? trades.find(trade => trade.id === item.vrsta_dela_id)?.naziv ?? '–';
 const missing = items.some(item => !item.izmere.length);
 const shown = editor?.type === 'measures' ? items.find(item => item.id === editor.id) : undefined;
 const reason = locked ? 'Ponudba je poslana, postavke so zaklenjene.' : undefined;
 const alert = error && <ActionAlert>{error}</ActionAlert>;
 const title = editor?.type === 'item' ? editor.item ? 'Uredi postavko' : 'Nova postavka' : editor?.type === 'catalog' ? 'Dodaj iz cenika' : shown ? `Izmere: ${shown.naziv}` : '';
 return <section className="quote-editor" aria-busy={loading || busy}>
  <div className="section-heading"><h2>Postavke projekta</h2><div className="heading-actions">
   <button type="button" className="secondary" disabled={loading || busy || locked} title={reason} onClick={() => open({ type: 'catalog' })}><Icon name="list"/>Dodaj iz cenika</button>
   <button type="button" disabled={loading || busy || locked} title={reason} onClick={() => open({ type: 'item', item: null })}><Icon name="plus"/>Nova postavka</button></div></div>
  <p className="muted">Postavke se pošljejo stranki v ponudbi. Vsaka postavka mora imeti vsaj eno izmero.</p>
  {locked && <p className="form-note">Ponudba je poslana, postavke so zaklenjene. Za spremembe pripravite novo različico.</p>}
  {!editor && error && <p role="alert" className="alert">{error}<IconButton icon="refresh" label="Poskusi znova" className="on-alert" onClick={() => { setError(''); void load().catch(e => setError(e instanceof Error ? e.message : 'Postavk ni mogoče naložiti.')); }}/></p>}
  {loading ? <div className="loading-state" role="status">Nalagam postavke …</div> : data && (!items.length ? <div className="empty-state"><p>Projekt še nima postavk.</p><p className="muted">Dodajte postavko ali jo prevzemite iz cenika.</p></div> : <>
   {missing && <p className="form-note">Ponudbe ni mogoče poslati, dokler vse postavke nimajo izmer.</p>}
   <div className="table-wrap"><table className="data-table items-table"><caption className="sr-only">Postavke projekta</caption><thead><tr><th>Postavka</th><th>Vrsta dela</th><th className="num">Izmera</th><th className="num">Neto</th><th className="num">Skupaj</th><th><span className="sr-only">Dejanja</span></th></tr></thead><tbody>
    {items.map(item => { const none = !item.izmere.length; return <tr key={item.id}><td><strong>{item.naziv}</strong>{item.opis && <span className="cell-detail">{item.opis}</span>}</td><td data-label="Vrsta dela">{tradeName(item)}</td>
     <td className="num" data-label="Izmera">{none ? <span className="status-badge pending">Brez izmer</span> : `${quantity(item.izmera_skupaj)} ${unitLabels[item.enota]}`}</td>
     <td className="num" data-label="Neto">{none ? <span className="muted">–</span> : money(item.neto)}</td><td className="num" data-label="Skupaj">{none ? <span className="muted">–</span> : money(item.koncna_cena)}</td>
     <td><IconButton icon="ruler" label={`Izmere ${item.naziv}`} tip="Izmere" disabled={busy} onClick={() => open({ type: 'measures', id: item.id })}/>
      <IconButton icon="pen" label={`Uredi ${item.naziv}`} tip={reason ?? 'Uredi'} disabled={busy || locked} onClick={() => open({ type: 'item', item })}/>
      <IconButton icon="trash" label={`Odstrani ${item.naziv}`} tip={reason ?? 'Odstrani'} disabled={busy || locked} onClick={() => void mutate(() => deleteItem(client, companyId, projectId, item.id), false)}/></td></tr>; })}
   </tbody></table></div>
   <dl className="kpi-strip" role="group" aria-label="Vsote postavk"><div><dt>Neto</dt><dd>{money(data.neto)}</dd></div><div><dt>DDV</dt><dd>{money(data.ddv)}</dd></div><div><dt>Skupaj</dt><dd>{money(data.skupaj)}</dd></div></dl></>)}
  {editor && (editor.type !== 'measures' || shown) && <Drawer title={title} onClose={() => { if (!busy || editor.type === 'measures') setEditor(null); }}>
   {alert}
   {editor.type === 'item' && <ItemForm key={editor.item?.id ?? 'new'} item={editor.item} trades={trades} busy={busy} onSave={async input => { await mutate(() => editor.item ? updateItem(client, companyId, projectId, editor.item.id, input) : createItem(client, companyId, projectId, input)); }}/>}
   {editor.type === 'catalog' && <CatalogPick options={catalog} busy={busy} onSave={async input => { await mutate(() => addItemFromCatalog(client, companyId, projectId, input)); }}/>}
   {editor.type === 'measures' && shown && <MeasuresPanel item={shown} locked={locked} busy={busy} onAdd={input => mutate(() => addMeasure(client, companyId, projectId, shown.id, input), false)} onRemove={id => void mutate(() => deleteMeasure(client, companyId, projectId, shown.id, id), false)}/>}
  </Drawer>}
 </section>;
}
