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
  const rows = document.querySelectorAll('#contractsTableBody tr');
  
  rows.forEach(r => {
    // Lấy nội dung mộc từ dataset, thay vì innerText để không dính icon HTML
    const tenant = (r.dataset.tenantName || '').toLowerCase();
    const room = (r.dataset.room || '').toLowerCase();
    const status = (r.dataset.status || '').toLowerCase();
    
    const okSearch = tenant.includes(q) || room.includes(q);
    const okPay = !payFilter || status.includes(payFilter);
    
    r.style.display = (okSearch && okPay) ? '' : 'none';
  });
}

function sortContracts(){
  const sortVal = document.getElementById('contractSort').value;
  const tbody = document.getElementById('contractsTableBody');
  if(!tbody) return;
  const rows = Array.from(tbody.querySelectorAll('tr'));
  
  rows.sort((a,b) => {
    const startA = a.dataset.startDateIso || a.dataset.startDate || '1900-01-01';
    const startB = b.dataset.startDateIso || b.dataset.startDate || '1900-01-01';
    const roomA = parseInt(a.dataset.room || '0', 10);
    const roomB = parseInt(b.dataset.room || '0', 10);
    
    if (sortVal === 'start_desc') return startB.localeCompare(startA);
    if (sortVal === 'start_asc') return startA.localeCompare(startB);
    if (sortVal === 'room_asc') return roomA - roomB;
    if (sortVal === 'room_desc') return roomB - roomA;
    return 0;
  });
  
  rows.forEach(r => tbody.appendChild(r));
}

document.addEventListener('DOMContentLoaded', function(){
  const input = document.getElementById('contractSearch'); if (input) input.addEventListener('input', filterContracts);
  const p = document.getElementById('contractPaymentFilter'); if (p) p.addEventListener('change', filterContracts);
  const s = document.getElementById('contractSort'); if (s) s.addEventListener('change', sortContracts);
  
  // Áp dụng Sort mặc định khi vừa tải trang
  try { sortContracts(); } catch(e) {}
});