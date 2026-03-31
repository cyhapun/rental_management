// accounts.js - behaviors for accounts page (CSR Model)

function filterAccounts(){
  const q = (document.getElementById('accountSearch').value || '').toLowerCase();
  
  document.querySelectorAll('#accountsTable tbody tr[data-account-id]').forEach(r => {
    const username = (r.dataset.username || '').toLowerCase();
    const role = (r.dataset.role || '').toLowerCase();
    
    if (username.includes(q) || role.includes(q)) {
        r.style.display = '';
    } else {
        r.style.display = 'none';
    }
  });
}

function openEditAccount(btn){
  const row = btn.closest('tr');
  const id = row.dataset.accountId;
  
  document.getElementById('edit_account_username').value = row.dataset.username || '';
  document.getElementById('edit_account_role').value = row.dataset.role || 'manager';
  
  const form = document.getElementById('editAccountForm');
  form.action = `/accounts/${id}/update`;
  
  const modal = new bootstrap.Modal(document.getElementById('editAccountModal'));
  modal.show();
}

function togglePassword(id){
  const el = document.getElementById(id);
  if (!el) return;
  
  const icon = el.nextElementSibling.querySelector('i');
  
  if (el.type === 'password') {
      el.type = 'text';
      icon.classList.remove('fa-eye');
      icon.classList.add('fa-eye-slash');
  } else {
      el.type = 'password';
      icon.classList.remove('fa-eye-slash');
      icon.classList.add('fa-eye');
  }
}

function validateCreateAccount(form){
  const pw = document.getElementById('create_password').value || '';
  const pwc = document.getElementById('create_password_confirm').value || '';
  if (pw !== pwc){
    try {
        const notyf = new Notyf({position: {x: 'right', y: 'top'}});
        notyf.error('Mật khẩu và xác nhận mật khẩu không khớp!');
    } catch(e) {
        alert('Mật khẩu và xác nhận mật khẩu không khớp!');
    }
    return false;
  }
  return true;
}

// HÀM FETCH DỮ LIỆU TỪ SERVER VÀ VẼ GIAO DIỆN BẢNG
async function loadAccounts() {
    const tbody = document.getElementById('accountsBody');
    if (!tbody) return;

    try {
        const response = await fetch('/accounts/_data');
        if (!response.ok) throw new Error("Fetch failed");
        
        const data = await response.json();
        
        // Cập nhật thẻ đếm tổng tài khoản
        document.getElementById('val-total-accounts').innerText = data.total || 0;

        tbody.innerHTML = '';
        if (!data.accounts || data.accounts.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-4">Chưa có dữ liệu tài khoản.</td></tr>';
            return;
        }

        data.accounts.forEach(a => {
            const tr = document.createElement('tr');
            tr.dataset.accountId = a.id || '';
            tr.dataset.username = a.username || '';
            tr.dataset.role = a.role || '';

            const firstChar = (a.username || '?').charAt(0).toUpperCase();
            
            const roleHtml = (a.role === 'admin') 
                ? '<span class="badge bg-danger-subtle text-danger border border-danger-subtle px-3 py-1 rounded-pill"><i class="fa-solid fa-crown me-1"></i> Admin</span>'
                : '<span class="badge bg-success-subtle text-success border border-success-subtle px-3 py-1 rounded-pill"><i class="fa-solid fa-user-tie me-1"></i> Manager</span>';

            tr.innerHTML = `
                <td>
                  <div class="d-flex align-items-center">
                    <div class="avatar-circle bg-secondary-subtle text-secondary me-3 shadow-sm d-none d-md-flex" style="width:36px; height:36px; border-radius:10px; align-items:center; justify-content:center; font-weight:bold; font-size:0.95rem;">
                      ${firstChar}
                    </div>
                    <span class="fw-bold text-dark">${a.username || ''}</span>
                  </div>
                </td>
                <td class="text-center">${roleHtml}</td>
                <td class="text-center text-muted">
                  <i class="fa-regular fa-calendar me-1"></i> ${a.created_at || '---'}
                </td>
                <td>
                  <div class="d-flex justify-content-center gap-1">
                    <button class="btn action-btn bg-primary-subtle text-primary" type="button" onclick="openEditAccount(this)" title="Sửa quyền/mật khẩu">
                      <i class="fa-solid fa-pen"></i>
                    </button>
                    <form action="/accounts/${a.id}/delete" method="post" style="display:inline" onsubmit="return confirm('Cảnh báo: Bạn có chắc chắn muốn xóa tài khoản ${a.username} không?');">
                      <button class="btn action-btn bg-danger-subtle text-danger" type="submit" title="Xóa tài khoản">
                        <i class="fa-solid fa-trash-can"></i>
                      </button>
                    </form>
                  </div>
                </td>
            `;
            tbody.appendChild(tr);
        });

        // Áp dụng bộ lọc ngay (nếu đang có chữ trong ô tìm kiếm)
        filterAccounts();
        
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger py-4"><i class="fa-solid fa-circle-exclamation me-2"></i>Lỗi khi tải dữ liệu</td></tr>';
        console.error("loadAccounts error", e);
    }
}

document.addEventListener('DOMContentLoaded', function(){
  const searchInput = document.getElementById('accountSearch');
  if(searchInput) {
      searchInput.addEventListener('input', filterAccounts);
  }

  // Tự động load khi vào trang
  const tbody = document.getElementById('accountsBody');
  if (tbody && tbody.dataset.autoLoad === 'true') {
      loadAccounts();
  }
});