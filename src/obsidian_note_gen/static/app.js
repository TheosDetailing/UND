function getConfig() {
  return {
    api_url: document.getElementById('api_url').value,
    notes_dir: document.getElementById('notes_dir').value,
    delay_meta_content: document.getElementById('delay_meta').value,
    delay_between_rows: document.getElementById('delay_rows').value,
  };
}

document.getElementById('one-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const data = new FormData();
  const cfg = getConfig();
  Object.entries(cfg).forEach(([k, v]) => data.append(k, v));
  data.append('subject', document.getElementById('subject').value);
  const res = await fetch('/run-one', { method: 'POST', body: data });
  const js = await res.json();
  document.getElementById('log').textContent = 'Created ' + js.path;
});

const drop = document.getElementById('drop-zone');
const fileInput = document.getElementById('csvfile');

drop.addEventListener('click', () => fileInput.click());
drop.addEventListener('dragover', (e) => {
  e.preventDefault();
});
drop.addEventListener('drop', (e) => {
  e.preventDefault();
  fileInput.files = e.dataTransfer.files;
  uploadCSV();
});
fileInput.addEventListener('change', uploadCSV);

async function uploadCSV() {
  const file = fileInput.files[0];
  if (!file) return;
  const data = new FormData();
  const cfg = getConfig();
  Object.entries(cfg).forEach(([k, v]) => data.append(k, v));
  data.append('file', file);
  const res = await fetch('/upload', { method: 'POST', body: data });
  const js = await res.json();
  document.getElementById('log').textContent = js.paths.join('\n');
}

