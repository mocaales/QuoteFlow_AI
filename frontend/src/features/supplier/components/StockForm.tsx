import type { FormEvent } from 'react';
import type { Material, Stock } from '../types';
import Icon from '../../../components/Icon';
export default function StockForm({ item, stock, onSave, onRemove, busy }: { item: Material; stock?: Stock; onSave: (lokacija: string, quantity: string) => Promise<void>; onRemove: () => Promise<void>; busy: boolean }) {
 function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const data = new FormData(event.currentTarget); void onSave(String(data.get('lokacija')).trim(), String(data.get('kolicina'))); }
 return <form className="editor-form" onSubmit={submit}><p className="muted">{item.naziv}</p>
  <label>Lokacija<input name="lokacija" defaultValue={stock?.lokacija ?? ''} required readOnly={!!stock} maxLength={200} autoFocus/></label>
  <label>Količina ({item.enota})<input name="kolicina" type="number" min="0" step="0.0001" defaultValue={stock?.kolicina ?? ''} required/></label>
  <p className="form-note">Zaloga se vodi za vsak material in lokacijo posebej.</p>
  <button disabled={busy} type="submit"><Icon name="check"/>Shrani zalogo</button>
  {stock && <button type="button" className="secondary" disabled={busy} onClick={() => void onRemove()}><Icon name="trash"/>Odstrani lokacijo</button>}
 </form>;
}
