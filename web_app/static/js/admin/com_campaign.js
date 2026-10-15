function filterToStr(filter, noText, allText) {
    var resp = []
    $("#"+filter+" .badge .label").each(function () {
        var txt = $(this).text();
        if (txt == 'All') {
            resp = ['<b>'+allText+'</b>'];
            return false;
        }
        resp.push('<var class="bold">'+txt+'</var>');
    });
    if (!resp.length) return '<b>'+noText+'</b>'
    return resp.join(' OR ')
}

function checkValid() {
    var phones = parseInt($('#csv_file_form .badge.counter').text());
    var clients = parseInt($("#client_count").text());
    var leads = parseInt($("#lead_count").text());
    var text = $("#sms_content").val().trim();
    var name = $("#name").val().trim();
    if (!name) {
        error_toast(PaygOps_LNG["NO_CAMPAING_NAME"])
    } else if (!clients && !leads && !phones) {
        error_toast(PaygOps_LNG["NO_RECIPIENTS"])
    } else if (!text) {
        error_toast(PaygOps_LNG["EMPTY_CONTENT"])
    } else {
        $('#preview_modal .total_count').text(phones+leads+clients);
        $('#preview_modal .phones_count').text(phones);
        $('#preview_modal .client_count').text(clients);
        $('#preview_modal .lead_count').text(leads);
        $('#preview_modal .preview').html(text);
        $('#preview_modal .name_preview').text(name);

        $('#preview_modal .client_locs_list').html(filterToStr('Client\\[Location\\]', 'no location', 'any location'));
        $('#preview_modal .client_status_list').html(filterToStr('Client\\[Status\\]', 'without status', 'in any status'));
        $('#preview_modal .client_tag_list').html(filterToStr('Client\\[Tags\\]', 'no', 'any'));
        $('#preview_modal .lead_locs_list').html(filterToStr('Lead\\[Location\\]', 'no location', 'any location'));
        $('#preview_modal .lead_status_list').html(filterToStr('Lead\\[Status\\]', 'without status','in any status'));

        showModal($('#preview_modal'));
    } 
    return false;     
}

function addChip(e) {
    var sel = e.currentTarget
    id = $(sel).val();
    text = $(sel).find("option:selected").text();
    row = $(sel).parents(".filter_row");
    console.log()
    if ($(row).find('.chips-container input[value="'+id+'"]').length) {
        error_toast("'" + text + PaygOps_LNG["ALREADY_ADDED"])
    } else {
        var el = $('.chip-template .badge').clone();
        el.find('input').attr('name',row.attr('id')+'[]');
        el.find('input').val(id);
        el.find('.label').text(text);
        el.find('.close').click(updateCount);
        if (id=='all') {
            $(sel).attr('disabled', 'true')
            $(row).find('.chips-container').html(el);
        } else {
            $(row).find('.chips-container').append(el);
        }
    }
    $(sel).val(null);
    if ($(sel).is('.select_2')) {
        $(sel).trigger('change');
    } else {
        $(sel).formSelect();
    }
    updateCount(e);
}

function submitCommunication() {
    filters = $('#recipients_filter').serializeJSON({useIntKeysAsArrayIndex: true})
    //$('#result_modal').modal({dismissible: false})
    showModal($('#result_modal'));

    data = new FormData($('#csv_file_form')[0]);
    data.append("recipients_filter", JSON.stringify(filters))
    data.append("name", $("#name").val().trim())
    data.append("content", $("#sms_content").val().trim())

    $.ajax({
        url: "",
        type: "POST",
        enctype: 'multipart/form-data',
        data: data,
        processData: false,
        contentType: false,
        cache: false,
        dataType: "json",
        success: function (result) {
            success_toast(PaygOps_LNG["COMM_CAMPAIGN_SUCCESS"])
            window.location = '/admin/communication_campaigns'
        },
        error: function (xhr, ajaxOptions, thrownError) {
            closeModal($('#result_modal'));
            error_toast(thrownError);
        }
    });
}

function updateCount(e) {
    if ($(e.currentTarget).is(".close")) {
        var select = $(e.currentTarget).parents('.chips-container').prev().find('select');
        select.removeAttr('disabled');
        $(e.currentTarget).parents('.badge').remove();
    }
    $("#client_count").text('')
    $("#lead_count").text('')
    filters = $('#recipients_filter').serializeJSON({useIntKeysAsArrayIndex: true})
    debug_log('filters', filters)
    $.ajax({
        url: "",
        type: "POST",
        data: {"recipients_filter": JSON.stringify(filters)},
        dataType: "json",
        success: function (result) {
            debug_log('results', result)
            $("#client_count").text(result.clients)
            $("#lead_count").text(result.leads)
        },
        error: function (xhr, ajaxOptions, thrownError) {
            error_toast(thrownError)
        }
    });
}

$(document).ready(function () {

    $('#sms_content').on('input', function () {
        var txt = $(this).val();
        updateCounter(document, txt)
    });

    $('#client_location_selector').on('select2:select', addChip)
    $('#client_status_selector').on('select2:select', addChip)
    $('#client_tag_selector').on('select2:select', addChip)
    $('#client_offer_type_selector').on('select2:select', addChip)
    $('#lead_location_selector').on('select2:select', addChip)
    $('#lead_status_selector').on('select2:select', addChip)
    $('#lead_offer_type_selector').on('select2:select', addChip)

    $('#csv_file').on('change', function() {
        $('#csv_file_form .invalid-phones-text').addClass('hide');
        $('#csv_file').removeClass('invalid')
        if ($('#csv_file')[0].files.length) {
            $('#csv_file_form .counter').text('');
            file = new FormData($('#csv_file_form')[0]);
            $.ajax({
                url: "",
                type: "POST",
                enctype: 'multipart/form-data',
                data: file,
                processData: false,
                contentType: false,
                cache: false,
                dataType: "json",
                success: function (result) {
                    $('#csv_file_form .badge.counter').text(result.phones.valid);
                    if (result.phones.invalid) {
                        error_toast(PaygOps_LNG["PHONES_INVALID"])
                        $('#csv_file_form .invalid-phones-text').removeClass('hide');
                        $('#csv_file_form .invalid-counter').text(result.phones.invalid);
                        $('#csv_file_form .total-counter').text(result.phones.total);
                    }
                },
                error: function (xhr, ajaxOptions, thrownError) {
                    toast(xhr.responseJSON.error)
                    $('#csv_file_form .counter').text('0');
                    $('.file-path').addClass('invalid')
                }
            });
        } else {
            $('#csv_file_form .counter').text('0');
        }

        
    })

});