const TOKEN='qa_admin_token';
function token(){return localStorage.getItem(TOKEN)}
async function api(path,opts={}){opts.headers={...(opts.headers||{}),Authorization:'Bearer '+token()};if(opts.body&&!(opts.body instanceof FormData))opts.headers['Content-Type']='application/json';const r=await fetch('/api'+path,opts);const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||'Request failed');return d}
function esc(v){return String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;')}
function guard(){if(!token())location.href='/admin';}
function logout(){localStorage.removeItem(TOKEN);location.href='/admin'}
async function navUser(){try{return await api('/admin/dashboard')}catch(e){logout()}}

async function requireAdmin(){if(!token()){location.href='/admin';return false;}try{await api('/admin/dashboard');return true}catch(e){localStorage.removeItem(TOKEN);location.href='/admin';return false;}}
