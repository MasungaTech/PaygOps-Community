function buildChartCanvas(name, response, tooltips={}, scales={}){
    var config = getConfig(response, tooltips, scales);
    var obj = name + "Obj"
    var ctx = document.getElementById(name).getContext("2d");
    if(window[obj]) {
      window[obj].destroy();
    }
    window[obj] = new Chart(ctx, config);
}

function getConfig(response, tooltips, scales){
    return {
        type: response.type,
        data: response.data,
        options: {
            legend: {
                position: 'bottom'
            },
            responsive: true,
            tooltips: tooltips,
            scales: scales
        },
    };
}

function createUrl(baseUrl, entityId, action, startDate, endDate, format, frequency, metric){
    let url = baseUrl + "/" + action + "/" + entityId +
           "?start_date=" + startDate +
           "&end_date=" + endDate +
           "&format=" + format;
    if(frequency)
        url += "&frequency=" + frequency;
    if(metric)
        url += "&metric=" + metric;
    return url;
           
}
function drawChart(id, baseUrl, charts, startDate, endDate, format, frequency=null, metric=null){
    for (const chart in charts) {
        var data = charts[chart]
        var url = createUrl(baseUrl, id, data[0], startDate, endDate, format, frequency, metric);
        $.get(url, function(response) {
          if(response){
            buildChartCanvas(chart, response, data[1], data[2])
          }
        });
    }
}
  