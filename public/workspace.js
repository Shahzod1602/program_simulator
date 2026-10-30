const workspace = {user: null, csrf: '', drafts: {}};
let workspaceResolve;
window.workspaceReady = new Promise(resolve => { workspaceResolve = resolve; });
window.campusWorkspace = workspace;
window.api = async function(path, {method = 'GET', body} = {}) {
 const response = await fetch(path, {method, headers: {'Content-Type': 'application/json', ...(workspace.csrf ? {'X-CSRF-Token': workspace.csrf} : {})}, ...(body === undefined ? {} : {body: JSON.stringify(body)})});
 const data = await response.json();
 if (!response.ok) {
  if (response.status === 401 && workspace.user) location.reload();
  throw new Error(data.error || 'Request failed. Please try again.');
 }
 return data;
};
async function openWorkspace(data) {
 workspace.user = data.user; workspace.csrf = data.csrf;
 workspace.drafts = (await window.api('/api/drafts')).drafts;
 // Preserve drafts from the earlier local prototype on the first guest visit.
 if (data.user.role === 'guest' && !Object.keys(workspace.drafts).length) {
  for (const language of ['python','cpp','c','javascript','java','go','ruby','sql']) {
   try {
    const key = `campus-code-${language}`;
    const draft = JSON.parse(localStorage.getItem(key) || 'null');
    if (draft && typeof draft.code === 'string') {
     await window.api(`/api/drafts/${language}`, {method:'PUT', body:{code:draft.code, stdin:typeof draft.stdin === 'string' ? draft.stdin : ''}});
     workspace.drafts[language] = draft;
     localStorage.removeItem(key);
    }
   } catch { /* Keep old drafts available if migration cannot complete. */ }
  }
 }
 document.getElementById('workspaceApp').inert = false;
 document.getElementById('guestNotice').hidden = false;
 workspaceResolve(workspace);
 try {
  const status = await window.api('/api/runner-status');
  document.getElementById('runnerNotice').hidden = status.ready;
  document.getElementById('runnerState').textContent = status.ready ? 'Isolated runner ready' : 'Runner not connected';
 } catch { document.getElementById('runnerNotice').hidden = false; }
}
(async () => {
 try {
  let data = await window.api('/api/session');
  if (!data.user) data = await window.api('/api/guest', {method:'POST', body:{}});
  await openWorkspace(data);
 } catch (error) {
  document.getElementById('workspaceApp').inert = false;
  document.getElementById('run').disabled = true;
  const message = document.getElementById('workspaceError');
  message.textContent = `Could not open your workspace: ${error.message} `;
  const retry = document.createElement('button');
  retry.textContent = 'Try again';
  retry.className = 'text-button';
  retry.onclick = () => location.reload();
  message.append(retry);
 }
})();
