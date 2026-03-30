// tenants.js - behaviors for tenants page

function filterTenants(){
  const q = document.getElementById('tenantSearch').value.toLowerCase();
  const genderFilter = (document.getElementById('tenantGenderFilter').value || '').toLowerCase();
  const statusFilter = (document.getElementById('tenantStatusFilter').value || '').toLowerCase();
  const rows = document.querySelectorAll('#tenantsTable tbody tr');
  
  rows.forEach(r => {
    // Tránh thẻ rỗng (khi chưa có dữ liệu)
    if (!r.dataset.tenantId) return;

    // Lấy dữ liệu thuần từ dataset thay vì innerText (tránh dính icon/html)
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
  const rows = Array.from(tbody.querySelectorAll('tr[data-tenant-id]')); // Chỉ sort hàng có data
  
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

// Chức năng bật/tắt CCCD đã đổi thành dạng Icon
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

document.addEventListener('DOMContentLoaded', function(){
  const input = document.getElementById('tenantSearch');
  if (input){ 
      input.addEventListener('input', filterTenants); 
      input.addEventListener('keydown', (e) => { if (e.key === 'Enter'){ e.preventDefault(); filterTenants(); }}); 
  }
  const g = document.getElementById('tenantGenderFilter'); if (g) g.addEventListener('change', filterTenants);
  const st = document.getElementById('tenantStatusFilter'); if (st) st.addEventListener('change', filterTenants);
  const s = document.getElementById('tenantSort'); if (s) s.addEventListener('change', sortTenants);
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