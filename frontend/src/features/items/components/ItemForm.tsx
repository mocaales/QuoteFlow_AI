import { useState, type FormEvent } from 'react';
import Icon from '../../../components/Icon';
import { money } from '../../../utils/format';
import { fraction, percentValue } from '../percent';
import { unitLabels } from '../../../utils/units';
import { type Item, type ItemInput, type Unit, type WorkTypeOption } from '../types';

const units = Object.keys(unitLabels) as Unit[];
const num = (value: string) => Number(value) || 0;
const cents = (value: number) => String(Math.round(value * 100) / 100);
// Preview only: the server stores the authoritative amounts (formula A, rounded per line).
export default function ItemForm({ item, trades, busy, onSave }: { item: Item | null; trades: WorkTypeOption[]; busy: boolean; onSave: (data: ItemInput) => Promise<void> }) {
 const [f, setF] = useState({ vrsta: item?.vrsta_dela_id ?? '', enota: item?.enota ?? 'm2', cena: item?.cena_na_enoto ? String(Number(item.cena_na_enoto)) : '', kolicina: item ? String(Number(item.kolicina)) : '1',
  popust: item ? percentValue(item.popust) : '0', ddv: item ? percentValue(item.stopnja_ddv) : '22', urna: item ? String(Number(item.urna_postavka)) : '', ure: item ? String(Number(item.stevilo_ur)) : '', delavci: item ? String(item.stevilo_delavcev) : '' });
 const set = (key: keyof typeof f) => (event: { target: { value: string } }) => setF(previous => ({ ...previous, [key]: event.target.value }));
 const current = trades.find(trade => trade.id === item?.vrsta_dela_id);
 const options = trades.filter(trade => trade.aktivna || trade.id === item?.vrsta_dela_id);
 function pick(id: string) {
  const trade = trades.find(entry => entry.id === id);
  setF(previous => ({ ...previous, vrsta: id, ...(trade ? { urna: String(Number(trade.urna_postavka)), ure: String(Number(trade.stevilo_ur)), delavci: String(trade.stevilo_delavcev) } : {}) }));
 }
 const delo = num(f.urna) * num(f.ure) * num(f.delavci);
 const measured = item ? Number(item.izmera_skupaj) > 0 : false;
 const neto = measured ? Math.round(((Number(item!.izmera_skupaj) * num(f.kolicina) * num(f.cena) + delo) * (1 - num(f.popust) / 100)) * 100) / 100 : null;
 const ddv = neto === null ? null : Math.round(neto * num(f.ddv)) / 100;
 async function submit(event: FormEvent<HTMLFormElement>) {
  event.preventDefault(); const data = new FormData(event.currentTarget);
  await onSave({ naziv: String(data.get('naziv')).trim(), opis: String(data.get('opis')).trim(), vrsta_dela_id: f.vrsta, enota: f.enota as Unit, cena_na_enoto: f.cena, kolicina: f.kolicina, popust: fraction(f.popust), stopnja_ddv: fraction(f.ddv),
   urna_postavka: f.urna, stevilo_ur: f.ure, stevilo_delavcev: f.delavci ? Number(f.delavci) : null });
 }
 return <form className="editor-form" onSubmit={submit}>
  <label>Naziv<input name="naziv" defaultValue={item?.naziv} maxLength={200} required autoFocus/></label>
  <label>Opis<textarea name="opis" defaultValue={item?.opis} maxLength={2000}/></label>
  <label>Vrsta dela<select value={f.vrsta} required onChange={event => pick(event.target.value)}><option value="">Izberite vrsto dela</option>{options.map(trade => <option key={trade.id} value={trade.id}>{trade.naziv}</option>)}</select></label>
  {current && !current.aktivna ? <p className="field-help">Vrsta dela je neaktivna. Ni je mogoče izbrati pri novih postavkah.</p> : f.vrsta && <p className="field-help">Vrednosti dela so prevzete iz vrste dela in jih lahko spremenite.</p>}
  <div className="form-grid"><label>Enota<select value={f.enota} onChange={set('enota')}>{units.map(unit => <option key={unit} value={unit}>{unitLabels[unit]}</option>)}</select></label>
   <label>Cena na enoto<input type="number" min="0" max="1000000" step="0.0001" required value={f.cena} onChange={set('cena')}/></label></div>
  <div className="form-grid"><label>Količina<input type="number" min="0.0001" max="1000000" step="0.0001" required value={f.kolicina} onChange={set('kolicina')}/></label>
   <label>Popust (%)<input type="number" min="0" max="99.9999" step="0.0001" value={f.popust} onChange={set('popust')}/></label></div>
  <p className="field-help">Količina je množitelj skupne izmere. Običajno 1.</p>
  <label>Stopnja DDV (%)<input type="number" min="0" max="100" step="0.0001" required value={f.ddv} onChange={set('ddv')}/></label>
  <h3>Delo</h3>
  <div className="form-grid"><label>Urna postavka (€)<input type="number" min="0" max="10000" step="0.0001" required value={f.urna} onChange={set('urna')}/></label>
   <label>Število ur<input type="number" min="0" max="100000" step="0.0001" required value={f.ure} onChange={set('ure')}/></label></div>
  <label>Število delavcev<input type="number" min="1" max="1000" step="1" required value={f.delavci} onChange={set('delavci')}/></label>
  <p className="field-help">Za delo brez stroška dela pustite 0.</p>
  {!item && <p className="form-note">Izmere dodate po shranitvi postavke.</p>}
  <dl className="calc-preview" role="group" aria-label="Predogled izračuna"><div><dt>Delo</dt><dd>{money(cents(delo))}</dd></div><div><dt>Neto</dt><dd>{neto === null ? '–' : money(cents(neto))}</dd></div><div><dt>DDV</dt><dd>{ddv === null ? '–' : money(cents(ddv))}</dd></div><div><dt>Skupaj</dt><dd>{neto === null || ddv === null ? '–' : money(cents(neto + ddv))}</dd></div></dl>
  {!measured && <p className="field-help">Neto se izračuna, ko dodate izmere.</p>}
  <button type="submit" disabled={busy}><Icon name="check"/>{busy ? 'Shranjujem …' : 'Shrani postavko'}</button>
 </form>;
}
