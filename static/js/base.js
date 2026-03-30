// base.js - common utilities for the app
(function(){
  // 1. Flash notification handler using Notyf
  window.addEventListener('load', function () {
    try {
      const el = document.getElementById('flash-data');
      if (!el) return;
      
      const isMobileSmall = (window.innerWidth <= 576);
      const notyfPos = isMobileSmall ? { x: 'center', y: 'top' } : { x: 'right', y: 'top' };
      const notyfDur = isMobileSmall ? 2500 : 3000;
      
      const notyf = new Notyf({
        duration: notyfDur,
        position: notyfPos,
        ripple: true,
        dismissible: true,
        types: [
          { type: 'success', background: '#10b981', icon: { className: 'fa-solid fa-check-circle', tagName: 'i', color: '#fff' } },
          { type: 'warning', background: '#f59e0b', icon: { className: 'fa-solid fa-triangle-exclamation', tagName: 'i', color: '#fff' } },
          { type: 'error', background: '#ef4444', icon: { className: 'fa-solid fa-times-circle', tagName: 'i', color: '#fff' } }
        ]
      });

      const msg = el.dataset.flash || '';
      const level = (el.dataset.level || 'success').toLowerCase();
      
      if (msg) {
        if (level === 'danger' || level === 'error') notyf.error(msg);
        else if (level === 'warning') notyf.open({ type: 'warning', message: msg });
        else notyf.success(msg);
      }

      // Clear params from URL
      try {
        const u = new URL(window.location);
        u.searchParams.delete('flash');
        u.searchParams.delete('level');
        window.history.replaceState({}, document.title, u.pathname + u.search + u.hash);
      } catch (e) {}
    } catch (e) { console.error("Notyf error:", e) }
  });

  // 2. Tự động đóng Offcanvas khi click link trên Mobile App Grid
  document.addEventListener('DOMContentLoaded', function() {
    const mobileLinks = document.querySelectorAll('.mobile-nav-item');
    const offcanvasEl = document.getElementById('offcanvasNav');
    
    if (offcanvasEl) {
        mobileLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                // Hiệu ứng scale mượt mà khi tap (bấm)
                this.style.transform = "scale(0.92)";
                setTimeout(() => this.style.transform = "", 200);

                // Đóng menu nếu trên mobile
                if (window.innerWidth < 768) {
                    const openedCanvas = bootstrap.Offcanvas.getInstance(offcanvasEl) || new bootstrap.Offcanvas(offcanvasEl);
                    setTimeout(() => openedCanvas.hide(), 150);
                }
            });
        });
    }

    // Xử lý collapse cho các list (Hỗ trợ nút Show/Hide)
    const collapseButtons = Array.from(document.querySelectorAll('button[data-bs-toggle="collapse"][data-bs-target]'));
    collapseButtons.forEach(btn => {
      const target = document.querySelector(btn.getAttribute('data-bs-target'));
      if (!target || !target.classList.contains('list-collapse')) return;
      
      const setActive = (isActive) => {
        btn.classList.toggle('btn-list-active', isActive);
        btn.classList.toggle('btn-list-inactive', !isActive);
      };
      
      setActive(target.classList.contains('show'));
      target.addEventListener('shown.bs.collapse', () => setActive(true));
      target.addEventListener('hidden.bs.collapse', () => setActive(false));
    });
  });

  // 3. Print element as image helper (Giữ nguyên logic của bạn)
  window.printElementAsImage = async function(selector, title) {
    try {
      const el = document.querySelector(selector);
      if (!el) return alert('Không tìm thấy phần tử để in: ' + selector);
      
      const sourceContainer = el.closest('.table-responsive') || el;
      const cloneWrapper = document.createElement('div');
      cloneWrapper.style.position = 'absolute';
      cloneWrapper.style.left = '-9999px';
      cloneWrapper.style.background = '#ffffff';
      cloneWrapper.style.padding = '20px';
      
      const clone = sourceContainer.cloneNode(true);
      const tbl = clone.querySelector('table') || clone;
      
      // Remove action column
      if (tbl && tbl.querySelector) {
        const thead = tbl.querySelector('thead');
        let actionIndex = -1;
        if (thead) {
          Array.from(thead.querySelectorAll('th')).forEach((th, idx) => {
            const txt = (th.innerText || th.textContent || '').trim().toLowerCase();
            if (txt.includes('thao tác') || txt.includes('thao_tac')) actionIndex = idx;
          });
        }
        if (actionIndex > -1) {
          try { thead.querySelectorAll('th')[actionIndex].remove(); } catch(e){}
          tbl.querySelectorAll('tbody tr').forEach(r => { 
            const cells = r.querySelectorAll('td'); 
            if (cells.length > actionIndex) cells[actionIndex].remove(); 
          });
        }
      }
      
      cloneWrapper.appendChild(clone);
      document.body.appendChild(cloneWrapper);
      
      const canvas = await html2canvas(cloneWrapper, { scale: 2, backgroundColor: '#ffffff', scrollY: 0 });
      cloneWrapper.remove();
      
      canvas.toBlob(function(blob){
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${title || 'export'}_${new Date().getTime()}.png`;
        a.click();
        URL.revokeObjectURL(url);
      }, 'image/png');
    } catch (e) {
      console.error(e); 
      alert('Lỗi khi tạo ảnh!');
    }
  }

  // Attach print button handlers
  document.addEventListener('DOMContentLoaded', function(){
    document.querySelectorAll('[data-print-target]').forEach(btn => {
      btn.addEventListener('click', function(){
        printElementAsImage(btn.getAttribute('data-print-target'), btn.getAttribute('data-print-title'));
      });
    });
  });

})();