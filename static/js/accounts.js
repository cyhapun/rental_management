// accounts.js - behaviors for accounts page

function filterAccounts(){
  const q = (document.getElementById('accountSearch').value || '').toLowerCase();
  
  // Lọc thông qua thuộc tính data- thay vì text bên trong (để tránh lỗi do thẻ html/icon)
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
  
  // Nạp dữ liệu vào form sửa
  document.getElementById('edit_account_username').value = row.dataset.username || '';
  document.getElementById('edit_account_role').value = row.dataset.role || 'manager';
  
  // Cập nhật action cho form
  const form = document.getElementById('editAccountForm');
  form.action = `/accounts/${id}/update`;
  
  // Hiển thị modal
  const modal = new bootstrap.Modal(document.getElementById('editAccountModal'));
  modal.show();
}

// Bật tắt xem mật khẩu và thay đổi Icon con mắt
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

// Validate mật khẩu khi tạo
function validateCreateAccount(form){
  const pw = document.getElementById('create_password').value || '';
  const pwc = document.getElementById('create_password_confirm').value || '';
  if (pw !== pwc){
    // Sử dụng Notyf nếu có, nếu không thì dùng alert mặc định
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

// Tự động gắn event listener cho ô tìm kiếm
document.addEventListener('DOMContentLoaded', function(){
  const searchInput = document.getElementById('accountSearch');
  if(searchInput) {
      searchInput.addEventListener('input', filterAccounts);
  }
});