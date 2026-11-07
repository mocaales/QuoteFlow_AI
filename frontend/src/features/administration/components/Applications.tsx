import IconButton from '../../../components/IconButton';
import { dateTime } from '../../../utils/format';
import type { ProsnjaAdmin } from '../../identity/types';

export default function Applications({ items, busy, onDecide }: { items: ProsnjaAdmin[]; busy: boolean; onDecide: (id: string, approve: boolean) => void }) {
 return <div className="table-wrap"><table className="data-table list-table"><caption className="sr-only">Prošnje za mojstra</caption><thead><tr><th>Podjetje</th><th>Stanje</th><th>Vlagatelj</th><th className="num">Oddano</th><th><span className="sr-only">Dejanja</span></th></tr></thead><tbody>
  {items.map(a => <tr key={a.id}><td><strong>{a.naziv_podjetja}</strong><span className="muted"> · {a.maticna_stevilka}</span></td><td><span className={`status-badge ${a.stanje === 'oddana' ? 'pending' : a.stanje === 'odobrena' ? 'confirmed' : 'inactive'}`}>{a.stanje === 'oddana' ? 'Oddana' : a.stanje === 'odobrena' ? 'Odobrena' : 'Zavrnjena'}</span></td><td data-label="Vlagatelj:">{a.e_posta}</td><td className="num" data-label="Oddano:">{dateTime(a.oddano_ob)}</td>
   <td className="num">{a.stanje === 'oddana' && <><IconButton icon="check" label={`Odobri ${a.naziv_podjetja}`} tip="Odobri" disabled={busy} onClick={() => onDecide(a.id, true)}/><IconButton icon="close" label={`Zavrni ${a.naziv_podjetja}`} tip="Zavrni" disabled={busy} onClick={() => onDecide(a.id, false)}/></>}</td></tr>)}
  {!items.length && <tr><td colSpan={5} className="muted">Prošenj še ni.</td></tr>}
 </tbody></table></div>;
}
