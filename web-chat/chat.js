const chatLog = document.getElementById('chat-log');
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');
const fileInput = document.getElementById('file-input');
const uploadBtn = document.getElementById('upload-btn');

function appendMessage(text, sender) {
  const msg = document.createElement('div');
  msg.className = `message ${sender}`;
  msg.textContent = text;
  chatLog.appendChild(msg);
  chatLog.scrollTop = chatLog.scrollHeight;
}

chatForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const question = userInput.value.trim();
  if (!question) return;
  appendMessage(question, 'user');
  userInput.value = '';
  appendMessage('...', 'rag');
  try {
    const res = await fetch('http://localhost:8000/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: question })
    });
    const data = await res.json();
    chatLog.removeChild(chatLog.lastChild); // remove '...'
    if (data.response) {
      appendMessage(data.response, 'rag');
    } else {
      appendMessage('No response from RAG.', 'rag');
    }
  } catch (err) {
    chatLog.removeChild(chatLog.lastChild);
    appendMessage('Error contacting RAG API.', 'rag');
  }
});

uploadBtn.addEventListener('click', () => {
  fileInput.click();
});

fileInput.addEventListener('change', async (e) => {
  const files = Array.from(e.target.files);
  if (!files.length) return;
  for (const file of files) {
    appendMessage(`Uploading: ${file.webkitRelativePath || file.name}`, 'user');
    const reader = new FileReader();
    reader.onload = async function(evt) {
      const content = evt.target.result;
      appendMessage('Ingesting file...', 'rag');
      try {
        const res = await fetch('http://localhost:8000/ingest', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content })
        });
        const data = await res.json();
        chatLog.removeChild(chatLog.lastChild); // remove 'Ingesting file...'
        if (data.message) {
          appendMessage(`File ingested: ${file.webkitRelativePath || file.name}`, 'rag');
        } else {
          appendMessage('Failed to ingest file.', 'rag');
        }
      } catch (err) {
        chatLog.removeChild(chatLog.lastChild);
        appendMessage('Error contacting RAG API.', 'rag');
      }
    };
    reader.readAsText(file);
    // Wait for this file to finish before starting the next
    await new Promise(resolve => reader.onloadend = resolve);
  }
});
