// tenants.js - behaviors for tenants page
function filterTenants(){
  const q = document.getElementById('tenantSearch').value.toLowerCase();
  const genderFilter = (document.getElementById('tenantGenderFilter').value || '').toLowerCase();
  const statusFilter = (document.getElementById('tenantStatusFilter').value || '').toLowerCase();
  const rows = document.querySelectorAll('#tenantsTable tbody tr');
  rows.forEach(r=>{
    const name = (r.cells[0].innerText || '').toLowerCase();
    const phone = (r.cells[1].innerText || '').toLowerCase();
    const gender = (r.cells[2].innerText || '').toLowerCase();
    const birthYear = (r.cells[3].innerText || '').toLowerCase();
    const rentalStatus = (r.cells[4].innerText || '').toLowerCase();
    const cccdFull = (r.dataset.cccdFull || '').toLowerCase();
    const cccdMasked = (r.dataset.cccdMasked || '').toLowerCase();
    const okSearch = (name.includes(q) || phone.includes(q) || gender.includes(q) || birthYear.includes(q) || rentalStatus.includes(q) || cccdFull.includes(q) || cccdMasked.includes(q));
    const okGender = !genderFilter || gender.includes(genderFilter);
    const okStatus = !statusFilter || rentalStatus.includes(statusFilter);
    r.style.display = (okSearch && okGender && okStatus) ? '' : 'none';
  });
}

function sortTenants(){
  const sortVal = document.getElementById('tenantSort').value;
  const tbody = document.querySelector('#tenantsTable tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  rows.sort((a,b)=>{
    const nameA = (a.cells[0].innerText || '').trim();
    const nameB = (b.cells[0].innerText || '').trim();
    const yA = parseInt((a.cells[3].innerText || '0').trim(),10) || 0;
    const yB = parseInt((b.cells[3].innerText || '0').trim(),10) || 0;
    if (sortVal==='name_asc') return nameA.localeCompare(nameB,'vi');
    if (sortVal==='name_desc') return nameB.localeCompare(nameA,'vi');
    if (sortVal==='year_asc') return yA-yB;
    if (sortVal==='year_desc') return yB-yA;
    return 0;
  });
  rows.forEach(r=>tbody.appendChild(r));
}

function toggleCccd(btn){
  const row = btn.closest('tr');
  const masked = row.querySelector('.cccd-masked');
  const full = row.querySelector('.cccd-full');
  const isFullShown = full.style.display !== 'none';
  if (isFullShown){ full.style.display = 'none'; masked.style.display = ''; btn.textContent = 'Hiện'; }
  else { full.style.display = ''; masked.style.display = 'none'; btn.textContent = 'Ẩn'; }
}

document.addEventListener('DOMContentLoaded', function(){
  const input = document.getElementById('tenantSearch');
  if (input){ input.addEventListener('input', filterTenants); input.addEventListener('keydown', (e)=>{ if (e.key === 'Enter'){ e.preventDefault(); filterTenants(); }}); }
  const g = document.getElementById('tenantGenderFilter'); if (g) g.addEventListener('change', filterTenants);
  const st = document.getElementById('tenantStatusFilter'); if (st) st.addEventListener('change', filterTenants);
  const s = document.getElementById('tenantSort'); if (s) s.addEventListener('change', sortTenants);
});

function openEditTenant(btn){
  const row = btn.closest('tr');
  const id = row.dataset.tenantId;
  document.getElementById('edit_full_name').value = row.dataset.fullName || '';
  document.getElementById('edit_phone').value = row.dataset.phone || '';
  document.getElementById('edit_gender').value = row.dataset.gender || '';
  document.getElementById('edit_birth_year').value = row.dataset.birthYear || '';
  document.getElementById('edit_cccd').value = row.dataset.cccdFull || '';
  document.getElementById('edit_rental_status').value = row.dataset.rentalStatus || 'Đã kết thúc';
  const form = document.getElementById('editTenantForm'); form.action = `/tenants/${id}/update`;
  const modal = new bootstrap.Modal(document.getElementById('editTenantModal')); modal.show();
}
