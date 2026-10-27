import { useState, type FormEvent } from 'react';
import type { SupabaseClient } from '@supabase/supabase-js';
import Brand from '../../../components/Brand';

export default function Login({ client }: { client: SupabaseClient }) {
 const [register, setRegister] = useState(false);
 const [error, setError] = useState('');
 const [notice, setNotice] = useState('');
 const [busy, setBusy] = useState(false);
 async function submit(e: FormEvent<HTMLFormElement>) {
  e.preventDefault(); setBusy(true); setError(''); setNotice('');
  const form = e.currentTarget;
  const data = new FormData(form);
  const credentials = { email: String(data.get('email')).trim(), password: String(data.get('password')) };
  try {
   const result = register ? await client.auth.signUp({ ...credentials, options: { emailRedirectTo: window.location.origin } }) : await client.auth.signInWithPassword(credentials);
   if (result.error) {
    const code = result.error.code;
    throw new Error(code === 'email_not_confirmed' ? 'Najprej potrdite e-poštni naslov.' : code === 'invalid_credentials' ? 'E-pošta ali geslo ni pravilno.' : code === 'weak_password' ? 'Uporabite močnejše geslo z najmanj osmimi znaki.' : 'Zahteve ni mogoče dokončati. Preverite podatke ali poskusite pozneje.');
   }
   form.reset();
   if (register && !result.data.session) setNotice('Preverite e-pošto za potrditev računa. Če račun že obstaja, se prijavite.');
  } catch (e) { setError(e instanceof Error ? e.message : 'Prijava trenutno ni dosegljiva.'); }
  finally { setBusy(false); }
 }
 return <div className="auth-page"><Brand/>
  <section className="auth-form"><p className="eyebrow">DELOVNI PROSTOR</p><h1>{register ? 'Ustvarite račun' : 'Prijava'}</h1>
   <p className="muted">{register ? 'Po registraciji vam administrator dodeli dostop do podjetja.' : 'Prijavite se za dostop do svojega podjetja.'}</p>
   <form onSubmit={submit}><label>E-pošta<input name="email" type="email" autoComplete="email" maxLength={254} required/></label>
    <label>Geslo<input name="password" type="password" minLength={8} maxLength={128} autoComplete={register ? 'new-password' : 'current-password'} required/></label>
    {register && <p className="muted">Geslo naj vsebuje najmanj osem znakov.</p>}
    {error && <p role="alert" className="alert">{error}</p>}{notice && <p role="status" className="notice">{notice}</p>}
    <button disabled={busy}>{busy ? 'Počakajte …' : register ? 'Registriraj se' : 'Prijavi se'}</button>
   </form>
   <button className="text-button" disabled={busy} onClick={() => { setRegister(!register); setError(''); setNotice(''); }}>{register ? 'Že imate račun? Prijavite se' : 'Nimate računa? Registrirajte se'}</button>
  </section><a className="demo-link" href="/demo">Odpri demonstracijski kalkulator →</a>
 </div>;
}
