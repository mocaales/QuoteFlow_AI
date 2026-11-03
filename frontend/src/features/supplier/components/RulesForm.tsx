import type { FormEvent } from 'react';
import type { RulesInput, SalesRules } from '../types';
import Icon from '../../../components/Icon';
export default function RulesForm({ current, onSave, busy }: { current: SalesRules | undefined; onSave: (data: RulesInput) => Promise<void>; busy: boolean }) {
 async function submit(event: FormEvent<HTMLFormElement>) {
  event.preventDefault();const data = new FormData(event.currentTarget);
  await onSave({ najmanjsa_marza: (Number(data.get('marza')) / 100).toFixed(6), najvecji_popust: (Number(data.get('popust')) / 100).toFixed(6), najdaljsi_rok_dni: Number(data.get('rok')),
   velja_od: data.get('od') ? new Date(String(data.get('od'))).toISOString() : null,
   velja_do: data.get('do') ? new Date(String(data.get('do'))).toISOString() : null });
 }
 return <form className="editor-form" onSubmit={submit}>
  <div className="form-grid"><label>Najmanjša marža (%)<input name="marza" type="number" min="0" max="99.9999" step="0.0001" defaultValue={current ? Number(current.najmanjsa_marza) * 100 : ''} required autoFocus/></label>
  <label>Največji popust (%)<input name="popust" type="number" min="0" max="99.9999" step="0.0001" defaultValue={current ? Number(current.najvecji_popust) * 100 : ''} required/></label></div>
  <label>Najdaljši dobavni rok (dni)<input name="rok" type="number" min="0" max="3650" step="1" defaultValue={current?.najdaljsi_rok_dni} required/></label>
  <label>Začetek veljavnosti<input name="od" type="datetime-local"/></label><p className="field-help">Prazno polje pomeni takojšnjo veljavnost.</p>
  <label>Konec veljavnosti<input name="do" type="datetime-local"/></label><p className="field-help">Neobvezno. Čas v vašem lokalnem časovnem pasu.</p>
  <p className="form-note">Nova različica zaključi prejšnjo ob začetku veljavnosti. Zgodovina ostane shranjena; prekrivanje načrtovanih različic ni dovoljeno.</p>
  <button disabled={busy} type="submit"><Icon name="check"/>Ustvari različico pravil</button>
 </form>;
}
