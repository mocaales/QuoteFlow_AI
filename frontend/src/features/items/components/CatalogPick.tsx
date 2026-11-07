import { useState, type FormEvent } from 'react';
import Icon from '../../../components/Icon';
import { money } from '../../../utils/format';
import { fraction } from '../percent';
import { unitLabels } from '../../../utils/units';
import { type CatalogItemInput, type CatalogOption } from '../types';

export default function CatalogPick({ options, busy, onSave }: { options: CatalogOption[] | null; busy: boolean; onSave: (data: CatalogItemInput) => Promise<void> }) {
 const [chosen, setChosen] = useState<CatalogOption | null>(null);
 async function submit(event: FormEvent<HTMLFormElement>) {
  event.preventDefault(); const data = new FormData(event.currentTarget);
  await onSave({ postavka_cenika_id: chosen!.id, kolicina: String(data.get('kolicina') || '1'), popust: fraction(data.get('popust') as string | null) });
 }
 if (!options) return <p role="status" className="loading-state">Nalagam cenik …</p>;
 if (chosen) return <form className="editor-form" onSubmit={submit}>
  <p><strong>{chosen.naziv}</strong><span className="cell-detail">{money(chosen.cena_na_enoto)} na {unitLabels[chosen.enota]}</span></p>
  <div className="form-grid"><label>Količina<input name="kolicina" type="number" min="0.0001" max="1000000" step="0.0001" placeholder="1" autoFocus/></label><label>Popust (%)<input name="popust" type="number" min="0" max="99.9999" step="0.0001" placeholder="0"/></label></div>
  <p className="field-help">Vrsta dela in delo se prevzamejo iz cenika. Izmere dodate po dodajanju.</p>
  <div className="row-actions"><button type="submit" disabled={busy}><Icon name="plus"/>Dodaj postavko</button><button type="button" className="secondary" disabled={busy} onClick={() => setChosen(null)}>Nazaj na seznam</button></div>
 </form>;
 const active = options.filter(option => option.aktivna);
 if (!active.length) return <p className="muted">V ceniku ni aktivnih postavk.</p>;
 return <div className="table-wrap"><table className="data-table"><caption className="sr-only">Aktivne postavke cenika</caption><thead><tr><th>Postavka</th><th className="num">Cena</th><th><span className="sr-only">Izbira</span></th></tr></thead><tbody>
  {active.map(option => <tr key={option.id}><td><strong>{option.naziv}</strong><span className="cell-detail">{option.opis}</span></td><td className="num" data-label="Cena">{money(option.cena_na_enoto)} / {unitLabels[option.enota]}</td>
   <td><button type="button" className="secondary small" aria-label={`Izberi ${option.naziv}`} onClick={() => setChosen(option)}>Izberi</button></td></tr>)}
 </tbody></table></div>;
}
