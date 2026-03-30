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
});

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
