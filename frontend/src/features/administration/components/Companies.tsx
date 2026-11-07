import { useState, type FormEvent, type ReactNode } from 'react';
import Drawer from '../../../components/Drawer';
import Icon from '../../../components/Icon';
import IconButton from '../../../components/IconButton';
import type { Podjetje } from '../../identity/types';
import type { AdminUser } from '../types';
import { fullName } from '../types';
import type { CompanyInput } from '../api';

export default function Companies({ companies, users, busy, error, onSave, onClearError }: { companies: Podjetje[]; users: AdminUser[]; busy: boolean; error: ReactNode; onSave: (company: Podjetje | null, data: CompanyInput) => Promise<boolean>; onClearError: () => void }) {
 const [form, setForm] = useState<{ item: Podjetje | null } | null>(null);
 const item = form?.item ?? null;
 async function submit(e: FormEvent<HTMLFormElement>) {
  e.preventDefault(); const data = new FormData(e.currentTarget), text = (name: string) => String(data.get(name) ?? '').trim();
  if (await onSave(item, { naziv: text('naziv'), lastnik_id: item?.lastnik_id ?? text('lastnik'), maticna_stevilka: text('maticna'), davcna_stevilka: text('davcna') || null, naslov: text('naslov'), aktivno: item ? data.get('stanje') === 'aktivno' : true })) setForm(null);
 }
 function close() { setForm(null); onClearError(); }
 return <>
  <div className="data-toolbar"><button type="button" disabled={busy} onClick={() => setForm({ item: null })}><Icon name="plus"/>Dodaj podjetje</button></div>
  <div className="table-wrap"><table className="data-table"><caption className="sr-only">Registrirana podjetja</caption><thead><tr><th>Naziv</th><th>Stanje</th><th><span className="sr-only">Dejanja</span></th></tr></thead><tbody>
   {companies.map(c => <tr key={c.id}><td><strong>{c.naziv}</strong><span className="cell-detail">{c.naslov}</span></td><td><span className={`status-badge ${c.aktivno ? 'confirmed' : 'inactive'}`}>{c.aktivno ? 'Aktivno' : 'Neaktivno'}</span></td><td className="num"><IconButton icon="pen" label={`Uredi ${c.naziv}`} tip="Uredi" disabled={busy} onClick={() => setForm({ item: c })}/></td></tr>)}
   {!companies.length && <tr><td colSpan={3} className="muted">Podjetij še ni. Dodajte prvo podjetje.</td></tr>}
  </tbody></table></div>
  {form && <Drawer title={item ? `Uredi ${item.naziv}` : 'Dodaj podjetje'} onClose={close}>
   {error}
   <form className="editor-form" onSubmit={e => void submit(e)}>
    <label>Naziv podjetja<input name="naziv" defaultValue={item?.naziv} required maxLength={200}/></label>
    {!item && <label>Lastnik podjetja<select name="lastnik" required defaultValue=""><option value="" disabled>Izberite lastnika</option>{users.filter(u => u.potrjen !== false).map(u => <option key={u.id} value={u.id}>{`${fullName(u)} · ${u.e_posta}`}</option>)}</select></label>}
    <label>Matična številka<input name="maticna" defaultValue={item?.maticna_stevilka} required maxLength={30}/></label>
    <label>Davčna številka<input name="davcna" defaultValue={item?.davcna_stevilka ?? ''} maxLength={30}/></label>
    <label>Naslov podjetja<input name="naslov" defaultValue={item?.naslov} required maxLength={500}/></label>
    {item && <label>Stanje<select name="stanje" defaultValue={item.aktivno ? 'aktivno' : 'neaktivno'}><option value="aktivno">Aktivno</option><option value="neaktivno">Neaktivno</option></select></label>}
    <button type="submit" disabled={busy}><Icon name="check"/>{item ? 'Shrani spremembe' : 'Dodaj podjetje'}</button>
   </form>
  </Drawer>}
 </>;
}
