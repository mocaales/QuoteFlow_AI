import App from './App';
import DemoPage from '../pages/DemoPage';
import ToastProvider from '../components/Toaster';

export default function Router() {
 return <ToastProvider>{window.location.pathname === '/demo' ? <DemoPage/> : <App/>}</ToastProvider>;
}
