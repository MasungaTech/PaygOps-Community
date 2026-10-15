
function portfolioSize() {
    $.get("/historical_data/chart/portfolio_size/recent", function(res) {
        if(res){
            document.getElementById("portfolio_size_date").innerHTML = res.calculated_on;
            document.getElementById("portfolio_size").innerHTML = res.content;
        }
    });
}

function averageCreditPeriod() {
    $.get("/historical_data/chart/average_credit_period/recent", function(res) {
        if(res){
            document.getElementById("average_credit_period_date").innerHTML = res.calculated_on;
            document.getElementById("average_credit_period").innerHTML = res.content;
        }
    });
}

function averageUnitCost() {
    $.get("/historical_data/chart/average_unit_cost/recent", function(res) {
        if(res){
            document.getElementById("average_unit_cost_date").innerHTML = res.calculated_on;
            document.getElementById("average_unit_cost").innerHTML = res.content;
        }
    });
}

function churnRate() {
    $.get("/historical_data/chart/churn_rate/recent", function(res) {
        if(res){
            document.getElementById("churn_rate_date").innerHTML = res.calculated_on;
            document.getElementById("churn_rate").innerHTML = res.content;
            }
    });
}

function revenue_average() {
    $.get("/historical_data/chart/revenue_average", function(res) {
        if(res){
            document.getElementById("revenue_average_date").innerHTML = res.calculated_on;
            document.getElementById("revenue_average").innerHTML = res.amount;
        }
    });
}

function standardCompliancePercentage() {
    $.get("/historical_data/chart/compliance_percentage/recent", function(res) {
        if(res){
            document.getElementById("compliance_percentage_date").innerHTML = res.calculated_on;
            document.getElementById("compliance_percentage").innerHTML = res.content;
            }
    });
}

function depositAsProportionCost() {
    $.get("/historical_data/chart/deposit-as-proportion-cost/recent", function(res) {
        if(res){
            document.getElementById("deposit_as_proportion_of_cost_date").innerHTML = res.calculated_on;
            document.getElementById("deposit_as_proportion_of_cost").innerHTML = res.content + '%';
        }
    });
}
