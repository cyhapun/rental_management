// accounts.js - behaviors for accounts page
function filterAccounts(){
  const q = (document.getElementById('accountSearch').value||'').toLowerCase();
  document.querySelectorAll('#accountsTable tbody tr').forEach(r=>{
    r.style.display = r.innerText.toLowerCase().includes(q) ? '' : 'none';
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
  el.type = el.type === 'password' ? 'text' : 'password';
}

function validateCreateAccount(form){
  const pw = document.getElementById('create_password').value || '';
  const pwc = document.getElementById('create_password_confirm').value || '';
  if (pw !== pwc){
    alert('Mật khẩu và xác nhận mật khẩu không khớp');
    return false;
  }
  return true;
}
