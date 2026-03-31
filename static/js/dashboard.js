// dashboard.js - extracted from dashboard.html inline script
(function(){
  document.addEventListener('DOMContentLoaded', async function() {
    try {
        const response = await fetch('/dashboard/_data');
        if (!response.ok) throw new Error("Không thể tải dữ liệu Dashboard");
        
        const D = await response.json();
        
        // Lưu vào biến global để các hàm onchange select dùng lại
        window.dashboardData = D; 

        // Hàm format tiền tệ
        const formatMoney = (amount) => {
            return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);
        };

        // Cập nhật các chỉ số Metrics trên giao diện
        document.getElementById('val-total-rooms').innerText = D.total_rooms || 0;
        document.getElementById('val-occupied').innerText = D.occupied || 0;
        document.getElementById('val-unpaid').innerText = D.unpaid || 0;
        document.getElementById('val-paid-month').innerText = formatMoney(D.paid_amount_current_month || 0);
        document.getElementById('val-room-price').innerText = formatMoney(D.room_price_avg || 0);
        document.getElementById('val-price-kwh').innerText = formatMoney(D.price_per_kwh || 0);
        document.getElementById('val-water-fee').innerText = formatMoney(D.water_fee || 0);
        document.getElementById('val-total-accounts').innerText = D.total_accounts || 0;

        // TẮT HIỆU ỨNG LOADING CỦA BIỂU ĐỒ TRƯỚC KHI VẼ
        document.querySelectorAll('.chart-loading').forEach(el => {
            el.classList.remove('d-flex'); // Gỡ bỏ thuộc tính cản trở
            el.classList.add('d-none');    // Ép ẩn bằng class của Bootstrap
        });

        // KHỞI TẠO BIỂU ĐỒ
        initCharts(D);

    } catch (error) {
        console.error("Lỗi khi tải Dashboard:", error);
        // Đổi loading thành báo lỗi nếu API sập
        document.querySelectorAll('.chart-loading').forEach(el => {
            el.innerHTML = '<span class="text-danger small"><i class="fa-solid fa-triangle-exclamation me-1"></i>Lỗi tải dữ liệu</span>';
        });
    }
  });

  function initCharts(D) {
      // Mã màu chuẩn Design System
      const colorPrimary = 'rgba(59, 130, 246, 0.85)';
      const colorPrimaryLight = 'rgba(59, 130, 246, 0.15)';
      const colorSuccess = 'rgba(16, 185, 129, 0.85)';
      const colorSuccessLight = 'rgba(16, 185, 129, 0.15)';
      const colorDanger = 'rgba(239, 68, 68, 0.85)';
      const colorWarning = 'rgba(245, 158, 11, 0.85)';
      const colorMuted = 'rgba(148, 163, 184, 0.85)';

      Chart.defaults.font.family = "'Inter', sans-serif";
      Chart.defaults.color = '#64748b';
      Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 23, 42, 0.9)';
      Chart.defaults.plugins.tooltip.padding = 10;
      Chart.defaults.plugins.tooltip.cornerRadius = 8;
      Chart.defaults.plugins.tooltip.titleFont = { size: 13, weight: 'bold' };

      // 1. REVENUE CHART
      const ctx = document.getElementById('revenueChart')?.getContext('2d');
      let revenueChart = null;
      if (ctx){
        revenueChart = new Chart(ctx, {
          type: 'line',
          data: { labels: D.labels6 || [], datasets: [{ label: 'Tiền đã nhận', data: D.payments6 || [], borderColor: colorSuccess, backgroundColor: colorSuccessLight, tension: 0.4, fill: true, pointBackgroundColor: '#fff', pointBorderColor: colorSuccess, pointRadius: 4 }] },
          options: { responsive: true, maintainAspectRatio: false, plugins:{legend:{display:false}}, scales:{x:{grid:{display:false}}, y:{border:{dash:[4,4]}, grid:{color:'#f1f5f9'}}} }
        });
      }

      function updateChart(range){
        if (!revenueChart) return;
        if (range === 'all'){
          revenueChart.data.labels = D.labels_all || [];
          revenueChart.data.datasets[0].data = D.payments_all || [];
          try{ document.getElementById('timeUnit').innerText = 'Đơn vị: Tháng'; }catch(e){}
        } else if (range === '30'){
          revenueChart.data.labels = D.labels30 || [];
          revenueChart.data.datasets[0].data = D.payments30 || [];
          try{ document.getElementById('timeUnit').innerText = 'Đơn vị: Ngày'; }catch(e){}
        } else if (range === '6'){
          revenueChart.data.labels = D.labels6 || [];
          revenueChart.data.datasets[0].data = D.payments6 || [];
          try{ document.getElementById('timeUnit').innerText = 'Đơn vị: Tháng'; }catch(e){}
        } else if (range === '12'){
          revenueChart.data.labels = D.labels12 || [];
          revenueChart.data.datasets[0].data = D.payments12 || [];
          try{ document.getElementById('timeUnit').innerText = 'Đơn vị: Tháng'; }catch(e){}
        }
        revenueChart.update();
      }

      // 2. PIE CHARTS
      try{
        const roomStatusCtx = document.getElementById('roomStatusChart')?.getContext('2d');
        if (roomStatusCtx){ new Chart(roomStatusCtx, { type: 'doughnut', data: { labels: ['Đang thuê', 'Trống'], datasets: [{ data: [D.occupied||0, D.available||0], backgroundColor: [colorPrimary, colorMuted], borderWidth: 0 }] }, options: {responsive:true, maintainAspectRatio: false, cutout: '70%', plugins:{legend:{position:'bottom'}}} }); }

        const billStatusCtx = document.getElementById('billStatusChart')?.getContext('2d');
        if (billStatusCtx){ new Chart(billStatusCtx, { type: 'doughnut', data: { labels: ['Đã đóng', 'Chưa đóng'], datasets: [{ data: [D.paid||0, D.unpaid||0], backgroundColor: [colorSuccess, colorDanger], borderWidth: 0 }] }, options: {responsive:true, maintainAspectRatio: false, cutout: '70%', plugins:{legend:{position:'bottom'}}} }); }

        const tenantStatusCtx = document.getElementById('tenantStatusChart')?.getContext('2d');
        if (tenantStatusCtx){ new Chart(tenantStatusCtx, { type: 'doughnut', data: { labels: ['Đang thuê', 'Đã kết thúc'], datasets: [{ data: [D.renting_tenants||0, D.ended_tenants||0], backgroundColor: [colorPrimary, colorMuted], borderWidth: 0 }] }, options: {responsive:true, maintainAspectRatio: false, cutout: '70%', plugins:{legend:{position:'bottom'}}} }); }
      }catch(e){console.error(e)}

      // 3. ELECTRIC CHART
      const electricCtx = document.getElementById('electricHistoryChart')?.getContext('2d');
      let electricChart = null;
      if (electricCtx){
        electricChart = new Chart(electricCtx, { type: 'bar', data: { labels: D.electric_labels_6||[], datasets: [{ label: 'Tổng mức tiêu thụ (kWh)', data: D.electric_series_6||[], backgroundColor: colorWarning, borderRadius: 6 }] }, options: { responsive:true, maintainAspectRatio: false, scales: { x:{grid:{display:false}}, y:{ beginAtZero:true, grid:{color:'#f1f5f9'} } }, plugins:{legend:{display:false}} } });
      }

      function updateElectricChart(range){
        if (!electricChart) return;
        if (range === 'all'){
          electricChart.data.labels = D.electric_labels_all || D.labels_all || [];
          electricChart.data.datasets[0].data = D.electric_series_all || [];
          try{ document.getElementById('electricTimeUnit').innerText = 'Đơn vị: Tháng'; }catch(e){}
        } else if (range === '30'){
          electricChart.data.labels = D.electric_labels_30 || [];
          electricChart.data.datasets[0].data = D.electric_series_30 || [];
          try{ document.getElementById('electricTimeUnit').innerText = 'Đơn vị: Ngày'; }catch(e){}
        } else if (range === '6'){
          electricChart.data.labels = D.electric_labels_6 || [];
          electricChart.data.datasets[0].data = D.electric_series_6 || [];
          try{ document.getElementById('electricTimeUnit').innerText = 'Đơn vị: Tháng'; }catch(e){}
        } else if (range === '12'){
          electricChart.data.labels = D.electric_labels_12 || [];
          electricChart.data.datasets[0].data = D.electric_series_12 || [];
          try{ document.getElementById('electricTimeUnit').innerText = 'Đơn vị: Tháng'; }catch(e){}
        }
        electricChart.update();
      }

      document.getElementById('electricRangeSelect')?.addEventListener('change', function(e){ updateElectricChart(e.target.value); });

      // 4. ELECTRIC TOP PANEL
      function renderTopPanelHtml(title, items){
        const container = document.getElementById('electricTopList'); if (!container) return;
        let html = '';
        if (!items || !items.length){ html = '<div class="text-muted fst-italic py-3 text-center">Chưa có dữ liệu</div>'; }
        else { 
            html = items.map((x, i)=>`
                <div class="d-flex justify-content-between align-items-center mb-2 pb-2 border-bottom">
                    <div class="d-flex align-items-center">
                        <span class="badge bg-secondary-subtle text-secondary me-2 rounded-circle" style="width:24px;height:24px;display:flex;align-items:center;justify-content:center;">${i+1}</span>
                        <span class="fw-semibold text-dark">${x.label}</span>
                    </div>
                    <strong class="text-warning">${x.usage} <small class="text-muted fw-normal">kWh</small></strong>
                </div>
            `).join(''); 
        }
        container.innerHTML = `<div class="fw-bold text-dark mb-3">${title}</div>` + html;
      }

      async function updateElectricTopPanelForLabel(range, label){
        const container = document.getElementById('electricTopList'); if (!container) return; 
        container.innerHTML = '<div class="text-center py-3"><span class="spinner-border spinner-border-sm text-primary"></span></div>';
        try{
          if (range === 'all'){
            const items = (D.top_room_labels||[]).map((lab, i)=>({label: lab, usage: (D.top_room_usage||[])[i]||0}));
            renderTopPanelHtml('Top tất cả thời gian', items); return;
          }
          if (range === '12'){
            const year = String(label).match(/^(\d{4})/)?.[1] || new Date().getFullYear();
            const res = await fetch(`/electric/dashboard/top-electric-year/${year}`);
            if (!res.ok) { container.innerHTML = 'Chưa có dữ liệu'; return; }
            const data = await res.json();
            const items = (data.top_months||[]).map(x=>({label:x.month, usage:x.usage}));
            renderTopPanelHtml(`Tháng dùng nhiều năm ${year}`, items); return;
          }
          const month = label;
          const res = await fetch(`/electric/dashboard/top-electric/${month}`);
          if (!res.ok) { container.innerHTML = 'Chưa có dữ liệu'; return; }
          const data = await res.json();
          const items = (data.top_rooms||[]).map(x=>({label:`Phòng ${x.room_number}`, usage:x.usage}));
          renderTopPanelHtml(`Top phòng tháng ${month}`, items);
        }catch(e){ console.error(e); container.innerHTML = 'Lỗi hiển thị dữ liệu'; }
      }

      try{
        const electricCanvas = document.getElementById('electricHistoryChart');
        if (electricCanvas && electricChart){
          electricCanvas.addEventListener('click', async function(evt){
            try{
              const pts = electricChart.getElementsAtEventForMode(evt,'nearest',{intersect:true},true);
              if (!pts || !pts.length) return;
              const idx = pts[0].index;
              const label = electricChart.data.labels[idx];
              const range = document.getElementById('electricRangeSelect').value;
              try{ await updateElectricTopPanelForLabel(range, label); }catch(e){}
            }catch(e){console.error(e)}
          });
        }
      }catch(e){console.error(e)}

      // 5. CHURN CHART
      const churnCtx = document.getElementById('churnChart')?.getContext('2d');
      let churnChart = null;
      if (churnCtx){
        churnChart = new Chart(churnCtx, { type: 'bar', data: { labels: D.labels6||[], datasets: [ { label: 'Thuê mới', data: D.tenant_started_6||[], backgroundColor: colorPrimary, borderRadius: 4 }, { label: 'Trả phòng', data: D.tenant_ended_6||[], backgroundColor: colorDanger, borderRadius: 4 } ] }, options: { responsive:true, maintainAspectRatio: false, plugins:{legend:{position:'top'}}, scales:{ x:{ stacked:false, grid:{display:false} }, y:{ beginAtZero:true, grid:{color:'#f1f5f9'} } } } });
      }

      function updateChurnChart(range){
        if (!churnChart) return;
        if (range === 'all'){
          churnChart.data.labels = D.labels_all || [];
          churnChart.data.datasets[0].data = D.tenant_started_all || [];
          churnChart.data.datasets[1].data = D.tenant_ended_all || [];
          try{ document.getElementById('churnTimeUnit').innerText = 'Đơn vị: Tháng'; }catch(e){}
        } else if (range === '30'){
          churnChart.data.labels = D.tenant_labels_30 || [];
          churnChart.data.datasets[0].data = D.tenant_started_30 || [];
          churnChart.data.datasets[1].data = D.tenant_ended_30 || [];
          try{ document.getElementById('churnTimeUnit').innerText = 'Đơn vị: Ngày'; }catch(e){}
        } else if (range === '6'){
          churnChart.data.labels = D.labels6 || [];
          churnChart.data.datasets[0].data = D.tenant_started_6 || [];
          churnChart.data.datasets[1].data = D.tenant_ended_6 || [];
          try{ document.getElementById('churnTimeUnit').innerText = 'Đơn vị: Tháng'; }catch(e){}
        } else if (range === '12'){
          churnChart.data.labels = D.labels12 || [];
          churnChart.data.datasets[0].data = D.tenant_started_12 || [];
          churnChart.data.datasets[1].data = D.tenant_ended_12 || [];
          try{ document.getElementById('churnTimeUnit').innerText = 'Đơn vị: Tháng'; }catch(e){}
        }
        churnChart.update();
      }
      
      // Events
      const mainRange = document.getElementById('rangeSelect');
      const churnRange = document.getElementById('churnRangeSelect');
      if (mainRange){ mainRange.addEventListener('change', function(e){ updateChart(e.target.value); }); }
      if (churnRange){ churnRange.addEventListener('change', function(e){ updateChurnChart(e.target.value); }); }

      try{
        const initialRange = document.getElementById('rangeSelect')?.value || '6';
        updateChart(initialRange);
        updateChurnChart(initialRange);
        updateElectricChart(document.getElementById('electricRangeSelect')?.value || '6');
        
        if(D.electric_labels_6 && D.electric_labels_6.length > 0) {
          updateElectricTopPanelForLabel('6', D.electric_labels_6[D.electric_labels_6.length - 1]);
        }
      }catch(e){ console.error(e); }
  }
})();