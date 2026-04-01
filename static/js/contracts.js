// contracts.js - behaviors for contracts page (CSR Model)

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
  const rows = document.querySelectorAll('#contractsTableBody tr[data-contract-id]');
  
  rows.forEach(r => {
    const tenant = (r.dataset.tenantName || '').toLowerCase();
    const room = (r.dataset.room || '').toLowerCase();
    const status = (r.dataset.status || '').toLowerCase();
    
    const okSearch = tenant.includes(q) || room.includes(q);
    const okPay = !payFilter || status.includes(payFilter);
    
    r.style.display = (okSearch && okPay) ? '' : 'none';
  });
}

function parseVnDate(dateStr) {
  if (!dateStr) return 0;
  if (dateStr.includes('-') && dateStr.length === 10) return new Date(dateStr).getTime() || 0;
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
  const rows = Array.from(tbody.querySelectorAll('tr[data-contract-id]'));
  
  rows.sort((a,b) => {
    const startA = parseVnDate(a.dataset.startDateIso || a.dataset.startDate);
    const startB = parseVnDate(b.dataset.startDateIso || b.dataset.startDate);
    
    const roomA = a.dataset.room || '';
    const roomB = b.dataset.room || '';
    
    if (sortVal === 'start_desc') return startB - startA;
    if (sortVal === 'start_asc') return startA - startB;
    if (sortVal === 'room_asc') return roomA.localeCompare(roomB, undefined, { numeric: true, sensitivity: 'base' });
    if (sortVal === 'room_desc') return roomB.localeCompare(roomA, undefined, { numeric: true, sensitivity: 'base' });
    return 0;
  });
  
  rows.forEach(r => tbody.appendChild(r));
}

// HÀM FETCH DỮ LIỆU TỪ SERVER VÀ VẼ GIAO DIỆN
async function loadContracts() {
    const tbody = document.getElementById('contractsTableBody');
    if (!tbody) return;
    
    const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || '';
    
    try {
        const response = await fetch('/contracts/_data');
        if (!response.ok) throw new Error("Fetch failed");
        
        const data = await response.json();
        
        // Cập nhật số liệu Metrics
        document.getElementById('val-active-rooms').innerText = data.active_rooms_count || 0;
        document.getElementById('val-active-tenants').innerText = data.active_tenants_count || 0;
        
        // Vẽ phần Cảnh báo Sắp đến hạn
        const duesContainer = document.getElementById('upcomingDuesContainer');
        if (data.upcoming_dues && data.upcoming_dues.length > 0) {
            let listHtml = data.upcoming_dues.map(u => `
                <li>Phòng ${u.room_number || '?'} - ${u.tenant_name || '?'}
                    ${u.days_left === 0 
                        ? '<strong class="text-danger">(Hôm nay đến kì hạn)</strong>' 
                        : `<strong class="text-secondary">(còn ${u.days_left} ngày)</strong>`}
                </li>
            `).join('');
            
            duesContainer.innerHTML = `
              <div class="bg-warning-subtle text-dark p-3 rounded-4 border border-warning-subtle d-flex shadow-sm h-100">
                <div class="me-3 mt-1"><i class="fa-solid fa-bell fs-4 text-warning"></i></div>
                <div>
                  <strong class="d-block mb-1">Chú ý: Có ${data.upcoming_dues.length} phòng sắp đến kì hạn thanh toán!</strong>
                  <ul class="mb-0 small ps-3">${listHtml}</ul>
                </div>
              </div>
            `;
            duesContainer.style.display = 'block';
        }

        // Xóa spinner bảng
        tbody.innerHTML = '';
        if (!data.contracts || data.contracts.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">Chưa có dữ liệu hợp đồng.</td></tr>';
            return;
        }

        const formatMoney = (amount) => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);
        const todayMonth = tbody.dataset.today || '';

        // Dựng HTML cho từng hàng
        data.contracts.forEach(c => {
            const tr = document.createElement('tr');
            if (c.is_active) tr.classList.add('row-active-contract');
            
            const tenantName = (c.tenant && c.tenant.full_name) ? c.tenant.full_name : (c.tenant_id || '?');
            const roomName = (c.room && c.room.room_number) ? c.room.room_number : (c.room_id || '?');
            const firstChar = tenantName.charAt(0).toUpperCase();
            
            let statusText = 'Chưa tới kì hạn';
            let badgeHtml = `<span class="badge bg-secondary-subtle text-secondary border border-secondary-subtle px-3 py-1 rounded-pill">Chưa tới kì hạn</span>`;
            
            if (c.rent_payment_status === 'paid') {
                statusText = 'Đã đóng';
                badgeHtml = `<span class="badge bg-success-subtle text-success border border-success-subtle px-3 py-1 rounded-pill">Đã đóng</span>`;
            } else if (c.rent_payment_status === 'unpaid') {
                statusText = 'Chưa đóng';
                badgeHtml = `<span class="badge bg-danger-subtle text-danger border border-danger-subtle px-3 py-1 rounded-pill">Chưa đóng</span>`;
            }

            tr.dataset.contractId = c.id;
            tr.dataset.tenantId = c.tenant_id || '';
            tr.dataset.tenantName = tenantName;
            tr.dataset.roomId = c.room_id || '';
            tr.dataset.room = roomName;
            tr.dataset.startDate = c.start_date || '';
            tr.dataset.endDate = c.end_date || '';
            tr.dataset.startDateIso = c.start_date_iso || '';
            tr.dataset.endDateIso = c.end_date_iso || '';
            tr.dataset.contractType = c.contract_type || '';
            tr.dataset.deposit = c.deposit || 0;
            tr.dataset.status = statusText;

            let endBtnHtml = '';
            if (c.is_active) {
                endBtnHtml = `
                <form action="/contracts/${c.id}/end" method="post" style="display:inline" onsubmit="return confirm('Bạn chắc chắn muốn KẾT THÚC hợp đồng này?');">
                    <button class="btn action-btn bg-warning-subtle text-warning" type="submit" title="Kết thúc"><i class="fa-solid fa-ban"></i></button>
                </form>`;
            }

            tr.innerHTML = `
                <td class="ps-4">
                  <div class="d-flex align-items-center">
                    <div class="avatar-circle bg-primary-subtle text-primary me-3 shadow-sm d-none d-md-flex" style="width:36px; height:36px; border-radius:10px; align-items:center; justify-content:center; font-weight:bold; font-size:0.95rem;">
                      ${firstChar}
                    </div>
                    <div>
                      <div class="fw-bold text-dark text-truncate" style="max-width: 180px;">${tenantName}</div>
                      ${!c.is_active ? '<div class="small text-muted mt-1"><i class="fa-solid fa-lock me-1"></i>Đã kết thúc</div>' : ''}
                    </div>
                  </div>
                </td>
                <td class="text-center">
                  <span class="badge bg-light text-dark border px-3 py-2 rounded-3 fs-6">${roomName}</span>
                </td>
                <td class="text-center fw-semibold text-dark">${(c.electric && c.electric.current_kwh) ? c.electric.current_kwh : 0}</td>
                <td class="text-center text-muted">${(c.electric && c.electric.used_kwh) ? c.electric.used_kwh : 0}</td>
                <td class="text-center fw-bold text-dark">${formatMoney(c.deposit || 0)}</td>
                <td class="text-center">${badgeHtml}</td>
                <td class="text-center">
                  <div class="text-success fw-bold small"><i class="fa-solid fa-calendar-plus me-1"></i>${c.start_date || ''}</div>
                  ${c.end_date ? `<div class="text-danger fw-bold small mt-1"><i class="fa-solid fa-calendar-xmark me-1"></i>${c.end_date}</div>` : ''}
                </td>
                <td class="text-center pe-3">
                  <div class="d-flex justify-content-center gap-1">
                    <button class="btn action-btn bg-primary-subtle text-primary" type="button" onclick="openEditContract(this)" title="Sửa"><i class="fa-solid fa-pen"></i></button>
                    <form action="/contracts/${c.id}/create_bill" method="post" style="display:inline">
                      <input type="hidden" name="month" value="${todayMonth}" />
                      <button class="btn action-btn bg-success-subtle text-success" type="submit" title="Tạo hóa đơn"><i class="fa-solid fa-file-invoice-dollar"></i></button>
                    </form>
                    ${endBtnHtml}
                    <form action="/contracts/${c.id}/delete" method="post" style="display:inline" onsubmit="return confirm('Cảnh báo: Xóa hợp đồng này sẽ xóa cả dữ liệu liên quan. Vẫn tiếp tục?');">
                      <input type="hidden" name="csrf_token" value="${csrfToken}">  
                      <button class="btn action-btn bg-danger-subtle text-danger" type="submit" title="Xóa"><i class="fa-solid fa-trash-can"></i></button>
                    </form>
                  </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
        
        // Gọi lại sắp xếp và bộ lọc sau khi đổ dữ liệu
        sortContracts();
        filterContracts();

    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-danger py-4"><i class="fa-solid fa-circle-exclamation me-2"></i>Lỗi khi tải dữ liệu hợp đồng</td></tr>';
        console.error("loadContracts error", e);
    }
}

document.addEventListener('DOMContentLoaded', function(){
  const input = document.getElementById('contractSearch'); if (input) input.addEventListener('input', filterContracts);
  const p = document.getElementById('contractPaymentFilter'); if (p) p.addEventListener('change', filterContracts);
  const s = document.getElementById('contractSort'); if (s) s.addEventListener('change', sortContracts);
  
  const tbody = document.getElementById('contractsTableBody');
  if (tbody && tbody.dataset.autoLoad === 'true') {
      loadContracts();
  }
});