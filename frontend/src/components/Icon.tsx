export type IconName = 'grid' | 'list' | 'stock' | 'rules' | 'users' | 'arrow' | 'plus' | 'search' | 'close' | 'logout' | 'check' | 'menu' | 'refresh' | 'calculator' | 'pen' | 'revoke' | 'restore' | 'trash' | 'user-plus' | 'calendar' | 'ruler' | 'lock' | 'more' | 'chevron-down' | 'chevron-left' | 'info' | 'alert' | 'check-circle' | 'tag' | 'wrench' | 'layers' | 'folder' | 'file-text';
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
 ruler: 'M3 17 17 3l4 4L7 21z M7 13l2 2 M10 10l2 2 M13 7l2 2',
 lock: 'M5 11h14v10H5z M8 11V8a4 4 0 0 1 8 0v3 M12 15v2',
 calculator: 'M6 3h12v18H6z M9 7h6 M9 12h.01 M12 12h.01 M15 12h.01 M9 16h.01 M12 16h.01 M15 16h.01',
 more: 'M5 12a1 1 0 1 0 2 0 1 1 0 1 0-2 0 M11 12a1 1 0 1 0 2 0 1 1 0 1 0-2 0 M17 12a1 1 0 1 0 2 0 1 1 0 1 0-2 0',
 'chevron-down': 'm6 9 6 6 6-6', 'chevron-left': 'm15 6-6 6 6 6',
 info: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z M12 11v5 M12 8h.01',
 alert: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z M12 7.5v5 M12 16h.01',
 'check-circle': 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z M8 12l3 3 5-6',
 tag: 'M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8Z M7.5 7.5h.01',
 wrench: 'M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76Z',
 layers: 'M12 3 21 8 12 13 3 8Z M3 12.5 12 17.5 21 12.5 M3 17 12 22 21 17',
 folder: 'M3 6a2 2 0 0 1 2-2h4l2 3h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z',
 'file-text': 'M6 3h8l5 5v13H6z M14 3v5h5 M9 13h6 M9 17h6',
};
export default function Icon({ name }: { name: Name }) {
 return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]}/></svg>;
}
