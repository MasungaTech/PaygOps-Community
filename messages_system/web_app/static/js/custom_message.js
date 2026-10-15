$(document).ready(function () {

    $('.template').each(function() {
        preview(this, false)
    });

    $('.saveCustomMsg').click(function() {
        if ($(this).find('button').is('.disabled')) {
            return false;
        }
        card = $(this).parents('.card-panel');
        tem = $(card).find('.editable .template');

        processedTem =  processTemplate(tem,'db').text();

        var data = {
            'default': $(card).find('.defaultMessage').is(":checked"),
            'disabled': $(card).find('.disableMessage').is(":checked"),
            'template': processedTem,
            'lang': $(card).attr('id').replace('lang_',''), 
        }

        $.ajax({
            url: '',
            type: "POST",
            data: JSON.stringify(data),
            contentType: "application/json",
            success: function (result) {
                toast(PaygOps_LNG["MESSAGE_TEMPLATE_UPDATED"]);
                if (data.default || data.disabled) {
                    tem.html($(card).find('.default .template').html());
                }
                disableSaveButton(tem);
            },
            error: function (result, ajaxOptions, thrownError) {
                if (result.status == 400) {
                    error_toast($.parseJSON(result.responseText));
                } else {
                    error_toast(PaygOps_LNG["SAVING_ERROR"]+result.responseText);
                }
            }
        });
        
    });
    
});


function get_errors(template) {
    if (/[{}]/.test($(template).html())) {
        return "{ and } are not allowed in the template.";
    } else if ($(template).html().trim() == '') {
        return "Template cannot be empty. Consider disabling this message."
    }
    return false
}
function validate(template) {
    error = get_errors(template);
    if (error) {
        $(template).addClass('is-invalid')
        $(template).siblings('.invalid-feedback').text(error);
    } else {
        $(template).removeClass('is-invalid')
        enableElement($(template).parents('.card-body').find('.save-message-button'))
    }
}

function toggleMessageMode(element, mode) {
    let card = $(element).parents('.lang-card');
    card.toggleClass('mode-editing').toggleClass('mode-'+mode);
}
function enableSaveButton(element) {
    $(element).parents('.card-panel').find('.saveCustomMsg button').removeClass('disabled');
}

function preview(el, changed=true) {
    var row = $(el).parents('.row');
    $(row).find('.preview').html(processTemplate($(el),'html').html());
    $(row).parent().find('.editable-template').val(processTemplate($(el),'db').html());
    if (changed) $(row).parent().find('.editable-template').trigger('change');
    updateCounter(row, processTemplate($(el),'counter').text())
}

function processTemplate(tem, target) {
    out = $(tem).clone()
    $(out).find('.badge').each(function () {
        vari = $(this).attr('data-variable');
        txt = (target!='db') ? variables[vari] : '{'+vari+'}' ;  
        $(this).replaceWith(txt);
    })
    if (target!='html') {
        $(out).find('div, p, br').each(function () {
            html =  $(this).html();  
            $(this).replaceWith('\n'+html);
        })
    }
    return out;
}
