document.addEventListener('DOMContentLoaded', () => {
  const labSelect = document.getElementById('labSelect');
  const searchBtn = document.getElementById('searchBtn');
  const qInput = document.getElementById('q');
  const statusInput = document.getElementById('status');
  const tableBody = document.getElementById('tableBody');
  const showImport = document.getElementById('showImport');
  const importArea = document.getElementById('importArea');
  const importForm = document.getElementById('importForm');
  const importMsg = document.getElementById('importMsg');
  const cancelImport = document.getElementById('cancelImport');

  fetch('/api/labs').then(r=>r.json()).then(labs=>{
    for(const l of labs){
      const o = document.createElement('option');
      o.value = l.name;
      o.textContent = l.name;
      labSelect.appendChild(o);
    }
  });

  async function doSearch(){
    const params = new URLSearchParams();
    const labName = labSelect.value;
    if(labName) {
      // we need lab id for filtering: fetch labs to find id
      const labs = await fetch('/api/labs').then(r=>r.json());
      const lab = labs.find(x=>x.name===labName);
      if(lab) params.set('lab_id', lab.id);
    }
    if(qInput.value) params.set('q', qInput.value);
    if(statusInput.value) params.set('status', statusInput.value);
    const url = '/api/search?' + params.toString();
    const items = await fetch(url).then(r=>r.json());
    tableBody.innerHTML = '';
    for(const it of items){
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${new Date(it.audit_date).toLocaleString()}</td>
                      <td>${it.lab_name}</td>
                      <td>${it.code}</td>
                      <td>${it.name}</td>
                      <td>${it.system_qty ?? ''}</td>
                      <td>${it.physical_qty ?? ''}</td>
                      <td>${it.status ?? ''}</td>`;
      tableBody.appendChild(tr);
    }
  }

  searchBtn.addEventListener('click', doSearch);

  showImport.addEventListener('click', () => {
    importArea.style.display = 'block';
  });
  cancelImport.addEventListener('click', () => {
    importArea.style.display = 'none';
  });

  importForm.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    importMsg.textContent = 'Enviando...';
    const formData = new FormData(importForm);
    const res = await fetch('/api/import_csv', { method: 'POST', body: formData });
    const json = await res.json();
    if(res.ok){
      importMsg.textContent = 'Importado com sucesso. Audit ID: ' + json.audit_id;
      importForm.reset();
    } else {
      importMsg.textContent = 'Erro: ' + (json.error || JSON.stringify(json));
    }
  });

  // run initial search
  doSearch();
});
