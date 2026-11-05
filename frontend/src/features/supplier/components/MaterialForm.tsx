import type { FormEvent } from 'react';
import type { Material, MaterialInput, MaterialKind } from '../types';
import Icon from '../../../components/Icon';
export default function MaterialForm({ item, kinds, busy, onSave }: { item: Material | null; kinds: MaterialKind[]; busy: boolean; onSave: (data: MaterialInput) => Promise<void> }) {
 function submit(event: FormEvent<HTMLFormElement>) {
  event.preventDefault(); const data = new FormData(event.currentTarget);
  void onSave({ vrsta_materiala_id: String(data.get('vrsta')), sifra: String(data.get('sifra')).trim(), naziv: String(data.get('naziv')).trim(), enota: String(data.get('enota')).trim(), cena_na_enoto: String(data.get('cena')), aktiven: data.get('aktiven') === 'on' });
 }
 return <form className="editor-form" onSubmit={submit}>
  <label>Naziv<input name="naziv" defaultValue={item?.naziv} required maxLength={200} autoFocus/></label>
  <label>Šifra<input name="sifra" defaultValue={item?.sifra} required maxLength={100}/></label>
  <label>Vrsta materiala<select name="vrsta" defaultValue={item?.vrsta_materiala_id ?? ''} required><option value="" disabled>Izberite vrsto</option>{kinds.map(kind => <option key={kind.id} value={kind.id}>{kind.naziv}</option>)}</select></label>
  <label>Enota<input name="enota" defaultValue={item?.enota ?? 'kg'} required maxLength={30}/></label>
  <label>Cena na enoto (€)<input name="cena" type="number" min="0" step="0.0001" defaultValue={item?.cena_na_enoto} required/></label>
  <label className="checkbox-label"><input type="checkbox" name="aktiven" defaultChecked={item?.aktiven ?? true}/>Aktiven material</label>
  <button disabled={busy || !kinds.length}><Icon name="check"/>Shrani material</button>
 </form>;
}
