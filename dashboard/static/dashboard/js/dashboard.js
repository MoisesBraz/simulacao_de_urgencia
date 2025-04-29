const API = {
  filas:   '/api/filas/',
  stats:   '/api/stats/',
  medicos: '/api/medicos/',
};

// Loop de atualização
async function fetchData() {
  try {
    const [r1, r2, r3] = await Promise.all([
      fetch(API.filas),
      fetch(API.stats),
      fetch(API.medicos),
    ]);

    const filasResp = await r1.json();
    const statsResp = await r2.json();
    const medResp   = await r3.json();

    renderFilas(filasResp);
    renderTaxa(statsResp);

    renderMedicosChart(medResp);
    renderTabela(medResp.medicos);

  } catch (err) {
    console.error('[dashboard] erro no polling:', err);
  }
}

fetchData();
setInterval(fetchData, 2_000);

// Gráficos e tabela
function renderFilas({ verde, amarelo, vermelho }) {
  Highcharts.chart('filas-chart', {
    chart: { type: 'column' },
    title: { text: 'Filas de Espera' },
    xAxis: { categories: ['Verde', 'Amarelo', 'Vermelho'] },
    series: [{ name: 'Pacientes', data: [verde, amarelo, vermelho] }],
  });
}

function renderTaxa({ atendidos, desistencias, esperando }) {
  Highcharts.chart('taxa-chart', {
    chart: { type: 'pie' },
    title: { text: 'Taxa de Conclusão' },
    plotOptions: {
      pie: { dataLabels: { format: '{point.name}: {point.percentage:.1f}%' } },
    },
    series: [{
      name: 'Pacientes',
      data: [
        { name: 'Atendidos',    y: atendidos    },
        { name: 'Desistências', y: desistencias },
        { name: 'Esperando',    y: esperando    },
      ],
    }],
  });
}

function renderMedicosChart({ medicos_livres, medicos_ocupados, medicos_totais }) {
  Highcharts.chart('medicos-chart', {
    chart: { type: 'bar' },
    title: { text: `Médicos (total ${medicos_totais})` },
    xAxis: { categories: ['Médicos'] },
    series: [
      { name: 'Livres',   data: [medicos_livres]   },
      { name: 'Ocupados', data: [medicos_ocupados] },
    ],
  });
}

function renderTabela(medicos) {
  const tbody = document.querySelector('#tabela-medicos tbody');
  if (!tbody) return;
  tbody.innerHTML = '';

  medicos.forEach(({ id, sala, ocupado }) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${id}</td>
      <td>${ocupado ? 'Ocupado' : 'Livre'}</td>
    `;
    tbody.appendChild(tr);
  });
}
