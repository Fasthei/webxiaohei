(() => {
  const key = document.currentScript?.dataset.key;
  const choice = new URLSearchParams(location.search).get('analytics');
  const sharedDomain = location.hostname === 'xiaohei.co' || location.hostname.endsWith('.xiaohei.co');
  let excluded = false;
  try {
    if (choice === 'off' || choice === 'on') {
      const value = choice === 'off' ? '1' : '0';
      document.cookie = `tr_analytics_excluded=${value}; Path=/; Max-Age=31536000; SameSite=Lax; Secure${sharedDomain ? '; Domain=xiaohei.co' : ''}`;
      localStorage.setItem('tr-analytics-excluded', value);
    }
    const saved = document.cookie.match(/(?:^|;\s*)tr_analytics_excluded=([01])(?:;|$)/);
    excluded = saved ? saved[1] === '1' : localStorage.getItem('tr-analytics-excluded') === '1';
  } catch { /* Storage can be disabled; the current URL choice still applies. */ }
  if (choice === 'off') excluded = true;
  if (choice === 'on') excluded = false;
  window.trAnalyticsExcluded = excluded || navigator.doNotTrack === '1';
  if (choice === 'off' || choice === 'on') {
    const notice = document.createElement('p');
    notice.className = 'analytics-notice';
    notice.setAttribute('role', 'status');
    const zh = document.documentElement.lang.startsWith('zh');
    notice.textContent = window.trAnalyticsExcluded
      ? (zh ? '此浏览器的访问已排除统计。' : 'Visits from this browser are excluded from analytics.')
      : (zh ? '此浏览器的访问统计已恢复。' : 'Analytics is enabled again for this browser.');
    document.body.prepend(notice);
  }
  if (!key || window.trAnalyticsExcluded) return;
  const script = document.createElement('script');
  script.src = 'https://analytics.ahrefs.com/analytics.js';
  script.dataset.key = key;
  script.async = true;
  document.head.appendChild(script);
})();
