  
  function filterMetricsByDate(deviceId, metrics, begin, end){
    var startDate = document.getElementById(begin).value;
    var endDate = document.getElementById(end).value;
    for(let metric of metrics){
      buildCharts(deviceId, startDate, endDate, metric, "%Y-%m-%d");
    }
  }
  
  function buildCharts(deviceId, startDate, endDate, metric, format){
    var tooltips = {
      enabled: true,
      mode: 'single',
      callbacks: {
        label: function(tooltipItems, data) {
          var dataset = data.datasets[tooltipItems.datasetIndex]
  
          return dataset.value[tooltipItems.index] + " " + metric;
        }
      }
    }
  
    var scales = {
      yAxes: [{
        type: 'linear',
        stacked: true,
        ticks:{
          beginAtZero: true,
        }
      }]
    }
    let chartKey = 'device_metric_'+metric
    var charts = {};
    charts[chartKey] = ["usage_metrics", tooltips, scales]
    drawChart(deviceId, "/devices/chart", charts, startDate, endDate, format, null, metric);
  }
  