var ChartConfig = {
  get: function (data) {
    return {
      type: 'line',
      data: data,
      options: {
        legend: {
          display: false
        }
      }
    }
  }
}

Spinner = {
  activate: function (spinnerId) {
    var spinner = document.getElementById(spinnerId);
    spinner.classList.remove('hide')
  },
  deactivate: function (spinnerId) {
    var spinner = document.getElementById(spinnerId);
    spinner.classList.add('hide')
  }
}

var AccountDashboard = {
  apiUrl: "/accounting/accounts/dashboard",

  buildAllCharts: function(ChartConfig, startDate, endDate) {
    this.buildTurnoverChart(ChartConfig, startDate, endDate);
    this.buildRevenueChart(ChartConfig, startDate, endDate);
    this.buildExpensesChart(ChartConfig, startDate, endDate);
    this.buildIncomeChart(ChartConfig, startDate, endDate);
    //this.buildRevenueChangeChart(ChartConfig, startDate, endDate);
    //this.buildNumberOfPaymentsChart(ChartConfig, startDate, endDate);
    //this.buildReceiptType(ChartConfig, startDate, endDate);
    this.buildTurnoverPerCustomerChart(ChartConfig, startDate, endDate);
  },
  buildData: function (startDate, endDate) {
    var dataUrl = this.createUrl('/data', startDate, endDate);

    $.get(dataUrl, function(response) {
      if(response){
        var totalTurnover = document.getElementById('turnover-value');
        totalTurnover.innerText = response.total_turnover;

        var turnoverAverage = document.getElementById('average-turnover');
        turnoverAverage.innerText = response.average_turnover;

        var accountReceivable = document.getElementById('account-receivable');
        accountReceivable.innerHTML = response.account_receivable;

        var averageReceivable = document.getElementById('average-account-receivable');
        averageReceivable.innerHTML = response.average_account_receivable_per_client;
      }
    });
  },
  buildTurnoverChart: function (Config, startDate, endDate) {
    //Spinner.activate('turnover_spinner');
    var turnoverUrl = this.createUrl('/turnover_chart_data', startDate, endDate);
    var turnoverChart = document.getElementById("Turnover");
    var ctx = turnoverChart.getContext("2d");

    turnoverChart.height = 300;
    turnoverChart.width = 800;

    if(window.turnoverChart){
      window.turnoverChart.destroy();
    }

    $.get(turnoverUrl, function(response) {
      if(response){
        //Spinner.activate('turnover_spinner');
        var config = Config.get(response.data);
        window.turnoverChart = new Chart(ctx, config);
      }
    });
  },
  buildRevenueChart: function (Config, startDate, endDate) {
    //Spinner.activate('revenue_spinner');
    var revenueChangeUrl = this.createUrl('/revenue_chart_data', startDate, endDate);
    var revenueChart = document.getElementById("Revenue");
    var ctx = revenueChart.getContext("2d");

    revenueChart.height = 300;
    revenueChart.width = 800;

    if(window.revenueChart){
      window.revenueChart.destroy();
    }

    $.get(revenueChangeUrl, function(response) {
      if(response){
        //Spinner.activate('revenue_spinner');
        var config = Config.get(response.data);
        window.revenueChart = new Chart(ctx, config);
      }
    });
  },
  buildExpensesChart: function (Config, startDate, endDate) {
    //Spinner.activate('expenses_spinner');
    var expensesUrl = this.createUrl('/expenses_chart_data', startDate, endDate);
    var expensesChart = document.getElementById("Expenses") ;
    var ctx = expensesChart.getContext("2d");

    expensesChart.height = 300;
    expensesChart.width = 800;

    if(window.expensesChart){
      window.expensesChart.destroy();
    }

    $.get(expensesUrl, function(response) {
      if(response){
        //Spinner.activate('expenses_spinner');
        var config = Config.get(response.data);
        window.expensesChart = new Chart(ctx, config);
      }
    });
  },
  buildIncomeChart: function (Config, startDate, endDate) {
    //Spinner.activate('income_spinner');
    var incomeUrl = this.createUrl('/income_data', startDate, endDate);
    var incomeChart = document.getElementById("Income") ;
    var ctx = incomeChart.getContext("2d");

    incomeChart.height = 300;
    incomeChart.width = 800;

    if(window.incomeChart){
      window.incomeChart.destroy();
    }

    $.get(incomeUrl, function(response) {
      if(response){
        //Spinner.activate('income_spinner');
        var config = Config.get(response.data);
        window.incomeChart = new Chart(ctx, config);
      }
    });
  },
  buildRevenueChangeChart: function (Config, startDate, endDate) {
    //Spinner.activate('revenue_change_spinner');
    var turnoverChangeUrl = this.createUrl('/revenue_change_data', startDate, endDate);
    var turnoverChangeChart = document.getElementById("RevenueChange") ;
    var ctx = turnoverChangeChart.getContext("2d");

    turnoverChangeChart.height = 300;
    turnoverChangeChart.width = 800;

    if(window.turnoverChangeChart){
      window.turnoverChangeChart.destroy();
    }

    $.get(turnoverChangeUrl, function(response) {
      if(response){
        //Spinner.activate('revenue_change_spinner');
        var config = Config.get(response.data);
        window.turnoverChangeChart = new Chart(ctx, config);
      }
    });
  },
  buildTurnoverPerCustomerChart: function (Config, startDate, endDate) {
    //Spinner.activate('revenue_per_customer_spinner');
    var turnoverPerCustomerUrl = this.createUrl('/turnover_per_customer_data', startDate, endDate);
    var turnoverPerCustomerChart = document.getElementById("RevenuePerCustomer") ;
    var ctx = turnoverPerCustomerChart.getContext("2d");

    turnoverPerCustomerChart.height = 300;
    turnoverPerCustomerChart.width = 800;

    if(window.turnoverPerCustomerChart){
      window.turnoverPerCustomerChart.destroy();
    }

    $.get(turnoverPerCustomerUrl, function(response) {
      if(response){
        //Spinner.activate('revenue_per_customer_spinner');
        var config = Config.get(response.data);
        window.turnoverPerCustomerChart = new Chart(ctx, config);
      }
    });
  },
  buildNumberOfPaymentsChart: function (Config, startDate, endDate) {
    //Spinner.activate('payments_spinner');
    var numberOfPaymentsUrl = this.createUrl('/number_of_payments_data', startDate, endDate);
    var numberOfPaymentsChart = document.getElementById("Payments") ;
    var ctx = numberOfPaymentsChart.getContext("2d");

    numberOfPaymentsChart.height = 300;
    numberOfPaymentsChart.width = 800;

    if(window.numberOfPaymentsChart){
      window.numberOfPaymentsChart.destroy();
    }

    $.get(numberOfPaymentsUrl, function(response) {
      if(response){
        //Spinner.activate('payments_spinner');
        var config = Config.get(response.data);
        window.numberOfPaymentsChart = new Chart(ctx, config);
      }
    });
  },
  buildReceiptType: function (Config, startDate, endDate) {
    //Spinner.activate('receipt_type_spinner');
    var receiptTypeUrl = this.createUrl('/receipt_type_data', startDate, endDate);
    var receiptTypeChart = document.getElementById("ReceiptType") ;
    var ctx = receiptTypeChart.getContext("2d");

    receiptTypeChart.height = 300;
    receiptTypeChart.width = 800;

    if(window.receiptTypeChart){
      window.receiptTypeChart.destroy();
    }

    $.get(receiptTypeUrl, function(response) {
      if(response){
        var config = Config.get(response.data);
        //Spinner.activate('receipt_type_spinner');
        window.receiptTypeChart = new Chart(ctx, config);
      }
    });
  },
  createUrl: function(path, startDate, endDate) {
    return this.apiUrl + path + "?start_date=" + startDate + "&end_date=" + endDate;
  }
}
