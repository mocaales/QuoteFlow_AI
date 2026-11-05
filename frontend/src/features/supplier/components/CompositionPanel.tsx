import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import type { SupabaseClient } from '@supabase/supabase-js';
import Icon from '../../../components/Icon';
import IconButton from '../../../components/IconButton';
import { getComposition, removeCompositionLine, saveCompositionLine } from '../api';
import type { CatalogItem, CompositionLine, Material } from '../types';
import { quantity } from '../../../utils/format';

export default function CompositionPanel({ client, companyId, item, materials }: { client: SupabaseClient; companyId: string; item: CatalogItem; materials: Material[] }) {
 const [lines, setLines] = useState<CompositionLine[]>([]);
 const [loading, setLoading] = useState(true);
 const [busy, setBusy] = useState(false);
 const [error, setError] = useState('');
 const sequence = useRef(0);
 const load = useCallback(async () => {
  const request = ++sequence.current;
  try { const next = await getComposition(client, companyId, item.id); if (request === sequence.current) setLines(next); }
  finally { if (request === sequence.current) setLoading(false); }
 }, [client, companyId, item.id]);
 useEffect(() => { void load().catch(e => setError(e instanceof Error ? e.message : 'Sestave ni mogoče naložiti.')); return () => { sequence.current++; }; }, [load]);
 async function mutate(action: () => Promise<unknown>) {
  setBusy(true); setError('');
  try { await action(); await load(); return true; }
  catch (e) { setError(e instanceof Error ? e.message : 'Spremembe ni mogoče shraniti.'); return false; }
  finally { setBusy(false); }
 }
 async function add(event: FormEvent<HTMLFormElement>) {
  event.preventDefault(); const form = event.currentTarget, data = new FormData(form);
  if (await mutate(() => saveCompositionLine(client, companyId, item.id, String(data.get('material')), String(data.get('kolicina'))))) form.reset();
 }
 const free = materials.filter(material => material.aktiven && !lines.some(line => line.material_id === material.id));
 return <div className="editor-form">
  <p className="muted">Material za 1 {item.enota} dela. Materialna sestava je neobvezna.</p>
  {error && <p role="alert" className="alert">{error}</p>}
  {loading ? <p role="status" className="loading-state">Nalagam sestavo …</p> : lines.length ? <div className="table-wrap"><table className="data-table"><caption className="sr-only">Materialna sestava postavke {item.naziv}</caption><thead><tr><th>Material</th><th className="num">Količina</th><th><span className="sr-only">Dejanja</span></th></tr></thead><tbody>
   {lines.map(line => <tr key={line.material_id}><td><strong>{line.naziv} · {quantity(line.kolicina_na_enoto)} {line.enota} na {item.enota}</strong><span className="cell-detail">{line.sifra}{line.aktiven ? '' : ' · neaktiven'}</span></td>
    <td className="num"><input className="qty-input" key={line.kolicina_na_enoto} type="number" min="0" step="0.0001" aria-label={`Količina ${line.naziv}`} defaultValue={line.kolicina_na_enoto} disabled={busy}
     onBlur={event => { const value = event.currentTarget.value; if (value && value !== line.kolicina_na_enoto) void mutate(() => saveCompositionLine(client, companyId, item.id, line.material_id, value)); }}/></td>
    <td><IconButton icon="trash" label={`Odstrani ${line.naziv}`} tip="Odstrani" disabled={busy} onClick={() => void mutate(() => removeCompositionLine(client, companyId, item.id, line.material_id))}/></td></tr>)}
  </tbody></table></div> : <p className="muted">Brez materialne sestave</p>}
  <form className="editor-form" onSubmit={add}>
   <label>Material<select name="material" required defaultValue=""><option value="" disabled>Izberite material</option>{free.map(material => <option key={material.id} value={material.id}>{material.naziv} ({material.sifra}, {material.enota})</option>)}</select></label>
   <label>Količina na enoto<input name="kolicina" type="number" min="0.0001" step="0.0001" required/></label>
   <button type="submit" disabled={busy || loading}><Icon name="plus"/>Dodaj v sestavo</button>
  </form>
 </div>;
}
