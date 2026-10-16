
class BulkTable {
    constructor(selector, opts) {

        this.selection = []
        this.table = $(selector);
        this.table[0].BulkTable = this;
        this.bulkCheckbox = this.table.find('input[name="bulk_action"]');
        this.bulkCheckbox[0].BulkTable = this;
        this.bulkCheckbox.change(function () {
            this.BulkTable.toogleAll();
        });
        var tickers = this.getTickers();
        for (const ticker of tickers.toArray()) {
            ticker.BulkTable = this;
            ticker.tickerID = this.getID(ticker);
            $(ticker).change(function () {
                if (this.BulkTable.selection.includes(this.tickerID)) {
                    this.BulkTable.selection = this.BulkTable.selection.filter(function(val) {return val !== ticker.tickerID});
                } else {
                    this.BulkTable.selection.push(this.tickerID);
                }
                this.BulkTable.selectionChanged();
                this.BulkTable.updateAllTicker();
            })
        }
        this.selectionChanged = typeof opts['onChange'] === 'undefined' ? function () {} : opts['onChange'];

    }
    toogleAll(){
        var newValue = this.bulkCheckbox.prop("checked");
        this.getTickers().each(function () {
            $(this).prop("checked", newValue);
            $(this).change();
        });
    }
    getTickers(){
        return this.table.find('.tickable');
    }
    getID(elem) {
        return parseInt(/^ticker\[(\d+)\]$/.exec($(elem).prop("name"))[1]);
    }
    updateAllTicker() {
        var newValue = this.getTickers().length == this.selection.length ? true : false;
        $(this.bulkCheckbox).prop("checked", newValue);
    }
}