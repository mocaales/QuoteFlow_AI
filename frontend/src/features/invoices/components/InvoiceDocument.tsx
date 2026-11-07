import type { ReactNode, Ref } from 'react';
import { date, money, percent, quantity } from '../../../utils/format';
import type { Invoice } from '../types';

export default function InvoiceDocument({ invoice, children, headingRef }: { invoice: Invoice; children?: ReactNode; headingRef?: Ref<HTMLHeadingElement> }) {
 const issued = invoice.stanje_dokumenta !== 'osnutek', paid = invoice.stanje_placila === 'placan';
 const party = (title: string, name: string | null, address: string | null, vat?: string | null) => <div><h3>{title}</h3><p><strong>{name ?? '—'}</strong><span className="cell-detail">{address ?? ''}</span>{vat && <span className="cell-detail">Davčna številka: {vat}</span>}</p></div>;
 return <section className="quote-editor">
  <div className="section-heading"><h2 tabIndex={-1} ref={headingRef}>{issued ? `Račun ${invoice.stevilka}` : 'Osnutek računa'}</h2>{issued ? <span className={`status-badge ${paid ? 'confirmed' : 'pending'}`}>{paid ? 'Plačan' : 'Neplačan'}</span> : <span className="status-badge">Osnutek</span>}</div>
  <p className="muted">Po ponudbi {invoice.ponudba.stevilka} · Različica {invoice.ponudba.razlicica}{issued && <> · Izdan {date(invoice.izdan_ob)} · Zapade {date(invoice.zapade_dne)}</>}{paid && <> · Plačano {date(invoice.placano_ob)}</>}</p>
  {issued && <div className="form-grid">{party('Izdajatelj', invoice.izdajatelj_naziv, invoice.izdajatelj_naslov, invoice.izdajatelj_davcna)}{party('Prejemnik', invoice.prejemnik_naziv, invoice.prejemnik_naslov)}</div>}
  <div className="table-wrap"><table className="data-table"><caption className="sr-only">Postavke računa</caption><thead><tr><th>Postavka</th><th className="num">Količina</th><th className="num">Cena</th><th className="num">Popust</th><th className="num">DDV</th><th className="num">Skupaj</th></tr></thead><tbody>
   {invoice.postavke.map(line => <tr key={line.zaporedje}><td><strong>{line.naziv}</strong><span className="cell-detail">{[line.vrsta_dela, line.opis].filter(Boolean).join(' · ')}</span></td>
    <td className="num" data-label="Količina">{quantity(line.kolicina)} {line.enota}</td><td className="num" data-label="Cena">{money(line.cena_na_enoto)}</td><td className="num" data-label="Popust">{percent(line.popust)}</td>
    <td className="num" data-label="DDV">{percent(line.stopnja_ddv)}</td><td className="num" data-label="Skupaj">{money(line.koncna_cena)}</td></tr>)}
  </tbody></table></div>
  <dl className="kpi-strip" role="group" aria-label="Vsote računa"><div><dt>Neto</dt><dd>{money(invoice.neto)}</dd></div><div><dt>DDV</dt><dd>{money(invoice.ddv)}</dd></div><div><dt>Za plačilo</dt><dd>{money(invoice.skupaj)}</dd></div></dl>
  {invoice.ddv_po_stopnjah.length > 0 && <p className="table-footnote">{invoice.ddv_po_stopnjah.map(r => `DDV ${percent(r.stopnja_ddv)}: osnova ${money(r.osnova)}, davek ${money(r.ddv)}`).join(' · ')}</p>}
  {children}
 </section>;
}
