// contracts.js - behaviors for contracts page
function openEditContract(btn){
  const row = btn.closest('tr');
  const id = row.dataset.contractId;
  document.getElementById('edit_contract_room').value = row.dataset.roomId || '';
  document.getElementById('edit_contract_tenant').value = row.dataset.tenantId || '';
  document.getElementById('edit_contract_start').value = row.dataset.startDateIso || row.dataset.startDate || '';
  document.getElementById('edit_contract_end').value = row.dataset.endDateIso || row.dataset.endDate || '';
  document.getElementById('edit_contract_type').value = row.dataset.contractType || '';
  document.getElementById('edit_contract_deposit').value = row.dataset.deposit || 0;
  const form = document.getElementById('editContractForm');
  form.action = `/contracts/${id}/update`;
  const modal = new bootstrap.Modal(document.getElementById('editContractModal'));
  modal.show();
}

function filterContracts(){
  const q = (document.getElementById('contractSearch').value || '').toLowerCase();
  const payFilter = (document.getElementById('contractPaymentFilter').value || '').toLowerCase();
  const rows = document.querySelectorAll('table tbody tr');
  rows.forEach(r=>{
    const text = r.innerText.toLowerCase();
    const okSearch = text.includes(q);
    const okPay = !payFilter || text.includes(payFilter);
    r.style.display = (okSearch && okPay) ? '' : 'none';
  });
}

function sortContracts(){
  const sortVal = document.getElementById('contractSort').value;
  const tbody = document.querySelector('table tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const getDate = (row, idx) => new Date((row.children[idx].innerText || '').trim() || '1900-01-01');
  const getRoom = (row) => {
    const txt = (row.children[1].innerText || '').trim();
    const m = txt.match(/\d+/);
    return m ? parseInt(m[0],10) : 0;
  };
  rows.sort((a,b)=>{
    if (sortVal === 'start_desc') return getDate(b,6) - getDate(a,6);
    if (sortVal === 'start_asc') return getDate(a,6) - getDate(b,6);
    if (sortVal === 'room_asc') return getRoom(a) - getRoom(b);
    if (sortVal === 'room_desc') return getRoom(b) - getRoom(a);
    return 0;
  });
  rows.forEach(r=>tbody.appendChild(r));
}

document.addEventListener('DOMContentLoaded', function(){
  const input = document.getElementById('contractSearch'); if (input) input.addEventListener('input', filterContracts);
  const p = document.getElementById('contractPaymentFilter'); if (p) p.addEventListener('change', filterContracts);
  const s = document.getElementById('contractSort'); if (s) s.addEventListener('change', sortContracts);
  try{ sortContracts(); }catch(e){}
});
