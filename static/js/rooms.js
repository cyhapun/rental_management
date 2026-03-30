// rooms.js - behaviors for rooms page
function filterRooms(){
  const q = (document.getElementById('roomSearch').value||'').toLowerCase();
  const status = (document.getElementById('roomStatusFilter').value || '').toLowerCase();
  const rows = document.querySelectorAll('#roomsTable tbody tr');
  rows.forEach(r=>{
    // Lấy textContent thay vì innerText để an toàn với HTML bên trong
    const room = r.cells[0]?.textContent.toLowerCase() || '';
    const st = r.cells[3]?.textContent.toLowerCase() || '';
    r.style.display = (room.includes(q) && (!status || st.includes(status))) ? '' : 'none';
  });
}

function sortRooms(){
  const sortVal = document.getElementById('roomSort').value;
  const tbody = document.querySelector('#roomsTable tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  
  // Trích xuất số phòng (bỏ ký tự thừa)
  const roomNo = (r) => parseInt((r.cells[0]?.textContent||'0').replace(/\D/g, ''), 10) || 0;
  const price = (r) => parseInt((r.dataset.roomPrice||'0').replace(/[^\d]/g,''), 10) || 0;
  
  rows.sort((a,b)=>{
    if (sortVal==='room_asc') return roomNo(a)-roomNo(b);
    if (sortVal==='room_desc') return roomNo(b)-roomNo(a);
    if (sortVal==='price_asc') return price(a)-price(b);
    if (sortVal==='price_desc') return price(b)-price(a);
    return 0;
  });
  rows.forEach(r=>tbody.appendChild(r));
}

document.addEventListener('DOMContentLoaded', function(){
  const input = document.getElementById('roomSearch');
  if (input){ 
    input.addEventListener('input', filterRooms); 
    input.addEventListener('keydown', (e)=>{ if (e.key === 'Enter'){ e.preventDefault(); filterRooms(); }}); 
  }
  const st = document.getElementById('roomStatusFilter'); if (st) st.addEventListener('change', filterRooms);
  const sort = document.getElementById('roomSort'); if (sort) sort.addEventListener('change', sortRooms);
  
  // Auto-load data if tbody requests it
  const tbody = document.getElementById('roomsBody');
  if (tbody && tbody.dataset && tbody.dataset.autoLoad === 'true'){
    const initialQ = tbody.dataset.initialQ || '';
    loadRooms(initialQ).then(()=>{ sortRooms(); filterRooms(); });
  }
});

async function loadRooms(q){
  const tbody = document.getElementById('roomsBody');
  if (!tbody) return;
  // show loading
  tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4"><span class="spinner-border spinner-border-sm text-primary me-2"></span>Đang tải dữ liệu...</td></tr>';
  try{
    const resp = await fetch(`/rooms/_list?q=${encodeURIComponent(q||'')}`);
    if (!resp.ok) throw new Error('Fetch failed');
    const rooms = await resp.json();
    tbody.innerHTML = '';
    const nf = new Intl.NumberFormat('vi-VN');
    
    if (rooms.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">Không tìm thấy phòng nào</td></tr>';
      return;
    }

    rooms.forEach(r=>{
      const tr = document.createElement('tr');
      tr.dataset.roomId = r.id || '';
      tr.dataset.roomNumber = r.room_number || '';
      tr.dataset.roomPrice = r.price || '';
      tr.dataset.roomElectricIndex = r.current_electric_index || 0;
      tr.dataset.roomStatus = r.status || '';
      
      const priceText = r.price != null ? nf.format(r.price) : '';
      
      // Giao diện Badge mới (Pastel)
      const statusHtml = (r.status === 'occupied') 
        ? '<div class="text-center"><span class="badge bg-warning-subtle text-warning border border-warning-subtle px-2 py-1"><i class="fa-solid fa-user-check me-1"></i>Đang thuê</span></div>' 
        : '<div class="text-center"><span class="badge bg-success-subtle text-success border border-success-subtle px-2 py-1"><i class="fa-solid fa-check me-1"></i>Trống</span></div>';
      
      // Giao diện Action Buttons mới (Icon Vuông)
      const actionHtml = `
        <div class="d-flex gap-1">
          <button type="button" class="btn action-btn bg-primary-subtle text-primary" onclick="openEditRoom(this)" title="Sửa thông tin">
            <i class="fa-solid fa-pen"></i>
          </button>
          <form action="/rooms/${r.id}/delete" method="post" style="display:inline" onsubmit="return confirm('Cảnh báo: Xóa phòng này sẽ mất các dữ liệu liên quan. Bạn có chắc chắn?');">
            <button type="submit" class="btn action-btn bg-danger-subtle text-danger" title="Xóa phòng">
              <i class="fa-solid fa-trash-can"></i>
            </button>
          </form>
        </div>
      `;

      tr.innerHTML = `
        <td>
          <span class="badge bg-light text-dark border px-2 py-1 fs-6">${r.room_number || ''}</span>
        </td>
        <td class="fw-semibold text-dark">${priceText}</td>
        <td><span class="text-muted"><i class="fa-solid fa-bolt text-warning me-1"></i>${r.current_electric_index || 0}</span></td>
        <td>${statusHtml}</td>
        <td>${actionHtml}</td>
      `;
      tbody.appendChild(tr);
    });
  }catch(e){
    tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger py-4"><i class="fa-solid fa-circle-exclamation me-2"></i>Lỗi khi tải dữ liệu</td></tr>';
    console.error('loadRooms error', e);
  }
}

function openEditRoom(btn){
  const row = btn.closest('tr');
  const roomId = row.dataset.roomId;
  document.getElementById('edit_room_number').value = row.dataset.roomNumber || '';
  document.getElementById('edit_room_price').value = row.dataset.roomPrice || '';
  document.getElementById('edit_room_electric_index').value = row.dataset.roomElectricIndex || '0';
  document.getElementById('edit_room_status').value = row.dataset.roomStatus || 'available';
  const form = document.getElementById('editRoomForm');
  form.action = `/rooms/${roomId}/update`;
  const modal = new bootstrap.Modal(document.getElementById('editRoomModal'));
  modal.show();
}