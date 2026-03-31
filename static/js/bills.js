// bills.js - behaviors for bills page

// 1. Xem Hóa Đơn
window.showBill = async function(billId) {
  const frame = document.getElementById('billViewFrame');
  (async ()=>{
    try{
      const resp = await fetch(`/invoice/print/${billId}`, { credentials: 'include' });
      const finalUrl = resp.url || '';
      const text = await resp.text();
      if (finalUrl.includes('/login') || /Đăng nhập|Đăng nh?p/.test(text)){
        try{ new Notyf().error('Bạn cần đăng nhập để xem hóa đơn'); }catch(e){}
        window.location.href = '/login';
        return;
      }
      frame.srcdoc = text;
      const modal = new bootstrap.Modal(document.getElementById('billViewModal'));
      modal.show();
    }catch(e){ console.error(e); try{ new Notyf().error('Không thể tải hóa đơn'); }catch(err){} }
  })();
};

// 2. Mở Modal Nhập Thanh Toán
window.openPayModal = function(billId, totalDue) {
  const form = document.getElementById('payBillForm');
  // Gắn URL xử lý cho Form
  form.action = `/bills/${billId}/pay`;
  // Tự động điền số tiền còn nợ
  document.getElementById('pay_amount').value = totalDue;
  // Hiện Modal
  const modal = new bootstrap.Modal(document.getElementById('payBillModal'));
  modal.show();
};

// 3. Tải/In Ảnh Hóa Đơn
window.captureInvoiceImage = async function(billId, btn) {
  try{
    const origHtml = btn.innerHTML; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    const resp = await fetch(`/invoice/print/${billId}`, { credentials: 'include' });
    const finalUrl = resp.url || '';
    const text = await resp.text();
    if (finalUrl.includes('/login') || /Đăng nhập|Đăng nh?p/.test(text)){
      try{ new Notyf().error('Bạn cần đăng nhập để xem hóa đơn'); }catch(e){}
      window.location.href = '/login'; return;
    }
    const iframe = document.createElement('iframe');
    iframe.style.position = 'fixed'; iframe.style.left = '-9999px'; iframe.style.top = '0'; iframe.style.width = '800px'; iframe.style.height = '1100px';
    iframe.id = 'invoice-capture-iframe'; document.body.appendChild(iframe);
    iframe.srcdoc = text;
    await new Promise((resolve)=>{ const tid = setTimeout(()=>{ resolve(); }, 1200); iframe.onload = ()=>{ clearTimeout(tid); resolve(); }; iframe.onerror = ()=>{ clearTimeout(tid); resolve(); }; });
    try{ const imgs = iframe.contentDocument.querySelectorAll('img'); await new Promise(res=>{ if (!imgs.length) return res(); let loaded = 0; const N = imgs.length; imgs.forEach(img=>{ if (img.complete) { if (++loaded===N) res(); } else img.addEventListener('load', ()=>{ if (++loaded===N) res(); }); img.addEventListener('error', ()=>{ if (++loaded===N) res(); }); }); }); }catch(e){}
    const scale = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
    const target = iframe.contentWindow.document.body;
    const canvas = await html2canvas(target, { scale: scale, backgroundColor: '#ffffff', useCORS: true });
    if (!canvas) throw new Error('Không thể tạo ảnh');
    canvas.toBlob(function(blob){
      const ts = new Date(); const pad = (n)=>String(n).padStart(2,'0');
      const fname = 'Hoa_don_tien_tro_' + ts.getFullYear() + pad(ts.getMonth()+1) + pad(ts.getDate()) + '_' + pad(ts.getHours()) + pad(ts.getMinutes()) + '.png';
      const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = fname; document.body.appendChild(a); a.click(); a.remove(); setTimeout(()=>URL.revokeObjectURL(url), 1500);
      try{ new Notyf({position: (window.innerWidth<=576?{x:'center',y:'top'}:{x:'right',y:'top'})}).success('Đã lưu ảnh Hóa đơn!'); }catch(e){}
    }, 'image/png');
    setTimeout(()=>{ const f = document.getElementById('invoice-capture-iframe'); if (f) f.remove(); }, 800);
    btn.innerHTML = origHtml;
  }catch(e){ console.error(e); try{ new Notyf().error('Không thể tạo ảnh hóa đơn'); }catch(err){}; btn.innerHTML = origHtml; }
};

// 4. Lọc & Tìm Kiếm
function filterBills(){
  const q = (document.getElementById('billSearch').value || '').toLowerCase();
  const rows = document.querySelectorAll('#billsTableBody tr.data-row');
  rows.forEach(r => { 
      const tName = (r.dataset.tenantName || '').toLowerCase();
      const room = (r.dataset.room || '').toLowerCase();
      const month = (r.dataset.month || '').toLowerCase();
      if (tName.includes(q) || room.includes(q) || month.includes(q)) r.style.display = '';
      else r.style.display = 'none';
  });
}

function sortBills(){
  const sortVal = document.getElementById('billSort').value;
  const tbody = document.getElementById('billsTableBody');
  if(!tbody) return;
  const rows = Array.from(tbody.querySelectorAll('tr.data-row'));
  rows.sort((a,b) => {
    const monthA = a.dataset.month || '';
    const monthB = b.dataset.month || '';
    const totalA = parseInt(a.dataset.total || '0', 10);
    const totalB = parseInt(b.dataset.total || '0', 10);
    if (sortVal === 'month_desc') return monthB.localeCompare(monthA);
    if (sortVal === 'month_asc') return monthA.localeCompare(monthB);
    if (sortVal === 'total_desc') return totalB - totalA;
    if (sortVal === 'total_asc') return totalA - totalB;
    return 0;
  });
  rows.forEach(r => tbody.appendChild(r));
}

document.addEventListener('DOMContentLoaded', function(){
  const input = document.getElementById('billSearch'); if (input) input.addEventListener('input', filterBills);
  const s = document.getElementById('billSort'); if (s) s.addEventListener('change', sortBills);
});