// dashboard.js - extracted from dashboard.html inline script
(function(){
  const D = window.dashboardData || {};

  const labels6 = D.labels6 || [];
  const payments6 = D.payments6 || [];
  const labels12 = D.labels12 || [];
  const payments12 = D.payments12 || [];
  const labels30 = D.labels30 || [];
  const payments30 = D.payments30 || [];
  const labels_all = D.labels_all || [];
  const payments_all = D.payments_all || [];

  const ctx = document.getElementById('revenueChart')?.getContext('2d');
  let revenueChart = null;
  if (ctx){
    revenueChart = new Chart(ctx, {
      type: 'line',
      data: { labels: labels6, datasets: [{ label: 'Tiền đã nhận', data: payments6, borderColor: 'rgba(40,167,69,0.9)', backgroundColor: 'rgba(40,167,69,0.12)', tension: 0.3, fill: true }] },
      options: { responsive: true, maintainAspectRatio: false, plugins:{legend:{display:false}}, scales:{x:{title:{display:true,text:'Thời gian'}}} }
    });
  }

  function updateChart(range){
    if (!revenueChart) return;
    if (range === 'all'){
      revenueChart.data.labels = labels_all;
      revenueChart.data.datasets = [{label:'Tiền đã nhận', data: payments_all, borderColor:'rgba(40,167,69,0.9)', backgroundColor:'rgba(40,167,69,0.12)', tension:0.3, fill:true}];
      try{ document.getElementById('timeUnit').innerText = 'Đơn vị: Tháng'; }catch(e){}
    } else if (range === '30'){
      revenueChart.data.labels = labels30;
      revenueChart.data.datasets = [{label:'Tiền đã nhận', data: payments30, borderColor:'rgba(40,167,69,0.9)', backgroundColor:'rgba(40,167,69,0.12)', tension:0.3, fill:true}];
      try{ document.getElementById('timeUnit').innerText = 'Đơn vị: Ngày'; }catch(e){}
    } else if (range === '6'){
      revenueChart.data.labels = labels6;
      revenueChart.data.datasets = [{label:'Tiền đã nhận', data: payments6, borderColor:'rgba(40,167,69,0.9)', backgroundColor:'rgba(40,167,69,0.12)', tension:0.3, fill:true}];
      try{ document.getElementById('timeUnit').innerText = 'Đơn vị: Tháng'; }catch(e){}
    } else if (range === '12'){
      revenueChart.data.labels = labels12;
      revenueChart.data.datasets = [{label:'Tiền đã nhận', data: payments12, borderColor:'rgba(40,167,69,0.9)', backgroundColor:'rgba(40,167,69,0.12)', tension:0.3, fill:true}];
      try{ document.getElementById('timeUnit').innerText = 'Đơn vị: Tháng'; }catch(e){}
    }
    revenueChart.update();
  }

  // small doughnuts/pies
  try{
    const roomStatusCtx = document.getElementById('roomStatusChart')?.getContext('2d');
    if (roomStatusCtx){ new Chart(roomStatusCtx, { type: 'doughnut', data: { labels: ['Đang thuê', 'Trống'], datasets: [{ data: [D.occupied||0, D.available||0], backgroundColor: ['rgba(255,193,7,0.85)', 'rgba(25,135,84,0.8)'] }] }, options: {responsive:true} }); }

    const billStatusCtx = document.getElementById('billStatusChart')?.getContext('2d');
    if (billStatusCtx){ new Chart(billStatusCtx, { type: 'doughnut', data: { labels: ['Đã đóng', 'Chưa đóng'], datasets: [{ data: [D.paid||0, D.unpaid||0], backgroundColor: ['rgba(13,110,253,0.85)', 'rgba(220,53,69,0.8)'] }] }, options: {responsive:true} }); }

    const tenantStatusCtx = document.getElementById('tenantStatusChart')?.getContext('2d');
    if (tenantStatusCtx){ new Chart(tenantStatusCtx, { type: 'pie', data: { labels: ['Đang thuê', 'Đã kết thúc'], datasets: [{ data: [D.renting_tenants||0, D.ended_tenants||0], backgroundColor: ['rgba(255,193,7,0.85)', 'rgba(108,117,125,0.8)'] }] }, options: {responsive:true} }); }
  }catch(e){console.error(e)}

  // Electric chart handling
  const E = D; // reuse
  const electricCtx = document.getElementById('electricHistoryChart')?.getContext('2d');
  let electricChart = null;
  if (electricCtx){
    electricChart = new Chart(electricCtx, { type: 'line', data: { labels: E.electric_labels_6||[], datasets: [{ label: 'kWh', data: E.electric_series_6||[], borderColor: 'rgba(255,159,64,0.9)', backgroundColor: 'rgba(255,159,64,0.12)', tension:0.3, fill:true }] }, options: { responsive:true, maintainAspectRatio: false, scales: { y:{ beginAtZero:true } }, plugins:{legend:{display:false}} } });
  }

  function updateElectricChart(range){
    if (!electricChart) return;
    if (range === 'all'){
      electricChart.data.labels = E.labels_all || [];
      electricChart.data.datasets = [{label:'kWh', data: E.electricSeriesAll || [], borderColor:'rgba(255,159,64,0.9)', backgroundColor:'rgba(255,159,64,0.12)', tension:0.3, fill:true}];
      try{ document.getElementById('electricTimeUnit').innerText = 'Đơn vị: Tháng'; }catch(e){}
    } else if (range === '30'){
      electricChart.data.labels = E.electric_labels_30 || [];
      electricChart.data.datasets = [{label:'kWh', data: E.electric_series_30 || [], borderColor:'rgba(255,159,64,0.9)', backgroundColor:'rgba(255,159,64,0.12)', tension:0.3, fill:true}];
      try{ document.getElementById('electricTimeUnit').innerText = 'Đơn vị: Ngày'; }catch(e){}
    } else if (range === '6'){
      electricChart.data.labels = E.electric_labels_6 || [];
      electricChart.data.datasets = [{label:'kWh', data: E.electric_series_6 || [], borderColor:'rgba(255,159,64,0.9)', backgroundColor:'rgba(255,159,64,0.12)', tension:0.3, fill:true}];
      try{ document.getElementById('electricTimeUnit').innerText = 'Đơn vị: Tháng'; }catch(e){}
    } else if (range === '12'){
      electricChart.data.labels = E.electric_labels_12 || [];
      electricChart.data.datasets = [{label:'kWh', data: E.electric_series_12 || [], borderColor:'rgba(255,159,64,0.9)', backgroundColor:'rgba(255,159,64,0.12)', tension:0.3, fill:true}];
      try{ document.getElementById('electricTimeUnit').innerText = 'Đơn vị: Tháng'; }catch(e){}
    }
    electricChart.update();
  }

  document.getElementById('electricRangeSelect')?.addEventListener('change', function(e){ updateElectricChart(e.target.value); });

  // Top panel update
  function renderTopPanelHtml(title, items){
    const container = document.getElementById('electricTopList'); if (!container) return;
    let html = '';
    if (!items || !items.length){ html = '<div>Chưa có dữ liệu ghi nhận</div>'; }
    else { html = '<ol class="mb-0 small">' + items.map(x=>`<li class="mb-1">${x.label}: <strong>${x.usage}</strong> kWh</li>`).join('') + '</ol>'; }
    container.innerHTML = `<div class="fw-semibold mb-1">${title}</div>` + html;
  }

  async function updateElectricTopPanelForLabel(range, label){
    const container = document.getElementById('electricTopList'); if (!container) return; container.innerHTML = 'Đang tải...';
    try{
      if (range === 'all'){
        const items = (E.top_room_labels||[]).map((lab, i)=>({label: lab, usage: (E.top_room_usage||[])[i]||0}));
        renderTopPanelHtml('Top tất cả thời gian', items); return;
      }
      if (range === '12'){
        const year = String(label).match(/^(\d{4})/)?.[1] || new Date().getFullYear();
        const res = await fetch(`/electric/dashboard/top-electric-year/${year}`);
        if (!res.ok) { container.innerHTML = 'Chưa có dữ liệu ghi nhận'; return; }
        const data = await res.json();
        const items = (data.top_months||[]).map(x=>({label:x.month, usage:x.usage}));
        renderTopPanelHtml(`Top tháng trong ${year}`, items); return;
      }
      const month = label;
      const res = await fetch(`/electric/dashboard/top-electric/${month}`);
      if (!res.ok) { container.innerHTML = 'Chưa có dữ liệu ghi nhận'; return; }
      const data = await res.json();
      const items = (data.top_rooms||[]).map(x=>({label:`Phòng ${x.room_number}`, usage:x.usage}));
      renderTopPanelHtml(`Top phòng ${month}`, items);
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

  // Churn chart
  const churnCtx = document.getElementById('churnChart')?.getContext('2d');
  let churnChart = null;
  if (churnCtx){
    churnChart = new Chart(churnCtx, { type: 'bar', data: { labels: labels6, datasets: [ { label: 'Thuê mới', data: D.tenant_started_6||[], backgroundColor: 'rgba(13,110,253,0.85)' }, { label: 'Thoát', data: D.tenant_ended_6||[], backgroundColor: 'rgba(220,53,69,0.85)' } ] }, options: { responsive:true, maintainAspectRatio: false, plugins:{legend:{position:'top'}}, scales:{ x:{ stacked:false }, y:{ beginAtZero:true } } } });
  }

  function updateChurnChart(range){
    if (!churnChart) return;
    if (range === 'all'){
      churnChart.data.labels = labels_all;
      churnChart.data.datasets = [{label:'Thuê mới', data: D.tenantStartedAll||[], backgroundColor:'rgba(13,110,253,0.85)'},{label:'Thoát', data: D.tenantEndedAll||[], backgroundColor:'rgba(220,53,69,0.85)'}];
      try{ document.getElementById('churnTimeUnit').innerText = 'Đơn vị: Tháng'; }catch(e){}
    } else if (range === '30'){
      churnChart.data.labels = D.tenant_labels_30 || [];
      churnChart.data.datasets = [{label:'Thuê mới', data: D.tenant_started_30||[], backgroundColor:'rgba(13,110,253,0.85)'},{label:'Thoát', data: D.tenant_ended_30||[], backgroundColor:'rgba(220,53,69,0.85)'}];
      try{ document.getElementById('churnTimeUnit').innerText = 'Đơn vị: Ngày'; }catch(e){}
    } else if (range === '6'){
      churnChart.data.labels = labels6;
      churnChart.data.datasets = [{label:'Thuê mới', data: D.tenant_started_6||[], backgroundColor:'rgba(13,110,253,0.85)'},{label:'Thoát', data: D.tenant_ended_6||[], backgroundColor:'rgba(220,53,69,0.85)'}];
      try{ document.getElementById('churnTimeUnit').innerText = 'Đơn vị: Tháng'; }catch(e){}
    } else if (range === '12'){
      churnChart.data.labels = labels12;
      churnChart.data.datasets = [{label:'Thuê mới', data: D.tenant_started_12||[], backgroundColor:'rgba(13,110,253,0.85)'},{label:'Thoát', data: D.tenant_ended_12||[], backgroundColor:'rgba(220,53,69,0.85)'}];
      try{ document.getElementById('churnTimeUnit').innerText = 'Đơn vị: Tháng'; }catch(e){}
    }
    churnChart.update();
  }

  // wire selectors
  const mainRange = document.getElementById('rangeSelect');
  const churnRange = document.getElementById('churnRangeSelect');
  if (mainRange){ mainRange.addEventListener('change', function(e){ updateChart(e.target.value); }); }
  if (churnRange){ churnRange.addEventListener('change', function(e){ updateChurnChart(e.target.value); }); }

  try{
    const initialRange = document.getElementById('rangeSelect')?.value || '6';
    updateChart(initialRange);
    updateChurnChart(initialRange);
    updateElectricChart(document.getElementById('electricRangeSelect')?.value || '6');

    function adjustChartsResponsive(){
      const w = window.innerWidth || document.documentElement.clientWidth || 1024;
      const small = w < 576;
      const tickSize = small ? 10 : 12;
      const applyToChart = (chart)=>{
        try{ if (!chart) return; if (chart.options && chart.options.scales){ Object.keys(chart.options.scales).forEach(k=>{ const s = chart.options.scales[k]; s.ticks = s.ticks || {}; s.ticks.font = s.ticks.font || {}; s.ticks.font.size = tickSize; }); } if (chart.options && chart.options.plugins && chart.options.plugins.legend && chart.options.plugins.legend.labels){ chart.options.plugins.legend.labels.font = chart.options.plugins.legend.labels.font || {}; chart.options.plugins.legend.labels.font.size = tickSize; } chart.resize(); chart.update(); }catch(e){console.error(e)} };
      applyToChart(revenueChart);
      applyToChart(electricChart);
      applyToChart(churnChart);
    }
    adjustChartsResponsive();
    let lastWindowWidth = window.innerWidth;
    window.addEventListener('resize', function(){ if (window.innerWidth !== lastWindowWidth) { lastWindowWidth = window.innerWidth; setTimeout(adjustChartsResponsive, 120); } });
  }catch(e){ console.error(e); }

})();
