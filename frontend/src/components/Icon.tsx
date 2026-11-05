export type IconName = 'grid' | 'list' | 'stock' | 'rules' | 'users' | 'arrow' | 'plus' | 'search' | 'close' | 'logout' | 'check' | 'menu' | 'refresh' | 'calculator' | 'pen' | 'revoke' | 'restore' | 'trash' | 'user-plus' | 'calendar';
type Name = IconName;
const paths: Record<Name, string> = {
 grid: 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
 list: 'M8 5h13 M8 12h13 M8 19h13 M3 5h.01 M3 12h.01 M3 19h.01',
 stock: 'm12 3 9 5-9 5-9-5 9-5Z M3 8v9l9 5 9-5V8 M12 13v9 M7.5 5.5l9 5',
 rules: 'M4 6h16 M4 12h16 M4 18h16 M8 3v6 M16 9v6 M10 15v6',
 users: 'M16 20v-1.5a3.5 3.5 0 0 0-3.5-3.5h-5A3.5 3.5 0 0 0 4 18.5V20 M10 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7 M20 20v-1.5a3.5 3.5 0 0 0-2.5-3.35 M15 4.15a3.5 3.5 0 0 1 0 6.7',
 arrow: 'M5 12h14 M13 6l6 6-6 6', plus: 'M12 5v14 M5 12h14',
 search: 'M21 21l-5-5 M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0',
 close: 'm6 6 12 12 M6 18 18 6', logout: 'M9 4H4v16h5 M13 8l4 4-4 4 M8 12h13', check: 'm5 12 4 4 10-10',
 menu: 'M4 7h16 M4 12h16 M4 17h16',
 refresh: 'M20 11a8 8 0 0 0-14.6-4.5L4 8 M4 4v4h4 M4 13a8 8 0 0 0 14.6 4.5L20 16 M20 20v-4h-4',
 pen: 'M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16v4Z M13.5 6.5l4 4',
 revoke: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z M5.6 5.6l12.8 12.8',
 restore: 'M3 12a9 9 0 1 0 2.6-6.4L3 8 M3 3v5h5',
 trash: 'M4 7h16 M9 7V4h6v3 M6 7l1 13h10l1-13 M10 11v6 M14 11v6',
 'user-plus': 'M15 20v-1.5a3.5 3.5 0 0 0-3.5-3.5h-5A3.5 3.5 0 0 0 3 18.5V20 M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7 M19 8v6 M16 11h6',
 calendar: 'M4 5h16v15H4z M4 10h16 M8 3v4 M16 3v4 M8 14h.01 M12 14h.01 M16 14h.01',
 calculator: 'M6 3h12v18H6z M9 7h6 M9 12h.01 M12 12h.01 M15 12h.01 M9 16h.01 M12 16h.01 M15 16h.01',
};
export default function Icon({ name }: { name: Name }) {
 return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]}/></svg>;
}
