// bills.js - behaviors for bills page (CSR Model)

// Hàm Format Tiền Tệ
const formatMoney = (amount) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);
};

// 1. Fetch dữ liệu & Build HTML bảng Hóa đơn
async function loadBills() {
    const tbody = document.getElementById('billsTableBody');
    if (!tbody) return;

    const currentStatus = tbody.dataset.status || 'all';
    // Lấy giá trị của bộ lọc thời gian (Mặc định là month)
    const timeFilter = document.getElementById('timeFilter')?.value || 'month';
    const csrfToken = document.getElementById('global_csrf_token')?.value || '';

    try {
        // Truyền thêm param time_filter
        const response = await fetch(`/bills/_data?status=${currentStatus}&time_filter=${timeFilter}`);
        if (!response.ok) throw new Error("Lỗi khi tải hóa đơn");
        
        const bills = await response.json();
        window.currentBillsData = bills; // Lưu biến global để modal đọc lấy dữ liệu
        
        if (bills.length === 0) {
            tbody.innerHTML = `
              <tr>
                <td colspan="6">
                  <div class="p-5 text-center">
                    <i class="fa-solid fa-box-open text-muted mb-3" style="font-size: 3rem; opacity: 0.5;"></i>
                    <p class="text-muted fw-semibold mb-0">Không có dữ liệu trong thời gian này.</p>
                  </div>
                </td>
              </tr>`;
            return;
        }

        // Tạo một mảng để chứa các thẻ HTML (nhanh hơn appendChild)
        const htmlRows = bills.map(b => {
            const tenantName = (b.contract_display && b.contract_display.tenant_name) ? b.contract_display.tenant_name : '';
            const roomNumber = (b.contract_display && b.contract_display.room_number) ? b.contract_display.room_number : '';
            
            const firstChar = tenantName ? tenantName.charAt(0).toUpperCase() : '<i class="fa-solid fa-user"></i>';
            const displayName = tenantName || 'Khách vãng lai';
            const displayRoom = roomNumber || '--';

            let statusHtml = '';
            let btnPayHtml = '';
            
            if (b.status === 'paid') {
                statusHtml = `<span class="badge bg-success-subtle text-success border border-success-subtle px-3 py-1 rounded-pill"><i class="fa-solid fa-circle-check me-1"></i> Đã đóng</span>`;
            } else {
                statusHtml = `<span class="badge bg-warning-subtle text-warning border border-warning-subtle px-3 py-1 rounded-pill"><i class="fa-solid fa-clock me-1"></i> Chưa đóng đủ</span>`;
                btnPayHtml = `
                  <button class="btn action-btn bg-warning-subtle text-warning" onclick="openPayModal('${b.id}', ${b.total || 0})" title="Ghi nhận thanh toán">
                    <i class="fa-solid fa-money-bill-wave"></i>
                  </button>`;
            }

            // Xử lý UI hiển thị Nút Lịch sử thanh toán dưới số tiền "Đã thu"
            let historyBtnHtml = '';
            if (b.payment_history && b.payment_history.length > 0) {
                historyBtnHtml = `
                <div class="mt-1">
                  <button class="btn btn-sm btn-link text-decoration-none p-0 text-info fw-semibold" style="font-size: 0.75rem;" onclick="showPaymentHistory('${b.id}')">
                    <i class="fa-solid fa-clock-rotate-left me-1"></i>Xem lịch sử
                  </button>
                </div>`;
            }

            // Gắn data-attributes trực tiếp vào chuỗi tr
            return `
                <tr class="data-row" data-tenant-name="${tenantName}" data-room="${roomNumber}" data-month="${b.month || ''}" data-total="${b.total || 0}">
                    <td class="ps-4">
                      <div class="d-flex align-items-center">
                        <div class="avatar-circle bg-primary-subtle text-primary me-3 shadow-sm d-none d-md-flex" style="width:36px; height:36px; border-radius:10px; align-items:center; justify-content:center; font-weight:bold; font-size:0.95rem;">
                          ${firstChar}
                        </div>
                        <div>
                          <div class="fw-bold text-dark">${displayName}</div>
                          <div class="small text-muted mt-1">
                            <span class="badge bg-light text-dark border px-2 py-1">Phòng ${displayRoom}</span>
                          </div>
                        </div>
                      </div>
                    </td>
                    <td class="text-center" data-label="Kỳ thu">
                      <span class="text-primary fw-semibold"><i class="fa-regular fa-calendar-alt me-1"></i>${b.month}</span>
                    </td>
                    <td class="text-end" data-label="Đã thu">
                      <span class="fw-semibold text-success fs-6">${formatMoney(b.paid_amount || 0)}</span>
                      ${historyBtnHtml}
                    </td>
                    <td class="text-end" data-label="Còn nợ">
                      <span class="fw-bold text-danger fs-6">${formatMoney(b.total || 0)}</span>
                    </td>
                    <td class="text-center" data-label="Trạng thái">
                      ${statusHtml}
                    </td>
                    <td class="text-center pe-4" data-label="Thao tác">
                      <div class="d-flex justify-content-center gap-1">
                        <button class="btn action-btn bg-primary-subtle text-primary" onclick="showBill('${b.id}')" title="Xem chi tiết Hóa đơn">
                          <i class="fa-solid fa-eye"></i>
                        </button>
                        ${btnPayHtml}
                        <button class="btn action-btn bg-success-subtle text-success" onclick="captureInvoiceImage('${b.id}', this)" title="Lưu/Tải ảnh Hóa đơn">
                          <i class="fa-solid fa-download"></i>
                        </button>
                        <form action="/bills/${b.id}/delete" method="post" style="display:inline" onsubmit="return confirm('Bạn có chắc chắn muốn xóa hóa đơn này không? Hành động này không thể hoàn tác.');">
                          <input type="hidden" name="csrf_token" value="${csrfToken}">  
                          <button class="btn action-btn bg-danger-subtle text-danger" type="submit" title="Xóa Hóa đơn">
                            <i class="fa-solid fa-trash-can"></i>
                          </button>
                        </form>
                      </div>
                    </td>
                </tr>
            `;
        });

        // Gán 1 lần duy nhất để tối ưu reflow của trình duyệt
        tbody.innerHTML = htmlRows.join('');

        // Khởi động lại tìm kiếm/sắp xếp
        filterBills();
        sortBills();

    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger py-4"><i class="fa-solid fa-circle-exclamation me-2"></i>Lỗi tải dữ liệu hóa đơn</td></tr>';
        console.error("Lỗi loadBills:", e);
    }
}

// Hàm hiển thị Lịch sử thanh toán ra Modal
window.showPaymentHistory = function(billId) {
    // Tìm hóa đơn trong biến dữ liệu đã load
    const bill = window.currentBillsData.find(b => b.id === billId);
    if (!bill || !bill.payment_history) return;

    const tbody = document.getElementById('paymentHistoryBody');
    if (bill.payment_history.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted py-4">Chưa có giao dịch thanh toán nào</td></tr>';
    } else {
        // Sắp xếp lịch sử mới nhất lên đầu
        const historySorted = [...bill.payment_history].reverse();
        
        tbody.innerHTML = historySorted.map(ph => `
            <tr>
                <td class="ps-4 fw-medium text-dark">${ph.date_fmt || '--'}</td>
                <td class="text-end fw-bold text-success">${formatMoney(ph.amount)}</td>
                <td class="text-center pe-4"><span class="badge bg-light text-dark border px-2 py-1">${ph.method}</span></td>
            </tr>
        `).join('');
    }

    // Mở Modal
    const modalEl = document.getElementById('paymentHistoryModal');
    const modal = new bootstrap.Modal(modalEl);
    modal.show();
};

// 2. Xem Hóa Đơn (Đã tối ưu tốc độ hiển thị)
window.showBill = async function(billId) {
  const frame = document.getElementById('billViewFrame');
  const modalEl = document.getElementById('billViewModal');
  
  // 1. MỞ MODAL NGAY LẬP TỨC ĐỂ TẠO CẢM GIÁC MƯỢT MÀ
  const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
  modal.show();
  
  // 2. HIỂN THỊ ANIMATION LOADING BÊN TRONG IFRAME TRONG LÚC CHỜ SERVER
  frame.srcdoc = `
    <div style="display:flex; flex-direction:column; justify-content:center; align-items:center; height:90vh; font-family:'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color:#64748b;">
      <div style="width: 40px; height: 40px; border: 4px solid #e2e8f0; border-top: 4px solid #2563eb; border-radius: 50%; animation: spin 1s linear infinite;"></div>
      <div style="margin-top: 16px; font-weight: 500; font-size: 0.95rem;">Đang tải dữ liệu hóa đơn...</div>
      <style>@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style>
    </div>
  `;

  // 3. TIẾN HÀNH GỌI SERVER
  try {
    const resp = await fetch(`/invoice/print/${billId}`, { credentials: 'include' });
    const finalUrl = resp.url || '';
    const text = await resp.text();
    
    // Kiểm tra mất phiên đăng nhập
    if (finalUrl.includes('/login') || /Đăng nhập|Đăng nh\?p/.test(text)){
      try { new Notyf().error('Bạn cần đăng nhập để xem hóa đơn'); } catch(e){}
      window.location.href = '/login';
      return;
    }
    
    // 4. ĐỔ DỮ LIỆU THẬT VÀO SAU KHI TẢI XONG
    frame.srcdoc = text;
    
  } catch(e) { 
    console.error(e); 
    frame.srcdoc = `
      <div style="display:flex; justify-content:center; align-items:center; height:90vh; font-family:sans-serif; color:#ef4444; font-weight:bold;">
        <svg style="width:24px; height:24px; margin-right:8px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
        Không thể tải hóa đơn. Vui lòng thử lại!
      </div>`;
  }
};

// 3. Mở Modal Nhập Thanh Toán
window.openPayModal = function(billId, totalDue) {
  try {
    const form = document.getElementById('payBillForm');
    if (form) form.action = `/bills/${billId}/pay`;
    
    const amountInput = document.getElementById('pay_amount');
    if (amountInput) amountInput.value = totalDue || 0;
    
    // Tự động điền ngày hôm nay chuẩn múi giờ Việt Nam
    const dateInput = document.getElementById('payment_date');
    if (dateInput) {
        const today = new Date();
        const tzOffset = today.getTimezoneOffset() * 60000; 
        const localISOTime = (new Date(today - tzOffset)).toISOString().split('T')[0];
        dateInput.value = localISOTime;
    }
    
    const modalEl = document.getElementById('payBillModal');
    if (modalEl) {
      const modal = new bootstrap.Modal(modalEl);
      modal.show();
    }
  } catch (e) {
    console.error("Lỗi mở modal thanh toán:", e);
  }
};

// 4. Tải/In Ảnh Hóa Đơn
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

// 5. Bộ lọc & Tìm kiếm
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

// 6. Gắn Event Listeners
document.addEventListener('DOMContentLoaded', function(){
  const input = document.getElementById('billSearch'); if (input) input.addEventListener('input', filterBills);
  const s = document.getElementById('billSort'); if (s) s.addEventListener('change', sortBills);
  const timeButtons = document.querySelectorAll('#timeFilterPills button');
  const timeHiddenInput = document.getElementById('timeFilter');

  timeButtons.forEach(btn => {
      btn.addEventListener('click', function() {
          // Xóa class active cũ
          timeButtons.forEach(b => {
              b.classList.remove('bg-white', 'text-primary', 'shadow-sm', 'active-time');
              b.classList.add('text-muted', 'border-0');
          });
          // Thêm class active cho nút vừa bấm
          this.classList.remove('text-muted', 'border-0');
          this.classList.add('bg-white', 'text-primary', 'shadow-sm', 'active-time');
          
          // Cập nhật giá trị và load lại data
          timeHiddenInput.value = this.dataset.value;
          loadBills();
      });
  });
  
  // Gắn event khi thay đổi bộ lọc thời gian
  const timeFilterSelect = document.getElementById('timeFilter');
  if (timeFilterSelect) {
      timeFilterSelect.addEventListener('change', loadBills);
  }

  // Kích hoạt load dữ liệu
  const tbody = document.getElementById('billsTableBody');
  if (tbody && tbody.dataset.autoLoad === 'true') {
      loadBills();
  }

  const generateForm = document.getElementById('generateBillForm');
  if (generateForm) {
      generateForm.addEventListener('submit', async function(e) {
          e.preventDefault(); // Chặn submit mặc định
          
          const btn = this.querySelector('button[type="submit"]');
          const origText = btn.innerHTML;
          btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang kiểm tra...';
          btn.disabled = true;

          const contractId = this.contract_id.value;
          const month = this.month.value;

          try {
              const res = await fetch(`/bills/check-electric?contract_id=${contractId}&month=${month}`);
              if (!res.ok) throw new Error('Lỗi kiểm tra điện');
              
              const data = await res.json();
              
              if (data.has_data) {
                  // Đã có điện, submit form bình thường
                  this.submit();
              } else {
                  // Chưa có điện, mở modal
                  document.getElementById('modal_contract_id').value = contractId;
                  document.getElementById('modal_month').value = month;
                  document.getElementById('display_month').innerText = month;
                  document.getElementById('modal_old_index').value = data.old_index;
                  document.getElementById('modal_new_index').min = data.old_index; // Bắt buộc số mới >= số cũ
                  
                  const modal = new bootstrap.Modal(document.getElementById('inputElectricModal'));
                  modal.show();
                  btn.innerHTML = origText;
                  btn.disabled = false;
              }
          } catch (error) {
              console.error(error);
              try{ new Notyf().error('Không thể kiểm tra chỉ số điện'); }catch(err){};
              btn.innerHTML = origText;
              btn.disabled = false;
          }
      });
  }
});