import { useToast } from '../../../lib/toast';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import type { SupabaseClient } from '@supabase/supabase-js';
import ActionAlert from '../../../components/ActionAlert';
import Icon from '../../../components/Icon';
import { dateTime } from '../../../utils/format';
import { finishWork, setSchedule } from '../api';
import { phases, type Project } from '../types';

const pad = (n: number) => String(n).padStart(2, '0');
const local = (value: string | null) => { if (!value) return ''; const d = new Date(value); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`; };

export default function ProjectProgress({ client, companyId, project, onChange }: { client: SupabaseClient; companyId: string; project: Project; onChange?: () => void }) {
 const [current, setCurrent] = useState(project);
 const [busy, setBusy] = useState(false);
 const [error, setError] = useState('');
 const [where, setWhere] = useState<'termin' | 'izvedba'>('termin');
 const toast = useToast();
 const heading = useRef<HTMLHeadingElement>(null);
 useEffect(() => { setCurrent(project); }, [project]);
 async function run(section: 'termin' | 'izvedba', action: () => Promise<Project>, message: string) {
  setBusy(true); setError(''); setWhere(section);
  try { const next = await action(); setCurrent(previous => ({ ...previous, ...next })); onChange?.(); toast(message); if (section === 'izvedba') heading.current?.focus(); }
  catch (e) { setError(e instanceof Error ? e.message : 'Spremembe ni mogoče shraniti.'); }
  finally { setBusy(false); }
 }
 function schedule(event: FormEvent<HTMLFormElement>) {
  event.preventDefault(); setWhere('termin'); const data = new FormData(event.currentTarget), from = String(data.get('termin_od') ?? ''), to = String(data.get('termin_do') ?? '');
  if (!from || !to) { setError('Vnesite začetek in konec termina.'); return; }
  const start = new Date(from), end = new Date(to);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) { setError('Vnesite veljaven začetek in konec termina.'); return; }
  if (end <= start) { setError('Konec termina mora biti po začetku.'); return; }
  void run('termin', () => setSchedule(client, companyId, current.id, { termin_od: start.toISOString(), termin_do: end.toISOString() }), 'Termin je shranjen.');
 }
 const index = phases.findIndex(([id]) => id === current.faza), done = !!current.izvedba_koncana_ob;
 const editable = ['termin', 'izvedba'].includes(current.faza) && !done;
 const alert = (section: 'termin' | 'izvedba') => error && where === section && <ActionAlert>{error}</ActionAlert>;
 return <section className="quote-editor" aria-busy={busy}>
  <div className="section-heading"><h2 tabIndex={-1} ref={heading}>Potek projekta</h2><span className="status-badge confirmed">{phases[index]?.[1] ?? current.faza}</span></div>
  <ol className="phase-steps" aria-label="Faze projekta">{phases.map(([id, label], i) => <li key={id} aria-current={i === index ? 'step' : undefined}><span className={`status-badge ${i < index ? 'confirmed' : i === index ? 'pending' : ''}`}>{label}</span></li>)}</ol>
  {index < 3 && <section className="panel"><h3>Termin</h3><p>Termin izvedbe je mogoče določiti po sprejeti ponudbi.</p></section>}
  {index >= 3 && <section className="panel"><h3>Termin</h3>
   {editable
    ? <form className="editor-form" onSubmit={schedule}><div className="form-grid">
      <label>Začetek termina<input name="termin_od" type="datetime-local" required defaultValue={local(current.termin_od)} key={`od${current.termin_od}`}/></label>
      <label>Konec termina<input name="termin_do" type="datetime-local" required defaultValue={local(current.termin_do)} key={`do${current.termin_do}`}/></label></div>
      <div className="row-actions"><button type="submit" className={current.faza === 'izvedba' ? 'secondary' : undefined} disabled={busy}><Icon name="calendar"/>Potrdi termin</button></div>{alert('termin')}</form>
    : <p>{current.termin_od ? `${dateTime(current.termin_od)} – ${dateTime(current.termin_do)}` : '—'}</p>}
  </section>}
  {index >= 4 && <section className="panel"><h3>Izvedba</h3>
   {done ? <p><Icon name="check"/> Izvedba je zaključena {dateTime(current.izvedba_koncana_ob)}.</p>
    : current.faza === 'izvedba' ? <><p>Ko je delo opravljeno, zaključite izvedbo. Nato je mogoče izdati račun.</p><div className="row-actions"><button type="button" disabled={busy} onClick={() => void run('izvedba', () => finishWork(client, companyId, current.id), 'Izvedba je zaključena. Račun je mogoče izdati.')}><Icon name="check"/>Zaključi izvedbo</button></div>{alert('izvedba')}</>
    : <p>Izvedba še ni zaključena.</p>}
  </section>}
 </section>;
}
