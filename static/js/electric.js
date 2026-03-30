// electric.js - behaviors for electric page
(function(){
  const D = window.electricData || {};
  document.addEventListener('DOMContentLoaded', function () {
    const initialLastIndices = D.last_indices || {};
    const roomSelect = document.getElementById('roomSelect');
    const oldIndexInput = document.getElementById('oldIndex');

    async function loadOldIndex(roomId) {
      if (!roomId) { oldIndexInput.value = ''; return; }
      try {
        if (initialLastIndices && Object.prototype.hasOwnProperty.call(initialLastIndices, roomId)) { oldIndexInput.value = initialLastIndices[roomId] ?? 0; return; }
      } catch (e) { console.error(e); }
      try {
        const res = await fetch(`/electric/last/${roomId}`);
        if (!res.ok) return;
        const data = await res.json();
        oldIndexInput.value = data.old_index ?? 0;
      } catch (e) { console.error(e); }
    }

    if (roomSelect) { roomSelect.addEventListener('change', function () { loadOldIndex(this.value); }); }
  });

})();

function openEditReading(btn){
  const row = btn.closest('tr');
  const id = row.dataset.readingId;
  document.getElementById('edit_month').value = row.dataset.month || '';
  document.getElementById('edit_old_index').value = row.dataset.oldIndex || 0;
  document.getElementById('edit_new_index').value = row.dataset.newIndex || 0;
  document.getElementById('edit_price').value = row.dataset.price || 2000;
  const form = document.getElementById('editReadingForm');
  form.action = `/electric/${id}/update`;
  const modal = new bootstrap.Modal(document.getElementById('editReadingModal'));
  modal.show();
}

function filterElectric(){
  const q = (document.getElementById('electricSearch').value || '').toLowerCase();
  const rows = document.querySelectorAll('table tbody tr.data-row');
  const noSearchRow = document.getElementById('noSearchResultRow');
  const emptyDbRow = document.getElementById('emptyDbRow');
  let visibleCount = 0;
  if (emptyDbRow && emptyDbRow.style.display !== 'none') { return; }
  rows.forEach(r => { if (r.innerText.toLowerCase().includes(q)) { r.style.display = ''; visibleCount++; } else { r.style.display = 'none'; } });
  if (visibleCount === 0 && rows.length > 0) noSearchRow.style.display = ''; else if (noSearchRow) noSearchRow.style.display = 'none';
}

function sortElectric(){
  const sortVal = document.getElementById('electricSort').value;
  const tbody = document.querySelector('table tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const monthVal = (r)=> (r.children[1].innerText || '').trim();
  const usageVal = (r)=> parseInt((r.children[4].innerText||'0').trim(),10) || 0;
  rows.sort((a,b)=>{
    if (sortVal==='month_desc') return monthVal(b).localeCompare(monthVal(a));
    if (sortVal==='month_asc') return monthVal(a).localeCompare(monthVal(b));
    if (sortVal==='usage_desc') return usageVal(b)-usageVal(a);
    if (sortVal==='usage_asc') return usageVal(a)-usageVal(b);
    return 0;
  });
  rows.forEach(r=>tbody.appendChild(r));
}

document.addEventListener('DOMContentLoaded', function(){
  const input = document.getElementById('electricSearch'); if (input) input.addEventListener('input', filterElectric);
  const s = document.getElementById('electricSort'); if (s) s.addEventListener('change', sortElectric);
});
