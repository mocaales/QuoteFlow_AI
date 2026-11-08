import { useState, type FormEvent } from 'react';
import type { SupabaseClient } from '@supabase/supabase-js';
import ActionAlert from '../../../components/ActionAlert';
import Drawer from '../../../components/Drawer';
import Icon from '../../../components/Icon';
import IconButton from '../../../components/IconButton';
import { money, quantity } from '../../../utils/format';
import { removeWorkTypeMaterial, saveWorkType, saveWorkTypeMaterial } from '../api';
import type { Material, WorkType, WorkTypeInput } from '../types';

const count = (n: number) => n === 0 ? 'Brez materialov' : `${n} ${n === 1 ? 'material' : n === 2 ? 'materiala' : n < 5 ? 'materiali' : 'materialov'}`;
const workers = (n: number) => `${n} ${n === 1 ? 'delavec' : n === 2 ? 'delavca' : n < 5 ? 'delavci' : 'delavcev'}`;
const input = (w: WorkType, aktivna: boolean): WorkTypeInput => ({ naziv: w.naziv, opis: w.opis, urna_postavka: w.urna_postavka, stevilo_ur: w.stevilo_ur, stevilo_delavcev: w.stevilo_delavcev, aktivna });
const cents = (n: number) => String(Math.round(n * 100) / 100);

function Form({ work, busy, onSave }: { work: WorkType | null; busy: boolean; onSave: (data: WorkTypeInput) => Promise<void> }) {
 const [f, setF] = useState({ urna: work ? String(Number(work.urna_postavka)) : '0', ure: work ? String(Number(work.stevilo_ur)) : '0', delavci: work ? String(work.stevilo_delavcev) : '1' });
 const set = (key: keyof typeof f) => (event: { target: { value: string } }) => setF(previous => ({ ...previous, [key]: event.target.value }));
 async function submit(event: FormEvent<HTMLFormElement>) {
  event.preventDefault(); const data = new FormData(event.currentTarget);
  await onSave({ naziv: String(data.get('naziv')).trim(), opis: String(data.get('opis')).trim(), urna_postavka: f.urna || '0', stevilo_ur: f.ure || '0', stevilo_delavcev: Number(f.delavci), aktivna: work?.aktivna ?? true });
 }
 // Preview only: the server stores cena_dela.
 const price = (Number(f.urna) || 0) * (Number(f.ure) || 0) * (Number(f.delavci) || 0);
 return <form className="editor-form" onSubmit={submit}>
  <label>Naziv<input name="naziv" defaultValue={work?.naziv} maxLength={200} required autoFocus/></label>
  <label>Opis<textarea name="opis" defaultValue={work?.opis} maxLength={2000}/></label>
  <div className="form-grid"><label>Urna postavka (€)<input type="number" min="0" max="10000" step="0.0001" value={f.urna} onChange={set('urna')}/></label><label>Število ur<input type="number" min="0" max="100000" step="0.0001" value={f.ure} onChange={set('ure')}/></label></div>
  <label>Število delavcev<input type="number" min="1" max="1000" step="1" required value={f.delavci} onChange={set('delavci')}/></label>
  <p className="field-help">Za delo brez stroška dela pustite 0.</p>
  <dl className="calc-preview" role="group" aria-label="Predogled cene dela"><div><dt>Cena dela</dt><dd>{money(cents(price))}</dd></div></dl>
  <button type="submit" disabled={busy}><Icon name="check"/>{busy ? 'Shranjujem …' : 'Shrani vrsto dela'}</button>
 </form>;
}

export default function WorkTypes({ client, companyId, workTypes, materials, failed, onChange, busy: parentBusy }: { client: SupabaseClient; companyId: string; workTypes: WorkType[]; materials: Material[]; failed: boolean; onChange: () => Promise<void>; busy: boolean }) {
 const [editor, setEditor] = useState<{ id: string | null; materials?: boolean } | null>(null);
 const [busy, setBusy] = useState(false);
 const [error, setError] = useState('');
 const work = editor?.id ? workTypes.find(entry => entry.id === editor.id) ?? null : null;
 async function run(action: () => Promise<unknown>) {
  setBusy(true); setError('');
  try { await action(); await onChange(); return true; }
  catch (e) { setError(e instanceof Error ? e.message : 'Spremembe ni mogoče shraniti.'); return false; }
  finally { setBusy(false); }
 }
 async function add(event: FormEvent<HTMLFormElement>) {
  event.preventDefault(); const form = event.currentTarget, data = new FormData(form);
  if (await run(() => saveWorkTypeMaterial(client, companyId, work!.id, String(data.get('material')), String(data.get('kolicina'))))) form.reset();
 }
 const free = materials.filter(material => material.aktiven && !work?.materiali.some(line => line.material_id === material.id));
 const off = busy || parentBusy;
 return <>
  <div className="data-toolbar"><span className="result-count">{workTypes.length} vrst dela</span><button type="button" disabled={off} onClick={() => { setError(''); setEditor({ id: null }); }}><Icon name="plus"/>Nova vrsta dela</button></div>
  {!editor && error && <ActionAlert>{error}</ActionAlert>}
  {workTypes.length ? <div className="table-wrap"><table className="data-table"><caption className="sr-only">Vrste dela izbranega podjetja</caption><thead><tr><th>Vrsta dela</th><th>Stanje</th><th className="num">Delo</th><th className="num">Materiali</th><th><span className="sr-only">Dejanja</span></th></tr></thead><tbody>
   {workTypes.map(entry => <tr key={entry.id}><td><strong>{entry.naziv}</strong>{entry.opis && <span className="cell-detail">{entry.opis}</span>}</td>
    <td><span className={`status-badge ${entry.aktivna ? 'confirmed' : 'inactive'}`}>{entry.aktivna ? 'Aktivna' : 'Neaktivna'}</span></td>
    <td className="num"><span className="num">Cena dela {money(entry.cena_dela)}</span><span className="cell-detail">{money(entry.urna_postavka)} × {quantity(entry.stevilo_ur)} h, {workers(entry.stevilo_delavcev)}</span></td>
    <td className="num" data-label="Materiali">{count(entry.materiali.length)}</td>
    <td><IconButton icon="list" label={`Materiali ${entry.naziv}`} tip="Materiali" disabled={off} onClick={() => { setError(''); setEditor({ id: entry.id, materials: true }); }}/><IconButton icon="pen" label={`Uredi ${entry.naziv}`} tip="Uredi" disabled={off} onClick={() => { setError(''); setEditor({ id: entry.id }); }}/>
     {entry.aktivna ? <IconButton icon="revoke" label={`Deaktiviraj ${entry.naziv}`} tip="Deaktiviraj" disabled={off} onClick={() => void run(() => saveWorkType(client, companyId, input(entry, false), entry.id))}/>
      : <IconButton icon="restore" label={`Aktiviraj ${entry.naziv}`} tip="Aktiviraj" disabled={off} onClick={() => void run(() => saveWorkType(client, companyId, input(entry, true), entry.id))}/>}</td></tr>)}
  </tbody></table></div> : !failed && <div className="full-empty"><Icon name="list"/><h2>Dodajte prvo vrsto dela</h2><p>Vrsta dela določa urno postavko, ure in delavce, ki se prevzamejo v postavke projekta.</p></div>}
  {editor && <Drawer title={editor.materials ? `Materiali: ${work?.naziv ?? ''}` : editor.id ? 'Uredi vrsto dela' : 'Nova vrsta dela'} onClose={() => { if (!off) setEditor(null); }}>
   {error && <ActionAlert>{error}</ActionAlert>}
   {editor.materials ? work && <div className="editor-form">
    <p className="field-help">Materiali so interni. Stranka jih ne vidi, v ceno na enoto pa niso všteti.</p>
    {work.materiali.length ? <ul className="material-list">{work.materiali.map(line => <li key={line.material_id} className="material-row"><strong>{`${line.naziv} · ${quantity(line.kolicina_na_enoto)} ${line.enota} na enoto`}</strong>
     <input className="qty-input" key={line.kolicina_na_enoto} type="number" min="0.0001" step="0.0001" aria-label={`Količina ${line.naziv}`} defaultValue={String(Number(line.kolicina_na_enoto))} disabled={busy}
      onBlur={event => { const value = event.currentTarget.value; if (value && Number(value) !== Number(line.kolicina_na_enoto)) void run(() => saveWorkTypeMaterial(client, companyId, work.id, line.material_id, value)); }}/>
     <IconButton icon="trash" label={`Odstrani ${line.naziv}`} tip="Odstrani" disabled={busy} onClick={() => void run(() => removeWorkTypeMaterial(client, companyId, work.id, line.material_id))}/></li>)}</ul> : <p className="muted">Brez materialov</p>}
    <form className="editor-form" onSubmit={add}>
     <label>Material<select name="material" required defaultValue=""><option value="" disabled>Izberite material</option>{free.map(material => <option key={material.id} value={material.id}>{material.naziv} ({material.sifra}, {material.enota})</option>)}</select></label>
     <label>Količina na enoto<input name="kolicina" type="number" min="0.0001" step="0.0001" required/></label>
     <button type="submit" className="secondary" disabled={busy}><Icon name="plus"/>Dodaj material</button>
    </form></div>
   : <Form key={editor.id ?? 'new'} work={work} busy={busy} onSave={async data => {
    setBusy(true); setError('');
    try { await saveWorkType(client, companyId, data, editor.id ?? undefined); await onChange(); setEditor(null); }
    catch (e) { setError(e instanceof Error ? e.message : 'Spremembe ni mogoče shraniti.'); }
    finally { setBusy(false); }
   }}/>}
  </Drawer>}
 </>;
}
