import Login from '../features/identity/components/Login';
import WorkspacePage from '../pages/WorkspacePage';
import { useAuthSession } from '../features/identity/hooks/useAuthSession';
import Brand from '../components/Brand';

export default function App() {
 const { client, session, loaded, error } = useAuthSession();
 if (error && !client) return <div className="auth-page"><Brand/><section className="auth-form"><h1>Prijava ni na voljo</h1><p role="alert">{error}</p><button onClick={() => window.location.reload()}>Poskusi znova</button><a className="demo-link" href="/demo">Demonstracijski kalkulator →</a></section></div>;
 if (!loaded || !client) return <div className="auth-page"><p role="status">Nalagam QuoteFlow …</p></div>;
 return session ? <WorkspacePage client={client} session={session}/> : <Login client={client}/>;
}
