// electric.js - behaviors for electric page (CSR Model)

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
  let visibleCount = 0;
  
  rows.forEach(r => { 
    if (r.textContent.toLowerCase().includes(q)) { 
        r.style.display = ''; 
        visibleCount++; 
    } else { 
        r.style.display = 'none'; 
    } 
  });
  
  const noSearchRow = document.getElementById('noSearchResultRow');
  if (noSearchRow) {
      noSearchRow.style.display = (visibleCount === 0 && rows.length > 0) ? '' : 'none';
  }
}

function sortElectric(){
  const sortVal = document.getElementById('electricSort').value;
  const tbody = document.getElementById('electricTableBody');
  if(!tbody) return;
  const rows = Array.from(tbody.querySelectorAll('tr.data-row'));
  
  rows.sort((a,b) => {
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

// HÀM FETCH DỮ LIỆU TỪ SERVER VÀ VẼ GIAO DIỆN
async function loadElectric() {
    const tbody = document.getElementById('electricTableBody');
    if (!tbody) return;
    
    const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || '';

    try {
        const response = await fetch('/electric/_data');
        if (!response.ok) throw new Error("Fetch failed");
        
        const data = await response.json();
        
        // Lưu trữ last_indices vào Global để Form Thêm Mới dùng lại
        window.electricData = { last_indices: data.last_indices || {} };
        
        tbody.innerHTML = '';
        if (!data.readings || data.readings.length === 0) {
            tbody.innerHTML = '<tr id="emptyDbRow"><td colspan="6" class="text-center text-muted py-4">Hiện tại chưa có dữ liệu điện năng.</td></tr>';
            return;
        }

        data.readings.forEach(r => {
            const tr = document.createElement('tr');
            tr.className = 'data-row';
            tr.dataset.readingId = r.id;
            tr.dataset.month = r.month || '';
            tr.dataset.oldIndex = r.old_index || 0;
            tr.dataset.newIndex = r.new_index || 0;
            tr.dataset.price = r.price_per_kwh || 3000;
            tr.dataset.usage = r.usage || 0;

            const roomName = (r.room && r.room.room_number) ? r.room.room_number : (r.room_id || '?');

            tr.innerHTML = `
              <td>
                <span class="badge bg-light text-dark border px-2 py-1 fs-6">
                  <i class="fa-solid fa-door-closed text-muted me-1"></i> ${roomName}
                </span>
              </td>
              <td class="text-center">
                <span class="text-primary fw-semibold"><i class="fa-regular fa-calendar-alt me-1"></i>${r.month || ''}</span>
              </td>
              <td class="text-center text-muted">${r.old_index || 0}</td>
              <td class="text-center fw-semibold">${r.new_index || 0}</td>
              <td class="text-center">
                <span class="badge bg-warning-subtle text-dark border border-warning-subtle px-2 py-1 fs-6">
                  ${r.usage || 0} <small class="text-muted fw-normal ms-1">kWh</small>
                </span>
              </td>
              <td>
                <div class="d-flex justify-content-center gap-1">
                  <button class="btn action-btn bg-primary-subtle text-primary" type="button" onclick="openEditReading(this)" title="Sửa">
                    <i class="fa-solid fa-pen"></i>
                  </button>
                  <form action="/electric/${r.id}/delete" method="post" style="display:inline" onsubmit="return confirm('Cảnh báo: Bạn có chắc chắn muốn xóa bản ghi chỉ số điện này không?');">
                    <input type="hidden" name="csrf_token" value="${csrfToken}">  
                    <button class="btn action-btn bg-danger-subtle text-danger" type="submit" title="Xóa">
                      <i class="fa-solid fa-trash-can"></i>
                    </button>
                  </form>
                </div>
              </td>
            `;
            tbody.appendChild(tr);
        });
        
        // Thêm hàng ẩn cho việc tìm kiếm rỗng
        const noSearchRow = document.createElement('tr');
        noSearchRow.id = 'noSearchResultRow';
        noSearchRow.style.display = 'none';
        noSearchRow.innerHTML = '<td colspan="6" class="text-center text-muted py-4">Không tìm thấy dữ liệu phù hợp với từ khóa.</td>';
        tbody.appendChild(noSearchRow);

        // Gọi lại sắp xếp và bộ lọc
        sortElectric();
        filterElectric();
        
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger py-4"><i class="fa-solid fa-circle-exclamation me-2"></i>Lỗi khi tải dữ liệu</td></tr>';
        console.error("loadElectric error", e);
    }
}

document.addEventListener('DOMContentLoaded', function(){
  // Khởi tạo Lắng nghe sự kiện
  const input = document.getElementById('electricSearch'); 
  if (input) input.addEventListener('input', filterElectric);
  const s = document.getElementById('electricSort'); 
  if (s) s.addEventListener('change', sortElectric);

  // Auto-Load dữ liệu AJAX
  const tbody = document.getElementById('electricTableBody');
  if (tbody && tbody.dataset.autoLoad === 'true') {
      loadElectric();
  }

  // Khởi tạo Logic Tự Điền "Số Cũ" khi Chọn Phòng ở Modal Thêm Mới
  const roomSelect = document.getElementById('roomSelect');
  const oldIndexInput = document.getElementById('oldIndex');

  async function loadOldIndex(roomId) {
    if (!roomId) { oldIndexInput.value = ''; return; }
    const D = window.electricData || {};
    const initialLastIndices = D.last_indices || {};
    
    // Ưu tiên lấy từ RAM (Dữ liệu vừa fetch xong)
    try {
      if (initialLastIndices && Object.prototype.hasOwnProperty.call(initialLastIndices, roomId)) { 
          oldIndexInput.value = initialLastIndices[roomId] ?? 0; 
          return; 
      }
    } catch (e) { console.error(e); }
    
    // Nếu không có, gọi API fallback
    try {
      const res = await fetch(`/electric/last/${roomId}`);
      if (!res.ok) return;
      const data = await res.json();
      oldIndexInput.value = data.old_index ?? 0;
    } catch (e) { console.error(e); }
  }

  if (roomSelect) { roomSelect.addEventListener('change', function () { loadOldIndex(this.value); }); }
});