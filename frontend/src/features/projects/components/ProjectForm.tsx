import type { FormEvent } from 'react';
import Icon from '../../../components/Icon';
import type { Project, ProjectCreate } from '../types';

export default function ProjectForm({ item, busy, onSave }: { item?: Project; busy: boolean; onSave: (data: ProjectCreate, reset: () => void) => Promise<void> }) {
 function submit(event: FormEvent<HTMLFormElement>) {
  event.preventDefault(); const form = event.currentTarget, data = new FormData(form), text = (name: string) => String(data.get(name) ?? '').trim();
  void onSave({ e_posta_stranke: text('e_posta_stranke'), naziv: text('naziv'), opis: text('opis'), lokacija_izvedbe: text('lokacija_izvedbe') }, () => form.reset());
 }
 return <form className="editor-form" onSubmit={submit}>
  <div className="form-grid">
  {!item && <label>E-pošta stranke<input name="e_posta_stranke" type="email" required maxLength={320} autoComplete="off"/></label>}
  <label>Naziv<input name="naziv" defaultValue={item?.naziv} required maxLength={200} autoFocus={!!item}/></label>
  <label>Lokacija izvedbe<input name="lokacija_izvedbe" defaultValue={item?.lokacija_izvedbe} maxLength={300}/></label>
  <label>Opis<textarea name="opis" defaultValue={item?.opis} maxLength={2000}/></label>
  </div>
  <button type="submit" disabled={busy}><Icon name={item ? 'check' : 'plus'}/>{item ? 'Shrani projekt' : 'Ustvari projekt'}</button>
 </form>;
}
