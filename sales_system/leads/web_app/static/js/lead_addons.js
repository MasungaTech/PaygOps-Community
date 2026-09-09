update_prices = function () {
    offer = $('#offer_id_selector').val();
    if (offer) {
        console.log(offers[offer])
        offer_dis = $('.offer_price_display');
        offer_dis.removeClass('hide');
        offer_dis.parent().removeClass('hide')
        if(offers[offer].needs_loan_mode) {
            showForm('.loan-mode');
        } else {
            hideForm('.loan-mode');
        }
        if (offers[offer].linked_to_product && offers[offer].is_serialized) {
            showForm('.linked-to-product');
            hideForm('.not-linked-to-product');
        } else {
            showForm('.not-linked-to-product');
            hideForm('.linked-to-product');
        }
        $('#device_serial').attr('data-add_on_offer', offer)
        up = offers[offer].price;
        dp = offers[offer].downpayment;
        offer_dis.find('var').text(offers[offer].price);
        quant = parseFloat($('#add_addon_form input[name=quantity_sold]').val());
        total = Math.round((quant*up + Number.EPSILON) * 100) / 100;
        downpayment = Math.round((quant*dp + Number.EPSILON) * 100) / 100;

        od = offers[offer].duration_change;
        total_days = Math.round((quant*od + Number.EPSILON) * 100) / 100;

        if_show(up !=0, '.offer_price_display');

        $('.unit_downpayment_no_value_display').removeClass('hide').find('var').text(dp);
        if_show(up==0 && dp != 0, '.unit_downpayment_no_value_display');
        $('.downpayment_no_value_display').removeClass('hide').find('var').text(downpayment);
        if_show(up==0 && dp != 0 && !isNaN(downpayment), '.downpayment_no_value_display');

        if (!isNaN(total_days) && od != 0) {
            $('.total_days_display').removeClass('hide').find('var').text(total_days);
        } else {
            if_show(up == 0, '.offer_price_display'); // if 0 value but is a loan extension add-on
            $('.total_days_display').addClass('hide')
        }
        if (!isNaN(total) && up != 0) {
            $('.total_price_display').removeClass('hide').find('var').text(total);
            $('.downpayment_display').removeClass('hide').find('var').text(downpayment);
        } else {
            $('.total_price_display').addClass('hide')
            $('.downpayment_display').addClass('hide')
        }
        allow_decimal_quantities = offers[offer].allow_decimal_quantities
        if (!allow_decimal_quantities && !Number.isInteger(quant)) {
             $('#allow_decimal_quantities').removeClass('hide')
        }else {
            $('#allow_decimal_quantities').addClass('hide')
        }
    }
}

function if_show(c, selector) {
    if (c) {$(selector).removeClass('hide')} else {$(selector).addClass('hide')}
}

var EDITED = false;
var firstAddonEdited = false;
function edited(el) {
    EDITED = true;
    var tr = $(el.currentTarget).parents('tr')
    enableElements(tr.find('.save-addon'));
    if(!firstAddonEdited) {
        tr.siblings().each(function () {
            disableElements($(this).find('select, input'));
            disableElements($(this).find('.remove-addon'));
            $(this).css('background', "#eee").css('color', '#888');
        });
        disableElements($('#add_addon_form select, #add_addon_form input'));
        disableElements($('#add_addon_form .send-form'));
        firstAddonEdited = true;
    }
    offer = tr.find('.offer_selector').val();
    debug_log('offer_edited', offer)
    up = offers[offer].price;
    dp = offers[offer].downpayment;
    quant = parseFloat(tr.find('input[name=quantity_sold]').val());
    total = Math.round((quant*up + Number.EPSILON) * 100) / 100;
    downpayment = Math.round((quant*dp + Number.EPSILON) * 100) / 100;
    tr.find('.total_price').text(total);
    tr.find('.downpayment').text(downpayment);
    tr.find('.type').text(offers[offer].type);
    if (offers[offer].needs_loan_mode) {
        enableElement(tr.find('.type').siblings('.input-field'))
    } else {
        disableElement(tr.find('.type').siblings('.input-field'))
    }
    var tot = 0;
    total_of_totals = tr.parents('table').find('.total_price').each(function () {
        tot += parseFloat($(this).text());
    });
    $('.total_addons_value').find('var').text(tot+' '+currencySymbol);
    var ext = offers[offer].needs_loan_mode ? '<i class="material-symbols-rounded" data-bs-toggle="tooltip" data-bs-html="true" title="Save to update">sync_disabled</i>' : '-';
    tr.find('td.extension-info').html(ext);
    refreshTooltips();
}

function save_addon(btn) {
    EDITED = false;
    SubmitForm(btn, '/'+$(btn).data('endpoint')+'/'+$(btn).data('addon'), {
        "method": $(btn).data('method'),
        "success_action": "reload",
    })
}

function sendAddonForm(btn) {
    SubmitForm(btn, $(btn.form).attr('action'), {
        'bypassPrevention': true
    });
}

function sendBundleForm() {
    var form = $('#add_bundle_form');
    if (form.valid()) {
        var form_data = form.serializeJSON()
        sendDataToAPI(form_data, '/addons_from_bundle', {
            'bypassPrevention': true
        })
    } else {
        debug_log('Form invalid!', $(form).validate()['errorList'])
    }
}

$(document).ready(function () {
    $('#add_addon_form').validate({ignore: ':hidden:not("select"), .hide *'})
    $('#offer_id_selector').change(update_prices);
    $('#add_addon_form input[name=quantity_sold]').keyup(update_prices);
    $('.loan-mode select').change(update_prices);
    $('.remove-addon').click(function () {
        sendDataToAPI({}, '/'+$(this).data('endpoint')+'/'+$(this).data('addon'), {
            'bypassPrevention': true,
            'method': 'DELETE'
        })
    });
    $('.addons-table input').keyup(edited);
    $('.addons-table textarea').keyup(edited);
    $('.addons-table select').on('select2:select', edited);
    $(window).on('beforeunload', function() {
        if (EDITED) {
            return 'Your changes have not been saved. You still want to leave the page?';
        }
    });
})
