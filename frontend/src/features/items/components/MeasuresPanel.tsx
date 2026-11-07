import { useRef, useState, type FormEvent } from 'react';
import Icon from '../../../components/Icon';
import IconButton from '../../../components/IconButton';
import { quantity } from '../../../utils/format';
import { unitLabels } from '../../../utils/units';
import { type Item, type MeasureInput } from '../types';

const fields: Record<string, ('dolzina' | 'visina' | 'sirina')[]> = { m: ['dolzina'], m2: ['dolzina', 'visina'], m3: ['dolzina', 'visina', 'sirina'], kos: [] };
const names = { dolzina: 'Dolžina', visina: 'Višina', sirina: 'Širina' };
const empty = { dolzina: '', visina: '', sirina: '', kosi: '1', odstej: false };
// Preview only: the server computes and stores the authoritative values.
export default function MeasuresPanel({ item, locked, busy, onAdd, onRemove }: { item: Item; locked: boolean; busy: boolean; onAdd: (data: MeasureInput) => Promise<boolean>; onRemove: (id: string) => void }) {
 const [v, setV] = useState(empty);
 const form = useRef<HTMLFormElement>(null);
 const unit = unitLabels[item.enota], used = fields[item.enota] ?? [];
 const ready = used.every(key => Number(v[key]) > 0) && Number(v.kosi) > 0;
 const value = ready ? used.reduce((product, key) => product * Number(v[key]), Number(v.kosi)) : null;
 const total = Number(item.izmera_skupaj) + (value === null ? 0 : (v.odstej ? -value : value));
 const negative = value !== null && total < 0;
 const text = (n: number) => `${quantity(String(Math.round(n * 10000) / 10000))} ${unit}`;
 async function submit(event: FormEvent<HTMLFormElement>) {
  event.preventDefault(); if (negative) return;
  const data: MeasureInput = { odstej: v.odstej, kosi: v.kosi };
  for (const key of used) data[key] = v[key];
  if (await onAdd(data)) { setV(empty); form.current?.querySelector<HTMLInputElement>('input:not([type=checkbox])')?.focus(); }
 }
 return <div className="editor-form">
  <p className="muted">Enota postavke: {unit}</p>
  {item.izmere.length ? <ul className="measure-list">{item.izmere.map(m => {
   const dims = [m.dolzina, m.visina, m.sirina].filter((x): x is string => x !== null).map(x => quantity(x)).join(' × '), pieces = Number(m.kosi) !== 1 ? `${dims ? ', ' : ''}${quantity(m.kosi)} kosi` : '';
   return <li key={m.id} className="measure-row"><span className="measure-no">{m.zaporedje}</span><span className="measure-sign">{m.odstej ? '−' : '+'}</span><span className="measure-value">{quantity(m.vrednost)} {unit}</span><span className="measure-dims">{dims}{pieces}</span>
    {!locked && <IconButton icon="trash" label={`Odstrani izmero ${m.zaporedje}`} tip="Odstrani" disabled={busy} onClick={() => onRemove(m.id)}/>}</li>;
  })}</ul> : <p className="muted">Postavka še nima izmer. Brez izmer ponudbe ni mogoče poslati.</p>}
  {!locked && <form className="editor-form" ref={form} onSubmit={submit}>
   <h3>Nova izmera</h3>
   <div className="measure-fields">
    <label className="checkbox-label"><input type="checkbox" checked={v.odstej} onChange={event => setV({ ...v, odstej: event.target.checked })}/>Odštej</label>
    {used.map(key => <label key={key}>{names[key]}<span className="input-suffix"><input aria-label={names[key]} type="number" min="0.0001" max="100000" step="0.0001" value={v[key]} onChange={event => setV({ ...v, [key]: event.target.value })}/><span className="unit-suffix" aria-hidden="true">m</span></span></label>)}
    <label>Kosi<input type="number" min="1" max="100000" step="1" required value={v.kosi} onChange={event => setV({ ...v, kosi: event.target.value })}/></label>
   </div>
   <dl className="calc-preview" role="group" aria-label="Izračun izmere">{value !== null && <div><dt>Vrednost izmere</dt><dd>{text(value)}</dd></div>}<div><dt>Skupaj izmer</dt><dd>{text(total)}</dd></div></dl>
   {negative && <p className="field-error">Izmere bi dale negativno količino.</p>}
   <button type="submit" disabled={busy || negative || !ready}><Icon name="plus"/>Dodaj izmero</button>
  </form>}
 </div>;
}
