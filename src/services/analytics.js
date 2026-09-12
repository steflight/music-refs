/** Lightweight analytics (console + optional Plausible/Umami later). MR-19 */
const QUEUE_KEY = 'mr:analytics:queue';

export function track(event, props = {}) {
  const payload = {
    event,
    props,
    ts: new Date().toISOString(),
    path: typeof location !== 'undefined' ? location.pathname + location.search : '',
  };
  try {
    console.info('[mr-analytics]', event, props);
    const q = JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]');
    q.push(payload);
    localStorage.setItem(QUEUE_KEY, JSON.stringify(q.slice(-200)));
  } catch (_) { /* ignore */ }
  // Plausible hook if present
  try {
    if (typeof window !== 'undefined' && typeof window.plausible === 'function') {
      window.plausible(event, { props });
    }
  } catch (_) { /* ignore */ }
}
