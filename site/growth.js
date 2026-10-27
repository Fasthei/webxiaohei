(() => {
  // No analytics provider is loaded until a real project key is configured.
  const emit = (name, props={}) => {
    if (navigator.doNotTrack === '1' || window.trAnalyticsExcluded) return;
    if (window.AhrefsAnalytics) window.AhrefsAnalytics.sendEvent(name,{props});
  };
  document.addEventListener('click', event => {
    const link=event.target.closest('a[href]');if(!link)return;
    if(link.href.startsWith('mailto:'))emit('contact_click',{language:document.documentElement.lang});
    else if(new URL(link.href).hostname==='github.com')emit('github_click',{language:document.documentElement.lang});
  });
  const article=document.querySelector('.article-body');
  if(article){
    let engaged=false;const start=Date.now();
    const check=()=>{
      const box=article.getBoundingClientRect();
      if(!engaged && Date.now()-start>=30000 && box.bottom<=innerHeight+box.height*.25){engaged=true;emit('engaged_read',{article:location.pathname,language:document.documentElement.lang});}
    };
    addEventListener('scroll',check,{passive:true});setTimeout(check,30000);
  }
})();
