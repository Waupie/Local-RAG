const $ = (id) => document.getElementById(id);
const apiKeyEl = $('apiKey');

function baseUrl(){
  return ''; // same-origin: requests resolve relative to the current page
}

// ---- tabs ----
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const tab = btn.dataset.tab;
    $('tab-text').style.display = tab === 'text' ? 'block' : 'none';
    $('tab-file').style.display = tab === 'file' ? 'block' : 'none';
  });
});

// ---- ingest log ----
function logEntry(text, kind){
  const el = document.createElement('div');
  el.className = 'log-entry' + (kind ? ' ' + kind : '');
  const time = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit', second:'2-digit'});
  el.textContent = `[${time}] ${text}`;
  $('ingestLog').appendChild(el);
}

// ---- ingest text ----
$('ingestTextBtn').addEventListener('click', async () => {
  const content = $('ingestText').value.trim();
  if(!content){ logEntry('nothing to ingest — paste some text first', 'err'); return; }
  const key = apiKeyEl.value.trim();
  if(!key){ logEntry('add your ingest API key above first', 'err'); return; }

  const btn = $('ingestTextBtn');
  btn.disabled = true; btn.textContent = 'Ingesting…';
  try{
    const res = await fetch(`${baseUrl()}/ingest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-API-Key': key },
      body: JSON.stringify({ content })
    });
    const data = await res.json();
    if(!res.ok) throw new Error(data.detail || `status ${res.status}`);
    logEntry(data.message || 'ingested', 'ok');
    $('ingestText').value = '';
  }catch(e){
    logEntry(`failed: ${e.message}`, 'err');
  }finally{
    btn.disabled = false; btn.textContent = 'Ingest text';
  }
});

// ---- ingest file ----
let selectedFile = null;
const dropZone = $('dropZone');
const fileInput = $('fileInput');

dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('drag'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag'));
dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('drag');
  if(e.dataTransfer.files.length){
    selectedFile = e.dataTransfer.files[0];
    $('fileName').textContent = selectedFile.name;
  }
});
fileInput.addEventListener('change', () => {
  if(fileInput.files.length){
    selectedFile = fileInput.files[0];
    $('fileName').textContent = selectedFile.name;
  }
});

$('ingestFileBtn').addEventListener('click', async () => {
  if(!selectedFile){ logEntry('choose a file first', 'err'); return; }
  const key = apiKeyEl.value.trim();
  if(!key){ logEntry('add your ingest API key above first', 'err'); return; }

  const btn = $('ingestFileBtn');
  btn.disabled = true; btn.textContent = 'Uploading…';
  try{
    const form = new FormData();
    form.append('file', selectedFile);
    const res = await fetch(`${baseUrl()}/ingest`, {
      method: 'POST',
      headers: { 'X-API-Key': key },
      body: form
    });
    const data = await res.json();
    if(!res.ok) throw new Error(data.detail || `status ${res.status}`);
    logEntry(data.message || 'ingested', 'ok');
    selectedFile = null;
    $('fileName').textContent = '';
    fileInput.value = '';
  }catch(e){
    logEntry(`failed: ${e.message}`, 'err');
  }finally{
    btn.disabled = false; btn.textContent = 'Ingest file';
  }
});

// ---- chat ----
const chatScroll = $('chatScroll');
const chatInput = $('chatInput');
const sendBtn = $('sendBtn');

function addMessage(role, html){
  const el = document.createElement('div');
  el.className = `msg ${role}`;
  if(role === 'assistant'){
    el.innerHTML = `<span class="prompt-tag">&gt; assistant</span>${html}`;
  }else{
    el.textContent = html;
  }
  chatScroll.appendChild(el);
  chatScroll.scrollTop = chatScroll.scrollHeight;
  return el;
}

function escapeHtml(str){
  return str.replace(/[&<>"']/g, (c) => ({
    '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
  }[c]));
}

async function sendQuery(){
  const question = chatInput.value.trim();
  if(!question) return;
  addMessage('user', question);
  chatInput.value = '';
  autoGrow();
  sendBtn.disabled = true;

  const thinking = addMessage('assistant', '<em style="color:var(--muted)">thinking…</em>');

  try{
    const res = await fetch(`${baseUrl()}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: question })
    });
    const data = await res.json();
    if(!res.ok) throw new Error(data.detail || `status ${res.status}`);

    let html = escapeHtml(data.response || 'No response.').replace(/\n/g, '<br>');
    if(Array.isArray(data.sources) && data.sources.length){
      html += '<div class="sources">' + data.sources.map(s =>
        `<span class="source-chip">match ${Math.round((s.similarity || 0) * 100)}%</span>`
      ).join('') + '</div>';
    }
    thinking.innerHTML = `<span class="prompt-tag">&gt; assistant</span>${html}`;
  }catch(e){
    thinking.innerHTML = `<span class="prompt-tag">&gt; assistant</span>Couldn't reach the RAG service (${escapeHtml(e.message)}). Check that the stack is running.`;
  }finally{
    sendBtn.disabled = false;
    chatScroll.scrollTop = chatScroll.scrollHeight;
  }
}

function autoGrow(){
  chatInput.style.height = 'auto';
  chatInput.style.height = Math.min(chatInput.scrollHeight, 140) + 'px';
}
chatInput.addEventListener('input', autoGrow);
chatInput.addEventListener('keydown', (e) => {
  if(e.key === 'Enter' && !e.shiftKey){
    e.preventDefault();
    sendQuery();
  }
});
sendBtn.addEventListener('click', sendQuery);