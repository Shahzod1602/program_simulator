const account = {user: null, csrf: '', drafts: {}};
let authMode = 'login';
let authResolve;
window.authReady = new Promise(resolve => { authResolve = resolve; });
window.campusAccount = account;
window.api = async function(path, {method = 'GET', body} = {}) {
 const response = await fetch(path, {method, headers: {'Content-Type': 'application/json', ...(account.csrf ? {'X-CSRF-Token': account.csrf} : {})}, ...(body === undefined ? {} : {body: JSON.stringify(body)})});
 const data = await response.json();
 if (!response.ok) {
  if (response.status === 401 && account.user) location.reload();
  throw new Error(data.error || 'Request failed. Please try again.');
 }
 return data;
};
function authModeUI(mode) {
 authMode = mode;
 document.getElementById('authTitle').textContent = mode === 'login' ? 'Pick up where you left off.' : 'Keep your ideas with you.';
 document.getElementById('authSubmit').textContent = mode === 'login' ? 'Sign in' : 'Create account';
 document.getElementById('authSwitch').textContent = mode === 'login' ? 'New here? Create an account' : 'Already have an account? Sign in';
 const password = document.getElementById('authPassword'); password.autocomplete = mode === 'login' ? 'current-password' : 'new-password'; password.minLength = mode === 'login' ? 1 : 12;
 document.getElementById('authError').textContent = '';
}
async function signedIn(data) {
 account.user = data.user; account.csrf = data.csrf;
 account.drafts = (await window.api('/api/drafts')).drafts;
 // Preserve drafts from the earlier local prototype on the first guest visit.
 if (data.user.role === 'guest' && !Object.keys(account.drafts).length) {
  for (const language of ['python','cpp','c','javascript','java','go','ruby','sql']) {
   try {
    const key = `campus-code-${language}`;
    const draft = JSON.parse(localStorage.getItem(key) || 'null');
    if (draft && typeof draft.code === 'string') {
     await window.api(`/api/drafts/${language}`, {method:'PUT', body:{code:draft.code, stdin:typeof draft.stdin === 'string' ? draft.stdin : ''}});
     account.drafts[language] = draft;
     localStorage.removeItem(key);
    }
   } catch { /* Keep old drafts available if migration cannot complete. */ }
  }
 }
 document.getElementById('authGate').hidden = true;
 document.getElementById('workspaceApp').inert = false;
 const guest = data.user.role === 'guest';
 document.getElementById('accountName').textContent = data.user.name;
 document.getElementById('accountRole').textContent = guest ? 'Guest workspace' : 'Student';
 document.getElementById('logout').textContent = guest ? 'New workspace' : 'Sign out';
 document.getElementById('logout').hidden = false;
 document.getElementById('openLogin').hidden = !guest;
 document.getElementById('guestNotice').hidden = !guest;
 document.querySelector('.avatar').textContent = guest ? 'G' : data.user.name[0].toUpperCase();
 authResolve(account);
 try {
  const status = await window.api('/api/runner-status');
  document.getElementById('runnerNotice').hidden = status.ready;
  document.getElementById('runnerState').textContent = status.ready ? 'Isolated runner ready' : 'Runner not connected';
 } catch { document.getElementById('runnerNotice').hidden = false; }
}
document.getElementById('authSwitch').onclick = () => authModeUI(authMode === 'login' ? 'register' : 'login');
document.getElementById('openLogin').onclick = async () => {
 try {
  if (window.flushDrafts) await window.flushDrafts();
  authModeUI('login');
  document.getElementById('authGate').hidden = false;
  document.getElementById('authGate').scrollTop = 0;
  document.getElementById('workspaceApp').inert = true;
 } catch (error) { document.getElementById('accountError').textContent = error.message; }
};
document.getElementById('continueGuest').onclick = () => {
 if (!account.user) return location.reload();
 document.getElementById('authGate').hidden = true;
 document.getElementById('workspaceApp').inert = false;
};
document.getElementById('authForm').onsubmit = async event => {
 event.preventDefault(); const button = document.getElementById('authSubmit'); button.disabled = true;
 document.getElementById('authError').textContent = '';
 try {
  await window.api(authMode === 'login' ? '/api/login' : '/api/register', {method: 'POST', body: {
   username: document.getElementById('authUsername').value,
   password: document.getElementById('authPassword').value,
  }});
  document.getElementById('authPassword').value = '';
  location.reload();
 } catch (error) { document.getElementById('authError').textContent = error.message; }
 finally { button.disabled = false; }
};
document.getElementById('logout').onclick = async () => {
 if (!confirm('Leave this workspace? Download your code first if you are using a guest workspace.')) return;
 const button = document.getElementById('logout'); button.disabled = true;
 document.getElementById('workspaceApp').inert = true;
 try {
  if (window.flushDrafts) await window.flushDrafts();
  await window.api('/api/logout', {method: 'POST', body: {}});
  location.reload();
 } catch (error) { button.disabled = false; document.getElementById('workspaceApp').inert = false; document.getElementById('accountError').textContent = error.message; }
};
(async () => {
 try {
  let data = await window.api('/api/session');
  if (!data.user) data = await window.api('/api/guest', {method:'POST', body:{}});
  await signedIn(data);
 } catch (error) {
  document.getElementById('authGate').hidden = false;
  document.getElementById('authError').textContent = error.message;
 }
})();
