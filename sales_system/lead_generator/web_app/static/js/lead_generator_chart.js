
function filterOfferByDate(leadGeneratorId, begin, end){
  var startDate = document.getElementById(begin).value;
  var endDate = document.getElementById(end).value;
  var frequency = document.getElementById('frequency').value;

  buildCharts(leadGeneratorId, startDate, endDate, frequency, "%Y-%m-%d");
}

function buildCharts(leadGeneratorId, startDate, endDate, frequency, format){
  var tooltips = {
    enabled: true,
    mode: 'single',
    callbacks: {
      label: function(tooltipItems, data) {
        var dataset = data.datasets[tooltipItems.datasetIndex]
        var percent = (dataset.data[tooltipItems.index]).toFixed(2);

        return percent + "% / " + dataset.value[tooltipItems.index];
      }
    }
  }

  var scales = {
    yAxes: [{
      stacked: true,
      ticks:{
        min: 0,
        max: 100.0
      }
    }]
  }

  var charts = {
    'NewLeads': ["new_leads", {}, {}],
    'NewLeadsByOfferType': ["new_leads_by_offer_type", {}, {}],
    'DropRate': ["drop_rate", {}, {}]
  };

  drawChart(leadGeneratorId, "/lead_generators/chart", charts, startDate, endDate, format, frequency);

}
