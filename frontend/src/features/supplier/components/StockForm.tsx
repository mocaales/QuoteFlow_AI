import type { FormEvent } from 'react';
import type { CatalogItem } from '../types';
import Icon from '../../../components/Icon';
export default function StockForm({ item, onSave, onRemove, busy }: { item: CatalogItem; onSave: (quantity: string) => Promise<void>; onRemove: () => Promise<void>; busy: boolean }) {
 function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); void onSave(String(new FormData(event.currentTarget).get('kolicina'))); }
 return <form className="editor-form" onSubmit={submit}><p className="muted">{item.opis}</p>
  <label>Razpoložljiva količina ({item.enota})<input name="kolicina" type="number" min="0" step="0.0001" defaultValue={item.razpolozljiva_kolicina ?? ''} required autoFocus/></label>
  <p className="form-note">Nič pomeni potrjeno prazno zalogo. Če zaloge ne vodite, odstranite podatek.</p>
  <button disabled={busy || !item.aktivna} type="submit"><Icon name="check"/>Potrdi zalogo</button>
  {item.razpolozljiva_kolicina !== null && <button type="button" className="secondary" disabled={busy} onClick={() => void onRemove()}><Icon name="trash"/>Prenehaj voditi zalogo</button>}
 </form>;
}
