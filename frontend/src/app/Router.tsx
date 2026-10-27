import App from './App';
import DemoPage from '../pages/DemoPage';

export default function Router() {
 return window.location.pathname === '/demo' ? <DemoPage/> : <App/>;
}
