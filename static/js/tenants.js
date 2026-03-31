// tenants.js - behaviors for tenants page (CSR Model)

function filterTenants(){
  const q = document.getElementById('tenantSearch').value.toLowerCase();
  const genderFilter = (document.getElementById('tenantGenderFilter').value || '').toLowerCase();
  const statusFilter = (document.getElementById('tenantStatusFilter').value || '').toLowerCase();
  const rows = document.querySelectorAll('#tenantsTable tbody tr');
  
  rows.forEach(r => {
    if (!r.dataset.tenantId) return;

    const name = (r.dataset.fullName || '').toLowerCase();
    const phone = (r.dataset.phone || '').toLowerCase();
    const gender = (r.dataset.gender || '').toLowerCase();
    const birthYear = (r.dataset.birthYear || '').toLowerCase();
    const rentalStatus = (r.dataset.rentalStatus || '').toLowerCase();
    const cccdFull = (r.dataset.cccdFull || '').toLowerCase();
    const cccdMasked = (r.dataset.cccdMasked || '').toLowerCase();

    const okSearch = (name.includes(q) || phone.includes(q) || gender.includes(q) || birthYear.includes(q) || rentalStatus.includes(q) || cccdFull.includes(q) || cccdMasked.includes(q));
    const okGender = !genderFilter || gender === genderFilter;
    const okStatus = !statusFilter || rentalStatus === statusFilter;

    r.style.display = (okSearch && okGender && okStatus) ? '' : 'none';
  });
}

function sortTenants(){
  const sortVal = document.getElementById('tenantSort').value;
  const tbody = document.querySelector('#tenantsTable tbody');
  const rows = Array.from(tbody.querySelectorAll('tr[data-tenant-id]')); 
  
  rows.sort((a,b)=>{
    const nameA = (a.dataset.fullName || '').trim();
    const nameB = (b.dataset.fullName || '').trim();
    const yA = parseInt((a.dataset.birthYear || '0').trim(), 10) || 0;
    const yB = parseInt((b.dataset.birthYear || '0').trim(), 10) || 0;

    if (sortVal==='name_asc') return nameA.localeCompare(nameB, 'vi');
    if (sortVal==='name_desc') return nameB.localeCompare(nameA, 'vi');
    if (sortVal==='year_asc') return yA-yB;
    if (sortVal==='year_desc') return yB-yA;
    return 0;
  });
  rows.forEach(r => tbody.appendChild(r));
}

function toggleCccd(btn){
  const row = btn.closest('tr');
  const masked = row.querySelector('.cccd-masked');
  const full = row.querySelector('.cccd-full');
  const isFullShown = full.style.display !== 'none';
  
  if (isFullShown) { 
      full.style.display = 'none'; 
      masked.style.display = ''; 
      btn.innerHTML = '<i class="fa-regular fa-eye"></i>'; 
      btn.title = "Hiện";
  } else { 
      full.style.display = ''; 
      masked.style.display = 'none'; 
      btn.innerHTML = '<i class="fa-regular fa-eye-slash"></i>'; 
      btn.title = "Ẩn";
  }
}

// HÀM FETCH API (MỚI)
async function loadTenants(q){
    const tbody = document.getElementById('tenantsBody');
    if (!tbody) return;
    
    tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4"><span class="spinner-border spinner-border-sm text-primary me-2"></span>Đang tải dữ liệu...</td></tr>';
    
    try {
        const resp = await fetch(`/tenants/_list?q=${encodeURIComponent(q||'')}`);
        if (!resp.ok) throw new Error('Fetch failed');
        const tenants = await resp.json();
        
        tbody.innerHTML = '';
        if (tenants.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">Chưa có dữ liệu khách thuê.</td></tr>';
            return;
        }

        tenants.forEach(t => {
            const tr = document.createElement('tr');
            // Gắn dataset để dùng cho Filter/Sort
            tr.dataset.tenantId = t.id || '';
            tr.dataset.fullName = t.full_name || '';
            tr.dataset.phone = t.phone || '';
            tr.dataset.gender = t.gender || '';
            tr.dataset.birthYear = t.birth_year || '';
            tr.dataset.rentalStatus = t.rental_status || '';
            tr.dataset.cccdFull = t.cccd_full || '';
            tr.dataset.cccdMasked = t.cccd || '';

            const firstChar = (t.full_name || 'U').charAt(0).toUpperCase();
            
            const phoneHtml = t.phone 
                ? `<div class="text-muted"><i class="fa-solid fa-phone me-2" style="font-size: 0.8rem;"></i>${t.phone}</div>`
                : `<span class="text-muted fst-italic">Chưa có</span>`;
                
            const statusHtml = (t.rental_status === "Đang thuê")
                ? `<span class="badge bg-warning-subtle text-warning border border-warning-subtle px-2 py-1"><i class="fa-solid fa-house-user me-1"></i>Đang thuê</span>`
                : `<span class="badge bg-secondary-subtle text-secondary border border-secondary-subtle px-2 py-1">Đã kết thúc</span>`;

            tr.innerHTML = `
                <td>
                    <div class="d-flex align-items-center">
                        <div class="avatar-circle bg-primary-subtle text-primary me-3 shadow-sm d-none d-md-flex" style="width:36px; height:36px; border-radius:10px; align-items:center; justify-content:center; font-weight:bold; font-size:0.95rem;">
                            ${firstChar}
                        </div>
                        <span class="fw-semibold text-dark">${t.full_name || ''}</span>
                    </div>
                </td>
                <td>${phoneHtml}</td>
                <td class="text-center">${t.gender || ''}</td>
                <td class="text-center">${t.birth_year || ''}</td>
                <td>
                    <div class="d-flex align-items-center">
                        <span class="cccd-masked me-2 text-dark">${t.cccd || ''}</span>
                        <span class="cccd-full me-2 text-dark" style="display:none;">${t.cccd_full || ''}</span>
                        <button type="button" class="btn-toggle-cccd" onclick="toggleCccd(this)" title="Hiện/Ẩn">
                            <i class="fa-regular fa-eye"></i>
                        </button>
                    </div>
                </td>
                <td class="text-center">${statusHtml}</td>
                <td>
                    <div class="d-flex justify-content-center gap-1">
                        <button type="button" class="btn action-btn bg-primary-subtle text-primary" onclick="openEditTenant(this)" title="Sửa thông tin">
                            <i class="fa-solid fa-pen"></i>
                        </button>
                        <form action="/tenants/${t.id}/delete" method="post" style="display:inline" onsubmit="return confirm('Cảnh báo: Xóa khách thuê này? Bạn nên đảm bảo họ đã thanh toán đủ tiền trước khi xóa.');">
                            <button type="submit" class="btn action-btn bg-danger-subtle text-danger" title="Xóa">
                                <i class="fa-solid fa-trash-can"></i>
                            </button>
                        </form>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch(e) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-danger py-4"><i class="fa-solid fa-circle-exclamation me-2"></i>Lỗi khi tải dữ liệu</td></tr>';
        console.error('loadTenants error', e);
    }
}

document.addEventListener('DOMContentLoaded', function(){
    const input = document.getElementById('tenantSearch');
    if (input){ 
        input.addEventListener('input', filterTenants); 
        input.addEventListener('keydown', (e) => { if (e.key === 'Enter'){ e.preventDefault(); filterTenants(); }}); 
    }
    const g = document.getElementById('tenantGenderFilter'); if (g) g.addEventListener('change', filterTenants);
    const st = document.getElementById('tenantStatusFilter'); if (st) st.addEventListener('change', filterTenants);
    const s = document.getElementById('tenantSort'); if (s) s.addEventListener('change', sortTenants);
    
    // Auto-load data if tbody requests it
    const tbody = document.getElementById('tenantsBody');
    if (tbody && tbody.dataset && tbody.dataset.autoLoad === 'true'){
        const initialQ = tbody.dataset.initialQ || '';
        loadTenants(initialQ).then(() => { 
            sortTenants(); 
            filterTenants(); 
        });
    }
});

function openEditTenant(btn){
  const row = btn.closest('tr');
  const id = row.dataset.tenantId;
  document.getElementById('edit_full_name').value = row.dataset.fullName || '';
  document.getElementById('edit_phone').value = row.dataset.phone || '';
  document.getElementById('edit_gender').value = row.dataset.gender || 'Nam';
  document.getElementById('edit_birth_year').value = row.dataset.birthYear || '';
  document.getElementById('edit_cccd').value = row.dataset.cccdFull || '';
  document.getElementById('edit_rental_status').value = row.dataset.rentalStatus || 'Đã kết thúc';
  
  const form = document.getElementById('editTenantForm'); 
  form.action = `/tenants/${id}/update`;
  const modal = new bootstrap.Modal(document.getElementById('editTenantModal')); 
  modal.show();
}