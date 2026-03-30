// bills.js - behaviors for bills page
async function showBill(billId){
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
}

function filterBills(){
  const q = (document.getElementById('billSearch').value || '').toLowerCase();
  const rows = document.querySelectorAll('table tbody tr');
  rows.forEach(r=>{ r.style.display = r.innerText.toLowerCase().includes(q) ? '' : 'none'; });
}

function sortBills(){
  const sortVal = document.getElementById('billSort').value;
  const tbody = document.querySelector('table tbody');
  if(!tbody) return;
  const rows = Array.from(tbody.querySelectorAll('tr'));
  
  const monthVal = (r) => (r.children[1].innerText || '').trim();
  const totalVal = (r) => {
      const text = r.children[2].innerText || '0';
      return parseInt(text.replace(/[^\d]/g,''), 10) || 0;
  };

  rows.sort((a,b) => {
    if (sortVal === 'month_desc') return monthVal(b).localeCompare(monthVal(a));
    if (sortVal === 'month_asc') return monthVal(a).localeCompare(monthVal(b));
    if (sortVal === 'total_desc') return totalVal(b) - totalVal(a);
    if (sortVal === 'total_asc') return totalVal(a) - totalVal(b);
    return 0;
  });
  
  rows.forEach(r => tbody.appendChild(r));
}

document.addEventListener('DOMContentLoaded', function(){
  const input = document.getElementById('billSearch'); if (input) input.addEventListener('input', filterBills);
  const s = document.getElementById('billSort'); if (s) s.addEventListener('change', sortBills);
});

async function captureInvoiceImage(billId, btn){
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
      const fname = 'danh_sach_hoa_don-' + ts.getFullYear() + pad(ts.getMonth()+1) + pad(ts.getDate()) + '-' + pad(ts.getHours()) + pad(ts.getMinutes()) + '.png';
      const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = fname; document.body.appendChild(a); a.click(); a.remove(); setTimeout(()=>URL.revokeObjectURL(url), 1500);
      try{ new Notyf({position: (window.innerWidth<=576?{x:'center',y:'top'}:{x:'right',y:'top'})}).success('Đã lưu ảnh: ' + fname); }catch(e){}
    }, 'image/png');
    setTimeout(()=>{ const f = document.getElementById('invoice-capture-iframe'); if (f) f.remove(); }, 800);
    btn.innerHTML = origHtml;
  }catch(e){ console.error(e); try{ new Notyf().error('Không thể tạo ảnh hóa đơn'); }catch(err){}; btn.innerHTML = origHtml; }
}
