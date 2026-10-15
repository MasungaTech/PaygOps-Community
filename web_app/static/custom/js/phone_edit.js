function setContactPhone(phone_number, person_id, person_type) {
    if(phone_number != null) {
        var form_data = {'preferred_phone_number': phone_number}
        var submit_url = '/'+person_type+'/'+person_id
        sendDataToAPI(form_data, submit_url, {
            'success_action': function (result) { success_toast(PaygOps_LNG["PHONE_SET_PREFFERED"]); },
            'error_action': function (result) { error_toast(PaygOps_LNG["COULD_NOT_SET_PREFFERED"]); },
        })
    }
}

// ----- To refactor after API changes -----

function addPhoneToPerson(person_id,lead_id, extension){
    addPrefixToNumber(extension)
    console.log('lead_id', lead_id, 'person_id', person_id)
    number = $('#new_phone').val();
    if(!$('#new_phone').valid() || number.length == 0) {
        return;
    }
    if (
      typeof person_id != 'undefined' &&
      typeof person_id != 'null' && person_id != '' &&  person_id != null 
    ) {
      sendPhoneToPerson(number, person_id, lead_id);
    }
    else {
      addPhoneIfNotExists(number);
    }
}

function addPrefixToNumber(extension){
    number = $('#new_phone').val();
    if(typeof number === 'string' && !number.startsWith('+') && number.length > 0) {
        number = number.replace(/^0+/,"") // We remove leading 0s if any
        if(number.startsWith(extension)) {
            number = '+'+number
        } else {
            number = '+'+extension+number
        }
        $('#new_phone').val(number)
        $('#new_phone').valid()
    }
}

function appendPhoneToSelection(phone){
    var $select = $("#preferred_phone_number");
    $select.append('<option value="'+phone+'">'+phone+'</option>');
    var currentVal = $select.val();
    // Auto-select the new phone if no phone is currently selected
    // (e.g. first phone being added or only placeholder option present)
    if(currentVal == null || currentVal === '') {
        $select.val(phone).trigger('change');
    }
    refreshSelects($select);
    $("#new_phone").val('');
    $('#pn_holder').append('<input type="hidden" name="phone_numbers[]" value="'+phone+'" />')
}

function deletePhone(last_allowed) {
    var pn_to_remove = $("#preferred_phone_number").val()
    if(pn_to_remove == null) {
        error_toast(PaygOps_LNG["SELECT_PHONE_FIRST"])
    } else {
        console.log(last_allowed, $("#preferred_phone_number").children().length)
        if(!last_allowed && $("#preferred_phone_number").children().length < 3) {
            error_toast(PaygOps_LNG["CANNOT_REMOVE_LAST_PHONE"])
        } else {
            $("#preferred_phone_number").children().filter(function(){return this.value==pn_to_remove}).remove();
            $("#pn_holder").children().filter(function(){return this.value==pn_to_remove}).remove();
            refreshSelects($("#preferred_phone_number"));
            // We select the first number if any
            new_val = $("#preferred_phone_number option:not([disabled]):first").val();
            $("#preferred_phone_number").val(new_val).trigger('change');
            success_toast(PaygOps_LNG["PHONE_DELETED"])
        }
    }
}

function sendPhoneToPerson(number, person_id, lead_id){
   $.ajax({
       url: '/phone_numbers/add_new',
       type: "POST",
       data: {data: JSON.stringify({number: number, person_id: person_id, lead_id: lead_id || null})},
       dataType: "json",
       success: function (result) {
           if (!result.duplicate) {
               appendPhoneToSelection(number);
               success_toast(result.flash_msg)
           } else if (result.duplicate) {
               toast(result.flash_msg)
           }else {
               error_toast(PaygOps_LNG["CANNOT_ADD_PHONE"]);
           }
       },
       error: function (xhr, ajaxOptions, thrownError) {
           error_toast(PaygOps_LNG["CANNOT_ADD_PHONE"]);
           console.log('error', xhr.answer)
       }
   });
}

function addPhoneIfNotExists(number) {
   $.ajax({
       url: '/phone_numbers/'+number+'/exists',
       type: "GET",
       success: function (result) {
           if (result.exists == true) {
               toast(result.message);
           } else if (result.exists == false) {
               success_toast(PaygOps_LNG["PHONE_ADDED"]);
               appendPhoneToSelection(number);
           } else {
               error_toast(PaygOps_LNG["CANNOT_ADD_PHONE"]);
           }
           return result.exists;
       },
       error: function (xhr, ajaxOptions, thrownError) {
           error_toast(PaygOps_LNG["CANNOT_ADD_PHONE"]);
           console.log('error', xhr.answer)
       }
   });
}

function removeNumberManual(number, person_id) {
    toast(PaygOps_LNG["REMOVE_NUMBER_CONFIRM"]+number+' <br><a href="#" onclick="removeNumber('+number+', '+person_id+')"><strong>'+PaygOps_LNG["CONFIRM"]+'</strong></a>')
}


function removeNumber(number, person_id, reload = true) {
    $.ajax({
        url: '/phone_numbers/+'+number+'/'+person_id+'/remove',
        type: "GET",
        success: function (result) {
            if(result.success) {
                success_toast(result.message);
                if(reload) {
                    reloadPage();
                }
            } else {
                error_toast(result.message);
            }
        },
        error: function (xhr, ajaxOptions, thrownError) {
            error_toast(PaygOps_LNG["CANNOT_REMOVE_PHONE"]);
            console.warn(xhr.answer)
        }
    });
}