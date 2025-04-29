const API = {
  filas:  '/api/filas/',
  stats:  '/api/stats/',
  medicos: '/api/medicos/',
};

async function fetchData() {
  try {
    const [r1, r2, r3] = await Promise.all([
      fetch(API.filas), fetch(API.stats), fetch(API.medicos)
    ]);
    const filas   = await r1.json();
    const stats   = await r2.json();
    const { medicos } = await r3.json();

    renderFilas(filas);
    renderTaxa(stats);
    renderMedicos(medicos);
    renderTabela(medicos);
  } catch (err) {
    console.error('Erro no polling:', err);
  }
}

fetchData();
// atualiza a cada 2s
setInterval(fetchData, 2000);

function renderFilas(data) {
  Highcharts.chart('filas-chart', {
    chart: { type: 'column' },
    title: { text: 'Filas de Espera' },
    xAxis: { categories: ['Verde','Amarelo','Vermelho'] },
    series: [{ name: 'Pacientes',
      data: [data.verde, data.amarelo, data.vermelho]
    }]
  });
}

function renderTaxa(data) {
  Highcharts.chart('taxa-chart', {
    chart: { type: 'pie' },
    title: { text: 'Taxa de Conclusão (total de pacientes)' },
    plotOptions: {
      pie: {
        dataLabels: {
          format: '{point.name}: {point.percentage:.1f}%'
        }
      }
    },
    series: [{
      name: 'Pacientes',
      data: [
        { name: 'Atendidos',  y: data.atendidos  },
        { name: 'Desistências', y: data.desistencias },
        { name: 'Esperando',  y: data.esperando  }
      ]
    }]
  });
}

function renderMedicos(medicos) {
  const livres   = medicos.filter(m => !m.ocupado).length;
  const ocupados = medicos.filter(m => m.ocupado).length;
  Highcharts.chart('medicos-chart', {
    chart: { type: 'bar' },
    title: { text: 'Médicos: Livres vs Ocupados' },
    xAxis: { categories: ['Médicos'] },
    series: [
      { name: 'Livres',   data: [livres] },
      { name: 'Ocupados', data: [ocupados] }
    ]
  });
}

function renderTabela(medicos) {
  const tbody = document.querySelector('#tabela-medicos tbody');
  tbody.innerHTML = '';
  medicos.forEach(m => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${m.id}</td>
      <td>${m.sala ?? '-'}</td>
      <td>${m.ocupado ? 'Ocupado' : 'Livre'}</td>
    `;
    tbody.appendChild(tr);
  });
}
