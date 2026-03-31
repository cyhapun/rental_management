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
    const tenant = (r.dataset.tenantName || '').toLowerCase();
    const room = (r.dataset.room || '').toLowerCase();
    const status = (r.dataset.status || '').toLowerCase();
    
    const okSearch = tenant.includes(q) || room.includes(q);
    const okPay = !payFilter || status.includes(payFilter);
    
    r.style.display = (okSearch && okPay) ? '' : 'none';
  });
}

// Thuật toán parse chuỗi Ngày Tháng ở VN sang Timestamp
function parseVnDate(dateStr) {
  if (!dateStr) return 0;
  // Nếu đã là ISO (YYYY-MM-DD)
  if (dateStr.includes('-') && dateStr.length === 10) return new Date(dateStr).getTime() || 0;
  // Nếu là định dạng DD/MM/YYYY
  const parts = dateStr.split('/');
  if (parts.length === 3) {
    return new Date(`${parts[2]}-${parts[1]}-${parts[0]}`).getTime() || 0;
  }
  return 0;
}

function sortContracts(){
  const sortVal = document.getElementById('contractSort').value;
  const tbody = document.getElementById('contractsTableBody');
  if(!tbody) return;
  const rows = Array.from(tbody.querySelectorAll('tr'));
  
  rows.sort((a,b) => {
    // So sánh thời gian sử dụng Timestamp để chính xác tuyệt đối
    const startA = parseVnDate(a.dataset.startDateIso || a.dataset.startDate);
    const startB = parseVnDate(b.dataset.startDateIso || b.dataset.startDate);
    
    const roomA = a.dataset.room || '';
    const roomB = b.dataset.room || '';
    
    if (sortVal === 'start_desc') return startB - startA;
    if (sortVal === 'start_asc') return startA - startB;
    
    // Tùy chọn numeric: true giúp máy tính hiểu số 10 lớn hơn số 2
    if (sortVal === 'room_asc') return roomA.localeCompare(roomB, undefined, { numeric: true, sensitivity: 'base' });
    if (sortVal === 'room_desc') return roomB.localeCompare(roomA, undefined, { numeric: true, sensitivity: 'base' });
    
    return 0;
  });
  
  rows.forEach(r => tbody.appendChild(r));
}

document.addEventListener('DOMContentLoaded', function(){
  const input = document.getElementById('contractSearch'); if (input) input.addEventListener('input', filterContracts);
  const p = document.getElementById('contractPaymentFilter'); if (p) p.addEventListener('change', filterContracts);
  const s = document.getElementById('contractSort'); if (s) s.addEventListener('change', sortContracts);
  
  try { sortContracts(); } catch(e) {}
});