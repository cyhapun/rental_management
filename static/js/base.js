// base.js - common utilities for the app
(function(){
  // flash notification handler using Notyf
  window.addEventListener('load', function () {
    try {
      const el = document.getElementById('flash-data');
      const isMobileSmall = (window.innerWidth <= 576);
      const notyfPos = isMobileSmall ? { x: 'center', y: 'top' } : { x: 'right', y: 'top' };
      const notyfDur = isMobileSmall ? 1800 : 2400;
      const notyf = new Notyf({
        duration: notyfDur,
        position: notyfPos,
        ripple: true,
        dismissible: true,
        types: [
          { type: 'success', background: 'linear-gradient(90deg,#10b981,#059669)', icon: { className: 'fa-solid fa-check-circle', tagName: 'i' } },
          { type: 'warning', background: 'linear-gradient(90deg,#f59e0b,#d97706)', icon: { className: 'fa-solid fa-triangle-exclamation', tagName: 'i' } },
          { type: 'error', background: 'linear-gradient(90deg,#ef4444,#dc2626)', icon: { className: 'fa-solid fa-times-circle', tagName: 'i' } }
        ]
      });
      if (!el) return;
      const msg = el.dataset.flash || '';
      const level = (el.dataset.level || 'success').toLowerCase();
      if (!msg) return;
      if (level === 'danger' || level === 'error') notyf.open({ type: 'error', message: msg });
      else if (level === 'warning') notyf.open({ type: 'warning', message: msg });
      else notyf.open({ type: 'success', message: msg });
      try {
        const u = new URL(window.location);
        u.searchParams.delete('flash');
        u.searchParams.delete('level');
        window.history.replaceState({}, document.title, u.pathname + u.search + u.hash);
      } catch (e) {}
    } catch (e) { console.error(e) }
  });

  // Toggle active/inactive classes for list collapse buttons
  (function(){
    try{
      document.addEventListener('DOMContentLoaded', function(){
        const buttons = Array.from(document.querySelectorAll('button[data-bs-toggle="collapse"][data-bs-target]'));
        buttons.forEach(btn=>{
          const target = document.querySelector(btn.getAttribute('data-bs-target'));
          if (!target || !target.classList.contains('list-collapse')) return;
          const setActive = (isActive)=>{
            btn.classList.toggle('btn-list-active', isActive);
            btn.classList.toggle('btn-list-inactive', !isActive);
          };
          setActive(target.classList.contains('show'));
          target.addEventListener('shown.bs.collapse', ()=> setActive(true));
          target.addEventListener('hidden.bs.collapse', ()=> setActive(false));
        });
      });
    }catch(e){console.error(e)}
  })();

  // Print element as image helper
  async function printElementAsImage(selector, title) {
    try {
      const el = document.querySelector(selector);
      if (!el) return alert('Không tìm thấy phần tử để in: ' + selector);
      const sourceContainer = el.closest('.table-responsive') || el;
      const cloneWrapper = document.createElement('div');
      cloneWrapper.style.position = 'absolute';
      cloneWrapper.style.left = '-9999px';
      cloneWrapper.style.top = '0';
      cloneWrapper.style.overflow = 'visible';
      cloneWrapper.style.background = '#ffffff';
      cloneWrapper.style.padding = '12px';
      const clone = sourceContainer.cloneNode(true);
      const tbl = clone.querySelector('table') || clone;
      if (tbl && tbl.querySelector) {
        const thead = tbl.querySelector('thead');
        let actionIndex = -1;
        if (thead) {
          const ths = Array.from(thead.querySelectorAll('th'));
          ths.forEach((th, idx) => {
            const txt = (th.innerText || th.textContent || '').trim().toLowerCase();
            if (txt.includes('thao tác') || txt.includes('thao_tac') || txt.includes('thao-tac')) actionIndex = idx;
          });
        }
        if (actionIndex === -1) {
          try{ const lastTh = thead && thead.querySelector('th:last-child'); if (lastTh) actionIndex = Array.from(thead.querySelectorAll('th')).length - 1; }catch(e){}
        }
        if (actionIndex > -1) {
          try{ thead.querySelectorAll('th')[actionIndex].remove(); }catch(e){}
          const rows = tbl.querySelectorAll('tbody tr');
          rows.forEach(r => { const cells = r.querySelectorAll('td'); if (cells && cells.length > actionIndex) { cells[actionIndex].remove(); } });
        }
      }
      clone.style.width = 'auto';
      const tables = clone.querySelectorAll('table');
      tables.forEach(t => { t.style.width = 'auto'; t.style.tableLayout = 'auto'; t.style.maxWidth = 'none'; t.style.overflow = 'visible'; });
      cloneWrapper.appendChild(clone);
      document.body.appendChild(cloneWrapper);
      const scale = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
      const canvas = await html2canvas(cloneWrapper, { scale: scale, useCORS: true, backgroundColor: '#ffffff', scrollY: 0, allowTaint: true });
      if (!canvas) { cloneWrapper.remove(); return alert('Không thể tạo ảnh từ phần tử'); }
      cloneWrapper.remove();
      canvas.toBlob(function(blob){
        try{
          const ts = new Date();
          const pad = (n)=>String(n).padStart(2,'0');
          function normalizeFilename(s){ if (!s) return 'capture'; try{ return String(s).normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-zA-Z0-9\-_]/g,'_').toLowerCase(); }catch(e){ return String(s).replace(/[^a-zA-Z0-9\-_]/g,'_'); } }
          const fname = normalizeFilename(title) + '-' + ts.getFullYear() + pad(ts.getMonth()+1) + pad(ts.getDate()) + '-' + pad(ts.getHours()) + pad(ts.getMinutes()) + pad(ts.getSeconds()) + '.png';
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a'); a.href = url; a.download = fname; document.body.appendChild(a); a.click(); a.remove(); setTimeout(()=>URL.revokeObjectURL(url), 1000);
          try{ new Notyf({position: (window.innerWidth<=576?{x:'center',y:'top'}:{x:'right',y:'top'})}).success('Đã lưu ảnh: ' + fname); }catch(e){}
        }catch(e){ console.error('download error', e); alert('Lỗi khi lưu ảnh: ' + (e && e.message)); }
      }, 'image/png');
    } catch (e) { console.error(e); alert('Lỗi khi tạo ảnh: ' + (e && e.message)); }
  }

  // Attach print button handlers
  document.addEventListener('DOMContentLoaded', function(){
    try{
      document.querySelectorAll('[data-print-target]').forEach(btn=>{
        btn.addEventListener('click', function(e){
          const target = btn.getAttribute('data-print-target');
          const title = btn.getAttribute('data-print-title') || '';
          printElementAsImage(target, title);
        });
      });
    }catch(e){console.error('print binding error', e)}
  });

})();
