import { useState, type FormEvent } from 'react';
import type { CatalogInput, CatalogItem } from '../types';
import Icon from '../../../components/Icon';
export default function CatalogForm({ item, onSave, busy }: { item: CatalogItem | null; onSave: (data: CatalogInput) => Promise<void>; busy: boolean }) {
 const [kind, setKind] = useState(item?.vrsta ?? 'blago');
 async function submit(event: FormEvent<HTMLFormElement>) {
  event.preventDefault(); const data = new FormData(event.currentTarget);
  await onSave({ vrsta: kind, opis: String(data.get('opis')).trim(), enota: String(data.get('enota')).trim(),
   cena_na_enoto: String(data.get('cena')), strosek_na_enoto: String(data.get('strosek')),
   dobavni_rok_dni: data.get('rok') === '' ? null : Number(data.get('rok')), aktivna: data.get('aktivna') === 'on' });
 }
 return <form className="editor-form" onSubmit={submit}>
  <label>Vrsta<select value={kind} onChange={e => setKind(e.target.value as typeof kind)}><option value="blago">Blago</option><option value="storitev">Storitev</option></select></label>
  <label>Opis<input name="opis" defaultValue={item?.opis} maxLength={1000} required placeholder="Npr. industrijski ležaj 6205" autoFocus/></label>
  <div className="form-grid"><label>Enota<input name="enota" defaultValue={item?.enota ?? 'kos'} maxLength={30} required/></label><label>Dobavni rok (dni)<input name="rok" type="number" min="0" max="3650" step="1" defaultValue={item?.dobavni_rok_dni ?? ''} placeholder="Ni določen"/></label></div>
  <div className="form-grid"><label>Cena na enoto (€)<input name="cena" type="number" min="0" max="99999999999999.9999" step="0.0001" defaultValue={item?.cena_na_enoto} required/></label><label>Strošek na enoto (€)<input name="strosek" type="number" min="0" max="99999999999999.9999" step="0.0001" defaultValue={item?.strosek_na_enoto} required/></label></div>
  <label className="checkbox-label"><input name="aktivna" type="checkbox" defaultChecked={item?.aktivna ?? true}/>Aktivna postavka</label>
  <p className="form-note">Po shranjevanju postavko izrecno potrdite. Sprememba vrste ali enote odstrani obstoječo zalogo.</p>
  <button disabled={busy} type="submit"><Icon name="check"/>{busy ? 'Shranjujem …' : 'Shrani postavko'}</button>
 </form>;
}
