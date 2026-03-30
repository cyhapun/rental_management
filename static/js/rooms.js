// rooms.js - behaviors for rooms page
function filterRooms(){
  const q = (document.getElementById('roomSearch').value||'').toLowerCase();
  const status = (document.getElementById('roomStatusFilter').value || '').toLowerCase();
  const rows = document.querySelectorAll('#roomsTable tbody tr');
  rows.forEach(r=>{
    const room = r.cells[0].innerText.toLowerCase();
    const st = r.cells[3].innerText.toLowerCase();
    r.style.display = (room.includes(q) && (!status || st.includes(status))) ? '' : 'none';
  });
}

function sortRooms(){
  const sortVal = document.getElementById('roomSort').value;
  const tbody = document.querySelector('#roomsTable tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const roomNo = (r)=> parseInt((r.cells[0].innerText||'0').trim(),10) || 0;
  const price = (r)=> parseInt((r.dataset.roomPrice||'0').replace(/[^\d]/g,''),10) || 0;
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
  if (input){ input.addEventListener('input', filterRooms); input.addEventListener('keydown', (e)=>{ if (e.key === 'Enter'){ e.preventDefault(); filterRooms(); }}); }
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
  tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Đang tải dữ liệu…</td></tr>';
  try{
    const resp = await fetch(`/rooms/_list?q=${encodeURIComponent(q||'')}`);
    if (!resp.ok) throw new Error('Fetch failed');
    const rooms = await resp.json();
    tbody.innerHTML = '';
    const nf = new Intl.NumberFormat('vi-VN');
    rooms.forEach(r=>{
      const tr = document.createElement('tr');
      tr.dataset.roomId = r.id || '';
      tr.dataset.roomNumber = r.room_number || '';
      tr.dataset.roomPrice = r.price || '';
      tr.dataset.roomElectricIndex = r.current_electric_index || 0;
      tr.dataset.roomStatus = r.status || '';
      const priceText = r.price != null ? nf.format(r.price) : '';
      const statusHtml = (r.status === 'occupied') ? '<span class="badge bg-warning text-dark">Đang thuê</span>' : '<span class="badge bg-success">Trống</span>';
      tr.innerHTML = `<td>${r.room_number || ''}</td><td>${priceText}</td><td>${r.current_electric_index || 0}</td><td>${statusHtml}</td><td><button type="button" class="btn btn-sm btn-outline-primary me-2" onclick="openEditRoom(this)">Sửa</button><form action="/rooms/${r.id}/delete" method="post" style="display:inline"><button class="btn btn-sm btn-outline-danger">Xóa</button></form></td>`;
      tbody.appendChild(tr);
    });
  }catch(e){
    tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Lỗi khi tải dữ liệu</td></tr>';
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
