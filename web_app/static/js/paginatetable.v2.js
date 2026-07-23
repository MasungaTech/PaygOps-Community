function refreshTables() {
    $(".paginate").each(function(i) {
        $(this).attr('id', "table" + i);
        Table('#table'+i,i);
    });
}
$(document).ready(function(){
    refreshTables()
});

 function Table(tableId,navNumber){
    var wrapperID = 'pagination-holder-'+navNumber;
    if ($(tableId).parent().attr('id') != wrapperID) {
        $(tableId).before('<div id="'+wrapperID+'"></div>');
        $(tableId).appendTo('#'+wrapperID);
    }
    var perPage = 10;
    var rowsTotal = $(tableId+' tbody tr').length;
    if(rowsTotal > perPage) {
        var data = [];
        for (var i = 1; i <= rowsTotal; i++) {
            data.push(i);
        }
        $('#pagination-holder-'+navNumber).pagination({
            dataSource: data,
            pageSize: perPage,
            showPrevious: false,
            showNext: false,
            className: 'paginationjs-group',
            ulClassName: 'pagination paginationjs-holder float-end mt-4 mb-0',
            activeClassName: 'page-item active',
            disableClassName: 'page-item',
            callback: function(data, pagination) {
                $(tableId+' tbody tr').hide();
                $(tableId+' tbody tr').slice(data[0]-1, data[0]+perPage-1).show();
            }
        })
        $(tableId+' tbody tr').hide();
        $(tableId+' tbody tr').slice(0, perPage).show();
    }
}
