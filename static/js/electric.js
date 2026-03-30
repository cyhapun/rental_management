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
  document.getElementById('edit_price').value = row.dataset.price || 3000;
  const form = document.getElementById('editReadingForm');
  form.action = `/electric/${id}/update`;
  const modal = new bootstrap.Modal(document.getElementById('editReadingModal'));
  modal.show();
}

function filterElectric(){
  const q = (document.getElementById('electricSearch').value || '').toLowerCase();
  const rows = document.querySelectorAll('#electricTableBody tr.data-row');
  const noSearchRow = document.getElementById('noSearchResultRow');
  const emptyDbRow = document.getElementById('emptyDbRow');
  let visibleCount = 0;
  
  if (emptyDbRow && emptyDbRow.style.display !== 'none') { return; }
  
  rows.forEach(r => { 
    // Dùng textContent thay cho innerText để an toàn với HTML ẩn
    if (r.textContent.toLowerCase().includes(q)) { 
        r.style.display = ''; 
        visibleCount++; 
    } else { 
        r.style.display = 'none'; 
    } 
  });
  
  if (visibleCount === 0 && rows.length > 0) {
      noSearchRow.style.display = ''; 
  } else if (noSearchRow) {
      noSearchRow.style.display = 'none';
  }
}

function sortElectric(){
  const sortVal = document.getElementById('electricSort').value;
  const tbody = document.getElementById('electricTableBody');
  const rows = Array.from(tbody.querySelectorAll('tr.data-row')); // Chỉ sort các hàng chứa data
  
  rows.sort((a,b) => {
    // Lấy dữ liệu thuần túy từ dataset thay vì moi từ HTML
    const monthA = a.dataset.month || '';
    const monthB = b.dataset.month || '';
    const usageA = parseInt(a.dataset.usage || '0', 10);
    const usageB = parseInt(b.dataset.usage || '0', 10);
    
    if (sortVal === 'month_desc') return monthB.localeCompare(monthA);
    if (sortVal === 'month_asc') return monthA.localeCompare(monthB);
    if (sortVal === 'usage_desc') return usageB - usageA;
    if (sortVal === 'usage_asc') return usageA - usageB;
    return 0;
  });
  
  rows.forEach(r => tbody.appendChild(r));
}

document.addEventListener('DOMContentLoaded', function(){
  const input = document.getElementById('electricSearch'); 
  if (input) input.addEventListener('input', filterElectric);
  
  const s = document.getElementById('electricSort'); 
  if (s) s.addEventListener('change', sortElectric);
});