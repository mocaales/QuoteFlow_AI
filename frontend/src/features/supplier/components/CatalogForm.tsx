import type { FormEvent } from 'react';
import type { CatalogInput, CatalogItem } from '../types';
import Icon from '../../../components/Icon';
export default function CatalogForm({ item, onSave, busy }: { item: CatalogItem | null; onSave: (data: CatalogInput) => Promise<void>; busy: boolean }) {
 async function submit(event: FormEvent<HTMLFormElement>) {
  event.preventDefault(); const data = new FormData(event.currentTarget);
  await onSave({ naziv: String(data.get('naziv')).trim(), opis: String(data.get('opis')).trim(), vrsta_dela: String(data.get('vrsta_dela')).trim(), enota: String(data.get('enota')).trim(),
   cena_na_enoto: String(data.get('cena')), stopnja_ddv: (Number(data.get('ddv')) / 100).toFixed(6), aktivna: data.get('aktivna') === 'on' });
 }
 return <form className="editor-form" onSubmit={submit}>
  <label>Naziv<input name="naziv" defaultValue={item?.naziv} maxLength={200} required placeholder="Npr. rušenje estriha" autoFocus/></label>
  <label>Opis<textarea name="opis" defaultValue={item?.opis} maxLength={1000} required/></label>
  <label>Vrsta dela<input name="vrsta_dela" defaultValue={item?.vrsta_dela} maxLength={100} required/></label>
  <label>Enota<input name="enota" defaultValue={item?.enota ?? 'm²'} maxLength={30} required/></label>
  <div className="form-grid"><label>Cena na enoto (€)<input name="cena" type="number" min="0" max="99999999999999.9999" step="0.0001" defaultValue={item?.cena_na_enoto} required/></label><label>DDV (%)<input name="ddv" type="number" min="0" max="100" step="0.0001" defaultValue={item ? Number(item.stopnja_ddv) * 100 : 22} required/></label></div>
  <label className="checkbox-label"><input name="aktivna" type="checkbox" defaultChecked={item?.aktivna ?? true}/>Aktivna postavka</label>
  <button disabled={busy} type="submit"><Icon name="check"/>{busy ? 'Shranjujem …' : 'Shrani postavko'}</button>
 </form>;
}
