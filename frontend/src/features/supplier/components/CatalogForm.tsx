import type { FormEvent } from 'react';
import type { CatalogInput, CatalogItem, Unit, WorkType } from '../types';
import Icon from '../../../components/Icon';
const units: [Unit, string][] = [['m', 'm'], ['m2', 'm²'], ['m3', 'm³'], ['kos', 'kos']];
export default function CatalogForm({ item, trades, onSave, busy }: { item: CatalogItem | null; trades: WorkType[]; onSave: (data: CatalogInput) => Promise<void>; busy: boolean }) {
 async function submit(event: FormEvent<HTMLFormElement>) {
  event.preventDefault(); const data = new FormData(event.currentTarget);
  await onSave({ naziv: String(data.get('naziv')).trim(), opis: String(data.get('opis')).trim(), vrsta_dela_id: String(data.get('vrsta_dela_id')), enota: String(data.get('enota')) as Unit,
   cena_na_enoto: String(data.get('cena')), stopnja_ddv: (Number(data.get('ddv')) / 100).toFixed(6), aktivna: data.get('aktivna') === 'on' });
 }
 return <form className="editor-form" onSubmit={submit}>
  <label>Naziv<input name="naziv" defaultValue={item?.naziv} maxLength={200} required placeholder="Npr. rušenje estriha" autoFocus/></label>
  <label>Opis<textarea name="opis" defaultValue={item?.opis} maxLength={1000} required/></label>
  <label>Vrsta dela<select name="vrsta_dela_id" defaultValue={item?.vrsta_dela_id ?? ''} required><option value="">Izberite vrsto dela</option>{trades.filter(trade => trade.aktivna || trade.id === item?.vrsta_dela_id).map(trade => <option key={trade.id} value={trade.id}>{trade.naziv}</option>)}{item && !trades.some(trade => trade.id === item.vrsta_dela_id) && <option value={item.vrsta_dela_id}>{item.vrsta_dela ?? 'Trenutna vrsta dela'}</option>}</select></label>
  <label>Enota<select name="enota" defaultValue={item?.enota ?? 'm2'}>{units.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
  <div className="form-grid"><label>Cena na enoto (€)<input name="cena" type="number" min="0" max="99999999999999.9999" step="0.0001" defaultValue={item?.cena_na_enoto} required/></label><label>DDV (%)<input name="ddv" type="number" min="0" max="100" step="0.0001" defaultValue={item ? Number(item.stopnja_ddv) * 100 : 22} required/></label></div>
  <label className="checkbox-label"><input name="aktivna" type="checkbox" defaultChecked={item?.aktivna ?? true}/>Aktivna postavka</label>
  <button disabled={busy} type="submit"><Icon name="check"/>{busy ? 'Shranjujem …' : 'Shrani postavko'}</button>
 </form>;
}
