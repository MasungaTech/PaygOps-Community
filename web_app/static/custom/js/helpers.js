// ------ Form Elements ----- //

var tagsInited = false;

function refreshAllFormsElements() {
    refreshInputs();
    refreshSelects();
    refreshDatepickers();
    refreshSignaturePads();
    if(!tagsInited) {
        // They cannot be initiated multiple times
        refreshTags();
        tagsInited = true;
    }
    refreshFormValidation();
    refreshTooltips();
    refreshHiddenElements();
    refreshModals();
    updateFieldSets();
}

function deInitFormElements() {
    $('select').each(function() {
        if ($(this).hasClass("select2-hidden-accessible")) {
            // Select2 has already been initialized, we destroy
            $(this).select2("destroy");
        }
    });
    $('.datepicker').each(function() {
        flatpickr(this).destroy()
    });
}

function deInitFormElementsInElem(elem) {
    $(elem).find('select').each(function() {
        if ($(this).hasClass("select2-hidden-accessible")) {
            // Select2 has already been initialized, we destroy
            $(this).select2("destroy");
        }
    });
    $(elem).find('.datepicker').each(function() {
        flatpickr(this).destroy()
    });
}


function updateFieldSets() {
    // Disable Select2 select elements in disable fieldsets
    $("fieldset:disabled").find("select").each(function(input, elem) {
        $(elem).prop('disabled', true);
    });
}

function refreshTooltips() {
    $('.tooltip').remove();
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}


function refreshFormValidation() {
    $('form:not(".novalidate")').each(function() {
        // We set validation on all forms
        $(this).validate({
            ignore: '.ignore, .skip, .hiddenform, :hidden:not("select"):not(".reqsignature"):not(".flatpickr-input")'
        });
    });
    $('form').each(function() {
        // We make the button auto-enabled if one of the inputs is change
        var formSubmitButton = $($(this).find('.submit-btn')[0])
        $(this.elements).on('input', function() {
            formSubmitButton.removeClass('disabled')
        });
        // We need to listen to change for tags instead of input
        $(this.elements).filter(".tags-field").on('change', function() {
            formSubmitButton.removeClass('disabled')
        })
        $(this.elements).filter(".device-tags-field").on('change', function() {
            formSubmitButton.removeClass('disabled')
        })
    });
}

function getSignatureInputFromPad(pad) {
    return $($(pad).parent('div:first').parent('div:first').find('.signature-uploader-input')[0])
}


function refreshSignaturePads() {
    $('.signature-pad:not(.disabled)').each(function() {
        var pad_input = getSignatureInputFromPad(this);
        if(pad_input.hasClass('signed')) {
            return
        }
        this.signaturePad = new SignaturePad(this, {
            backgroundColor: 'white',
        });
        this.signaturePad.uploaded = false;
        this.signaturePad.addEventListener("endStroke", () => {
            $(this).removeClass('invalid')
            pad_input.val('signed').change();
            pad_input.triggerHandler('input')
            pad_input.addClass('signed')
        }, { once: true });
        
    });
    window.addEventListener("resize", resizeCanvas);
    $('.collapse').on('shown.bs.collapse', function () {
        resizeCanvas();
    });
    resizeCanvas();
}

function resizeCanvas() {
    $('.signature-pad:not(.disabled)').each(function() {
        var canvas = this;
        if (canvas.offsetWidth == 0 || canvas.offsetHeight == 0) {
            return
        }
        const ratio =  Math.max(window.devicePixelRatio || 1, 1);
        canvas.width = canvas.offsetWidth * ratio;
        canvas.height = canvas.offsetHeight * ratio;
        const context = canvas.getContext('2d');
        context.scale(ratio, ratio);
        context.fillStyle = 'white';
        context.fillRect(0, 0, canvas.width, canvas.height);
        //$(this).signaturePad.fromData(signaturePad.toData()); // otherwise isEmpty() might return incorrect value
    });
}


function refreshInputs() {
    $('.autosize').each(function() {
        autosize($(this));
    });
    $(':input').each(function() {
        if(!$(this).hasClass('nochangeonload')) {
            if($(this).attr('type') == 'checkbox') {
                $(this).triggerHandler('click'); // We trigger the onclick event to show/hide stuff in the form accordingly
            }
        }
    });
}

function updateAutosize() {
    $('.autosize').each(function() {
        autosize.update($(this));
    });
}

var defaultDatePickerOptions = {
    altFormat: "d M Y",
    altInput: true,
    dateFormat: "Y-m-d",
    time_24hr: true,
    allowInput: true,
};

function refreshDatepickers(subset=undefined) { 
    if (!subset) {
        subset = $('.datepicker');
    }
    subset.each(function() {
        var options = {};
        $.extend(options, defaultDatePickerOptions);
        var type = $(this).attr('data-type')
        if(type == 'datetimepicker') {
            options.altFormat = "d/m/Y H:i"
            options.dateFormat = "Z"
            options.enableTime = true
        }
        if(type == 'timepicker') {
            options.altFormat = "H:i"
            options.dateFormat = "H:i"
            options.enableTime = true
            options.noCalendar = true
        }
        options.allowInvalidPreload = true
        options.disableMobile = true
        if($(this).attr('data-datepicker-min')) {
            options.minDate = new Date($(this).attr('data-datepicker-min'));
        }
        if($(this).attr('data-datepicker-max')) {
            options.maxDate = new Date($(this).attr('data-datepicker-max'));
        }
        if ($(this).attr('data-value')) {
            if(type == 'timepicker') {
                options.defaultDate = $(this).attr('data-value')
            } else {
                options.defaultDate = new Date($(this).attr('data-value'));
            }
        }
        if(isCustomApp) {
            // Set readonly on the original input before initializing flatpickr
            $(this).attr('readonly', 'readonly');
        }
        $(this).flatpickr(options);
        if(isCustomApp) {
            // Set readonly on the flatpickr input after initialization
            $(this).siblings('input.datepicker').attr('readonly', 'readonly');
        }
    });
}

// We add this convenience function for setting/getting dates using the bootstrap datepicker
$.fn.getDate = function() {
    return this[0]._flatpickr.selectedDates
};

$.fn.setDate = function(value) {
    return this[0]._flatpickr.setDate(value);
};

function addOptionsToSelect(select_elem, new_options) {
    select_elem = $(select_elem)
    $.each(new_options, function(new_opt) {
        select_elem.append('<option value="'+new_opt+'">'+new_options[new_opt]+'</option>')
    })
    refreshSelects(select_elem);
}

function refreshSelects(subset=undefined) {
    if (!subset) {
        subset = $('select');
    }
    subset.each(function() { 
        if ($(this).parents('.no-select').length) {
            return;
        } else if ($(this).data('icon-picker')) {
            initIconPicker($(this));
        } else {
            var noResultsMsg = 'No Results Found.'
            if ($(this).data('no-results-msg')) {
                noResultsMsg = $(this).data('no-results-msg');
            }
            modal = $(this).parents(".modal")
            parent = modal.length ? modal : $(this).parent()
            function formatOption(state) {
                if (!state.id || !state.element) {
                    return state.text
                }
                return $('<span class="'+state.element.className+'">'+state.text+'</span>');
            }
            var config = {
                "language": {
                    "noResults": function () {
                        return noResultsMsg;
                    }
                },
                escapeMarkup: function (markup) {
                    return markup;
                },
                dropdownParent: $(this).parent(),
                templateResult: formatOption,
                debug: DEBUG_MODE
            };
            function search(data,term) {
                if ($.trim(term)==='') {
                    return data;
                }
                var search = data.text.toLowerCase().indexOf(term.toLowerCase()); 
                if (search > -1) {
                    return data;
                }
                return null;
            }
            config.matcher = function (params, data) {
                if (data.disabled == true && (data.id == "default" || data.id == "")) {
                    return null;
                }
                if (typeof data.children === 'undefined') {
                    return search(data,params.term);
                } else {
                    var filteredChildren = [];
                    $.each(data.children, function (idx, child) {
                        if (search(child,params.term)) {
                          filteredChildren.push(child);
                        }
                    });
                    if (filteredChildren.length) {
                        var modifiedData = $.extend({}, data, true);
                        modifiedData.children = filteredChildren;
                        return modifiedData;
                    }
                }
                return null;
            };
            if ($(this).hasClass(AJAX_SELECT_CLASS)) {
                var url_base = $(this).attr('data-ajax--url') || '';
                var extra = [];
                $(this).find('option').each(function() {
                    var val = $(this).attr('value');
                    if (!$(this).attr('disabled') || (val != "default" && val != "")) {
                        extra.push({
                            'id': val,
                            'text': $(this).text(),
                            'data': $(this)[0].dataset
                        })
                    }
                });
                if (!$(this).attr('data-source')) $(this).attr('data-source', $(this).attr('id'));
                var el = this;
                config.ajax = {
                    url: url_base,
                    data: function (params) {
                        var data = el.dataset;
                        return Object.assign({}, params, data);
                    },
                    processResults: function (data) {
                        data.results = data.results.concat(extra)
                        return data;
                    },
                    dataType: 'json',
                    cache: $(this).attr('data-cache') == 'false' ? false : true,
                    delay: 500
                };
                config.minimumInputLength = $(this).attr('data-min-chars') || 2;
                config.templateSelection = function(data, container) {
                    // This handles support for custom data
                    if (data.hasOwnProperty('data')) {
                        Object.entries(data.data).map(([key, value]) => {
                            $(data.element).attr('data-' + key, value);
                        });
                    }
                    return data.text;
                }
            }
            if ($(this).data('styled-selection')) config.templateSelection = formatOption;            
            $(this).select2(config);
            $(this).on('select2:open',function(e) {
                results = $(this).parents('.modal').find('.select2-dropdown')[0];
                if (results) setTimeout(function(){results.scrollIntoView(false)},10);
            });
            if(!$(this).hasClass('nochangeonload')) {
                // We trigger the onchange event to show/hide stuff in the form accordingly
                $(this).trigger('change');
            }  
            $(this).on('change', function () {
                $(this).removeClass('invalid');
                try { // needed to avoid break loading of multiple selects asynchronously
                    $(this).valid();
                } catch {}
            });
        }
    }); 
}

function passwordFormPreprocessor(form) {
    var pass = $(form).find('input[type=password]:not(.no-hash):not(.hashed)')
    pass.each(function () {
        if ($(this).val()) {
            const shaObj = new jsSHA("SHA-256", "TEXT", { encoding: "UTF8" });
            shaObj.update($(this).val());
            $(this).addClass("hashed")
            $(this).val(shaObj.getHash("HEX"));
        }
    });
}


function cleanTagValue(input_field, raw_value) {
    input_field.value = JSON.parse(raw_value).map(item => item.value);
}

function refreshTags() {
    $('.tags-field').each(function() { 
        new TagsField({
            'tagsData': EXISTING_TAGS_LIST,
            'inputElement': this
        })
        this.processVal = cleanTagValue;
    });
    $('.device-tags-field').each(function() { 
        new TagsField({
            'tagsData': EXISTING_DEVICE_TAGS_LIST,
            'inputElement': this
        })
        this.processVal = cleanTagValue;
    });
}


function enableElement(elem) {
    elem.attr('disabled', false)
    elem.removeClass('disabled')
    if(elem.hasClass('select_2')) {
        refreshSelects(elem)
    }
}


function disableElement(elem) {
    elem.attr('disabled', true)
    elem.addClass('disabled')
    if(elem.hasClass('select_2')) {
        refreshSelects(elem)
    }
}

function enableElements(elem) {
    $(elem).each(function() {
        enableElement($(this))
    })
}

function disableElements(elem) {
    $(elem).each(function() {
        disableElement($(this))
    })
}

/* ---- Toasts ---- */

function toastr_defaults(duration) {
    return {timeOut: duration ? duration : 5000, newestOnTop: true, progressBar: true}
}


// This is a nice handler for toast, to be improved for different types
function toast(message, title, duration) {
    toastr.info(message, title, toastr_defaults(duration));
}

function success_toast(message, title, duration) {
    toastr.success(message, title, toastr_defaults(duration));
}

function error_toast(message, title, duration) {
    toastr.error(message, title, toastr_defaults(duration));
}

function warning_toast(message, title, duration) {
    toastr.warning(message, title, toastr_defaults(duration));
}

// ---- Validation ---- //

function setValidators() {
    $.validator.setDefaults({
        errorClass: 'invalid',
        errorPlacement: function (error, element) {
            var par = element.parent()
            par.find('.error-icon-container').remove();
            if(error[0].innerHTML != "") {
                if($(element).hasClass('reqsignature')) {
                    if(!$(element).hasClass('signed')) {
                        par.find('.signature-pad').addClass("invalid")
                    }
                } else {
                    par.addClass("invalid")
                    var warning_icon = par.append('<span class="input-group-text error-icon-container"><i class="material-symbols-rounded red error-icon" data-bs-toggle="tooltip" data-bs-html="true" title="'+error.contents().text()+'">warning</i></span>')
                    new bootstrap.Tooltip(warning_icon.find('.error-icon'));
                }
            } else {
                var par = element.parent()
                par.removeClass("invalid")
                par.find('invalid').removeClass("invalid")
            }
        },
        success: function (element) {
            // We do nothing but needs to be defined
        }
    });

  $.validator.addMethod("float", function(value, element) {
    return /^(-?([0-9]+)(\.[0-9]{0,2}0*)?)?$/.test(value);
  }, "The amount should be just numbers and maximum two decimal digits.");

  $.validator.addMethod("float_accurate", function(value, element) {
    return /^(-?([0-9]+)(\.[0-9]*)?)?$/.test(value);
  }, "The amount should be just numbers");

  $.validator.addMethod("float_not_zero", function(value, element) {
    return /^[-]?(?:[1-9]\d*|0(?!(?:\.0+)?$))?(?:\.\d+)?$/.test(value);
  }, "The amount should be just numbers except 0 and maximum two decimal digits.");

  $.validator.addMethod("latitude", function(value, element) {
    return /^(-?(([0-8]?[0-9])(\.[0-9]*)?)|90(\.0*)?)?$/.test(value);
  }, "Latitude should be just numbers and between -90 and 90.");

  $.validator.addMethod("longitude", function(value, element) {
    return /^(-?(((1[0-7]|[0-9])?[0-9])(\.[0-9]*)?)|180(\.0*)?)?$/.test(value);
  }, "Latitude should be just numbers and between -180 and 180.");

  $.validator.addMethod("negint", function(value, element) {
    return /^-?[0-9]*$/.test(value);
  }, "Only integer numbers (positive or negative).");

  $.validator.addMethod("positive", function(value, element) {
    return /^[+]?\d+([.]\d+)?$/.test(value);
  }, "Only positive numbers.");

  $.validator.addMethod("nospaces", function(value, element) {
    return value.indexOf(' ') == -1;
  }, "Spaces are not allowed.");

  $.validator.addMethod("datepicker", function(value, element) {
    return value || value === '';
  }, "Specify a valid date (e.g. 23 August 1988).");

  $.validator.addMethod("reqselect", function(value, element) {
    if ($(element).val() != '' && $(element).val() != undefined && $(element).val() != null) {
      return true;
    }
    return false;
  }, "Please choose a value.");

  $.validator.addMethod("regex", function(value, element) {
    var regex = $(element).data('regex-validate');

    if (regex) {
        var pattern = new RegExp(regex);
        return pattern.test(value);
    }
    return true;
}, "The value does not match the required pattern.");

  $.validator.addClassRules({
    'req': {
        required: true
    },
    'int': {
        digits: true,
        max: MAX_INT_AMOUNT
    },
    'negint': {
        negint: true
    },
    'url': {
      url: true
    },
    'float': {
      number: true,
      float: true,
      max: MAX_FLOAT_AMOUNT
    },
    'float_accurate': {
        number: true,
        float_accurate: true,
        max: MAX_FLOAT_AMOUNT
    },
    'float_not_zero': {
      number: true,
      float_not_zero: true,
      max: MAX_FLOAT_AMOUNT
    },
    'latitude': {
      number: true,
      latitude: true
    },
    'longitude': {
      number: true,
      longitude: true
    },
    'phone': {
      phoneTZ: true
    },
    'datepicker': {
      datepicker: true
    },
    'reqselect': {
      reqselect: true
    },
    'nospaces': {
      nospaces: true
    },
    'positive': {
      positive: true
    },
    'custom_id': {
      custom_id: true
    },
    'gps_location_field': {
      gps_location: true
    },
    'regex': {
      regex: true
    }
    
});

$('input.regex').on('keyup', function () {
    $(this).valid();
});

}

// ---- Pagination ---- //

objectToQueryString = function(obj) {
    var str = [];
    for (var p in obj)
        if (obj.hasOwnProperty(p)) {
        str.push(p + "=" + (obj[p] != null ? obj[p]: ''));
        }
    return str.join("&");
}

function changeQueryParameters(newValues, toggles = {}) {
    var pairs = window.location.search.replace("?","").split('&');
    if (Object.keys(newValues).filter(k => !['tab', 'page'].includes(k)).length > 0) {
        newValues['page'] = 1;
    }
    //newValues['yPos'] = window.pageYOffset;
    for (var i = 0; i < pairs.length; i++) {
        if(!pairs[i])
        continue;
        var pair = pairs[i].split('=');
        if (!(pair[0] in newValues)) newValues[pair[0]] = pair[1];
        else if (newValues[pair[0]] == pair[1] && pair[0] in toggles) newValues[pair[0]] = toggles[pair[0]];
    }
    window.location.search = objectToQueryString(newValues);
}

/* --- Form Processing --- */
function SubmitForm(this_button, submit_url, options) {
    options = options ? options : {};

    this_form = this_button.form;

    let form_data = {};
    if (this_form) {
        // Preprocess password inputs - Should be done before assigning form_data variable
        passwordFormPreprocessor(this_form);

        // Extract all fields that are not disabled or skipped
        disabled_fields = $([]);
        $(this_form.elements).each(function () {
            if ($(this).prop('disabled')) {
                disabled_fields.push(this);
            }
        });
        disabled_fields.prop('disabled', false);

        form_elems = $(this_form.elements).filter(":not(.skip):not(.hiddenform)").filter(function () {
            return $(this).parents('.hiddenform').length <= 0;
        });

        if ($(this_form).data('raw-field') != undefined) {
            form_data = JSON.parse(
                Object.values(form_elems)
                    .filter((x) => x.name == $(this_form).data('raw-field'))[0]
                    .value
            );
        } else {
            var serial_options = { useIntKeysAsArrayIndex: true };
            if ($(this_form).data('checkbox-false') === true) {
                $.extend(serial_options, { checkboxUncheckedValue: "false" });
            }
            form_data = form_elems.serializeJSON(serial_options);
        }

        disabled_fields.prop('disabled', true);
    }

    // Add extra data if needed
    if (options.extra_data) {
        for (var attrname in options.extra_data) {
            form_data[attrname] = options.extra_data[attrname];
        }
    }

    if (options.method === 'DELETE') {
        sendDataToAPI(form_data, submit_url, options);
        return;
    }

    if (!$(this_form).valid()) {
        error_toast(PaygOps_LNG["FORM_INCORRECT"], PaygOps_LNG["FORM_INCORRECT_TITLE"]);
        debug_log('form errors', $(this_form).validate()['errorList']);
        return;
    }

    $(this_button).addClass("disabled");
    showButtonSpinner(this_button);

    let signatures_to_upload = $(this_form).find('.signature-pad:not(.uploaded)');
    if (signatures_to_upload.length > 0) {
        uploadSignatureAndGetUUID(signatures_to_upload[0], () => SubmitForm(this_button, submit_url, options));
        return;
    }

    let pictures_to_upload = $(this_form).find('.picture-input:not(.uploaded)');
    if (pictures_to_upload.length > 0) {
        uploadPictureAndGetUUID(pictures_to_upload[0], '/files/upload/picture/', () => SubmitForm(this_button, submit_url, options));
        return;
    }

    options.submit_button = this_button;

    if (options.postprocess_data) {
        form_data = options.postprocess_data(form_data);
    }

    sendDataToAPI(form_data, submit_url, options);
}


function sendDataToAPI(form_data, submit_url, options){
    options = options ? options : {};
    var success_action = options.success_action ? options.success_action : 'reload';
    var error_action = options.error_action ? options.error_action : 'show_error';
    var success_message = options.success_message ? options.success_message : 'Success!';
    var method = options.method ? options.method : "POST";
    var bypassPrevention = options.bypassPrevention ? bypassPrevention : false;
    var transaction = options.transaction ? options.transaction : false;
    debug_log('DEBUG:','form_data', form_data, 'method', method, 'url', submit_url)
    var clean_url = PAYGAPIURL+"/api/v1"+submit_url;
    if (submit_url.includes("http://") || submit_url.includes("https://")) {
        clean_url = submit_url;
    }
    $.ajax({
        url: clean_url,
        method: method,
        data: JSON.stringify(form_data),
        contentType: "application/json",
        beforeSend: function(xhr) { 
            xhr.setRequestHeader("Authorization", "Bearer " + JWTKey); 
            xhr.setRequestHeader("PaygOpsApp", "Web");
        },
        success: function (result) {
            debug_log('DEBUG:','response', result)
            if(result && result.msg) {
                success_message = result.msg
            }
            if (transaction && !result.success) {
                error_toast('Something went wrong. DETAIL: '+result.human_answer, 'Error');
            } else if(success_action == 'reload') {
                if (bypassPrevention) GLOBAL_bypassLeavePrevention = true;
                success_toast(success_message);
                reloadPage();
            } else if(success_action == 'redirect') {
                if (bypassPrevention) GLOBAL_bypassLeavePrevention = true;
                success_toast(success_message);
                var redirect_url = options.redirect_url;
                if(options.redirect_append) {
                    redirect_url += result[options.redirect_append];
                }
                if(options.redirect_append_static) {
                    redirect_url += options.redirect_append_static;
                }
                window.location = redirect_url;
            } else if(success_action == 'message') {
                success_toast(success_message);
                if(options.submit_button) {
                    hideButtonSpinner(options.submit_button)
                }
            } else {
                success_action(result, options.callback_options)
                if(options.submit_button) {
                    hideButtonSpinner(options.submit_button)
                }
            }
        },
        error: function (result, ajaxOptions, thrownError) {
            debug_log('DEBUG:','response', result)
            if(options.submit_button) {
                $(options.submit_button).removeClass("disabled");
                hideButtonSpinner(options.submit_button)
            }
            if(error_action == 'show_error') {
                if (result.status == 400) {
                    error_toast($.parseJSON(result.responseText).error_message || result.responseJSON.error, 'Error');
                } else if (result.status == 401) {
                    var retrying = options.retrying ? options.retrying : false;
                    if(!retrying) {
                        options.retrying = true
                        debug_log('JWT Expired. Retrying...')
                        $.ajax({
                            url: '/login/refresh_jwt',
                            type: 'GET',
                            success: function(result){ 
                                JWTKey = result.jwt
                                sendDataToAPI(form_data, submit_url, options)
                            },
                            error: function(data) {
                                error_toast(PaygOps_LNG["LOGIN_EXPIRED"])
                            }
                        });
                    } else {
                        error_toast(PaygOps_LNG["LOGIN_EXPIRED"])
                    }
                } else if (result.status == 0) {
                    error_toast(PaygOps_LNG["CONNECTION_ISSUE"])
                } else {
                    console.log(result)
                    var err_message = null
                    if(result.responseJSON) {
                        err_message = result.responseJSON.error_message || result.responseJSON.error
                    }
                    if(err_message) {
                        error_toast(err_message)
                    } else {
                        error_toast(PaygOps_LNG["SOMETHING_WRONG"]+result.responseText, 'Error');
                    }
                }
            } else {
                error_action(result, options.callback_options)
            }
            // Optional per-call hook to run additional cleanup (e.g. hide custom loaders)
            if (typeof options.after_error === 'function') {
                options.after_error(result);
            }
        }
    });
}

function showButtonSpinner(this_button) {
    $(this_button).children(".btn-label").addClass('hide');
    $(this_button).children(".btn-label-icon").addClass('invisible');
    $(this_button).children(".btn-spinner").removeClass('hide');
}

function hideButtonSpinner(this_button) {
    $(this_button).children(".btn-label").removeClass('hide');
    $(this_button).children(".btn-label-icon").removeClass('invisible');
    $(this_button).children(".btn-spinner").addClass('hide');
}

/* Async HTML Loading */

function loadRemoteHTMLInElement(html_url, this_div, show_skeleton, in_card) {
    if(show_skeleton) {
        skeleton = '<div class="skeleton skeleton-text"></div><div class="skeleton skeleton-text"></div><div class="skeleton skeleton-text skeleton-footer"></div>'
        if(in_card) {
            skeleton = '<div class="col mb-4"><div class="card"><div class="card-body">'+skeleton+'</div></div></div>'
        } else {
            skeleton = '<div class="mx-4 my-4">'+skeleton+'</div>'
        }
        this_div.html(skeleton)
    }
    $.ajax({
        url: html_url,
        type: "GET",
        success: function (result) {
            this_div.html(result);
            refreshAllFormsElements();
        },
        error: function (xhr, ajaxOptions, thrownError) {
            this_div.html(xhr.status+' '+thrownError);
        }
    });
}

/* Add / Remove buttons */

function addRemoveAnswer(input_name, add) {
    // We get the button and data
    var data_div = $(escapeBrackets('#add_remove_'+input_name))
    var add_button = $(escapeBrackets('#add_'+input_name))
    var remove_button = $(escapeBrackets('#remove_'+input_name))
    var current = data_div.data('currentindex');
    var min = data_div.data('minanswers')-1 // We remove one because we deal with indexes
    var max = data_div.data('maxanswers')-1 // We remove one because we deal with indexes
    var last_answer = $(escapeBrackets('#input_'+input_name+'['+current+']'))
    console.log(last_answer);
    console.log('#input_'+input_name+'['+current+']');
    if(add) { 
        // We load the last input HTML into a variable
        deInitFormElements(); // We need to do that BEFORE cloning
        var new_input = last_answer.clone()
        new_input = new_input.wrap("<div>").parent().html()
        // We replace the content for the new index
        var new_index = current + 1 
        var last_name = input_name+'['+current+']'
        var new_name = input_name+'['+new_index+']'
        new_input = replaceAllInText(new_input, last_name, new_name)
        new_input = replaceAllInText(new_input, 'signed', '') // This is to reinit signatures
        // We insert and initialize the new elements
        last_answer.after(new_input)
        refreshAllFormsElements()
        // We update the new index
        current = new_index
    } else { 
        // We decrement counter and remove element 
        last_answer.remove()
        current -= 1
    }
    // We update the index
    data_div.data('currentindex', current)
    // We enable/disable the buttons
    if(current <= min) { remove_button.addClass('disabled'); } else { remove_button.removeClass('disabled'); }
    if(current >= max) { add_button.addClass('disabled'); } else { add_button.removeClass('disabled'); }
}

function escapeBrackets(input_name) {
    // We need escaping square brackets in names for jquery to find it
    return input_name.replace(/[[]/g,'\\[').replace(/]/g,'\\]');
}

/* ----- General Helpers ----- */

function replaceAllInText(text, old_value, new_value) {
    // Javascript trick because "replace()" only works for the first instance
    return text.split(old_value).join(new_value)
}

function refreshHiddenElements() {
    $('.hiddenform').each(function() {
        hideForm($(this))
    });
}

function hideForm(div) {
    if(div) {
        $(div).addClass('hiddenform')
        $(div).find('.reqselect').each(function() {
            $(this).addClass('ignore')
        });
        $(div).find('.flatpickr-input').each(function() {
            $(this).addClass('ignore')
        });
    }
}

function showForm(div) {
    if(div) {
        $(div).removeClass('hiddenform')
        $(div).find('.reqselect').each(function() {
            $(this).removeClass('ignore')
        });
        $(div).find('.flatpickr-input').each(function() {
            $(this).removeClass('ignore')
        });
        updateAutosize();
    }
}

function toggleFormVisibility(div) {
    if($(div).hasClass('hiddenform')) {
        showForm(div)
    } else {
        hideForm(div)
    }
}

function hideDiv(div) {
    if(div) {
        $(div).addClass('hide')
    }
}

function showDiv(div) {
    if(div) {
        $(div).removeClass('hide')
        updateAutosize();
    }
}

function toggleDivVisibility(div) {
    if($(div).hasClass('hide')) {
        showDiv(div)
    } else {
        hideDiv(div)
    }
}

function makeArrayIfNot(values) {
    return [].concat(values);
}

function checkBoxToggleForms(checkbox, shown_if_true, shown_if_false) {
    var checked = $(checkbox).is(":checked")
    var shown = shown_if_false
    var hidden = shown_if_true
    if(checked) {
        shown = shown_if_true
        hidden = shown_if_false
    }
    debug_log('Checkbox Toggle Value: ', checked, ' - Shown: ', shown, ' - Hidden: ', hidden)
    showForm(shown)
    hideForm(hidden)
    // We refresh in case there were imbricated classes
    refreshHiddenElements();
}

function checkBoxToggleDiv(checkbox, shown_if_true, shown_if_false) {
    console.log(checkbox)
    var checked = $(checkbox).is(":checked")
    var shown = shown_if_false
    var hidden = shown_if_true
    if(checked) {
        shown = shown_if_true
        hidden = shown_if_false
    }
    debug_log('Checkbox Toggle Value: ', checked, ' - Shown div: ', shown, ' - Hidden div: ', hidden)
    showDiv(shown)
    hideDiv(hidden)
}

function selectToggleFormsMap(select, attribute, value_map) {
    select = $(select)
    if (!select.is(':visible') && !select.hasClass("modal-select")) return
    var value = ''
    if(attribute != 'value') {
        value = select.find(':selected').data(attribute);
    } else {
        value = select.val();
    }
    debug_log('Select Toggle Value: ', value, ' - Map: ', value_map)
    // First all the hiding
    for (const key in value_map) {
        if (value_map.hasOwnProperty(key)) {
            if(key != value) {
                debug_log('Hiding: ', value_map[key])
                hideForm(value_map[key])
            }
        }
    }
    // Then all the showing
    for (const key in value_map) {
        if (value_map.hasOwnProperty(key)) {
            if(key == value) {
                debug_log('Showing: ', value_map[key])
                showForm(value_map[key])
            }
        }
    }
    // We refresh in case there were imbricated classes
    refreshHiddenElements();
}

function selectToggleForms(select, attribute, shown_if_true, shown_if_false) {
    var shown = shown_if_false
    var hidden = shown_if_true
    select = $(select)
    var value = ''
    if(attribute != 'value') {
        value = select.find(':selected').data(attribute);
    } else {
        value = select.val();
    }
    debug_log('Select Toggle Value: ', value, select)
    if(value) {
        shown = shown_if_true
        hidden = shown_if_false
    }
    showForm(shown)
    hideForm(hidden)
    // We refresh in case there were imbricated classes
    refreshHiddenElements();
}

function clearTextField(e) {
    $(e).parents('.input-group').find('input').val('').trigger('input');
}

/* ----- Custom Forms ----- */

function editForm(button_clicked, update=false, lead_id=null) {
    var card_div = $(button_clicked).closest('.custom-form-card')
    card_div.find('.form-buttons').addClass('hide') // We hide the buttons right away
    var content_holder = card_div.find('.form-content-holder')[0]
    var form_content = $(content_holder).find('.form-content')[0]
    var form_answer_id = $(form_content).data('formAnswerId')
    if(update) {
        var form_url = '/custom_forms/answers/'+form_answer_id+'/update'
    } else {
        var form_url = '/custom_forms/answers/'+form_answer_id+'/edit'
    }
    if(lead_id) {
        form_url += '?lead_id='+lead_id
    }
    var discussedTopicId = card_div.find('.form-buttons').data('discussed-topic-id');
    if (discussedTopicId) {
        form_url += (form_url.indexOf('?') === -1 ? '?' : '&') + 'discussed_topic_id=' + discussedTopicId;
    }
    $(content_holder).collapse('show') // We show the collapsible if it wasn't already open
    loadRemoteHTMLInElement(form_url, $(content_holder), true)
}

function customFormSubmitCallback(response, options) {
    var card_div = $(options.submit_button).closest('.card')
    var content_holder = card_div.find('.form-content-holder')[0]
    var view_form_url = '/custom_forms/answers/'+response.id+'/view'
    loadRemoteHTMLInElement(view_form_url, $(content_holder), true)
    card_div.find('.form-buttons').removeClass('hide') // We show the edit buttons at the end
    location.reload();
}


/* ----- Cookies ----- */

function setCookie(name, value, expiry_time_seconds) {
    document.cookie = name + "=" + (value || "")  + "; max-age=" + expiry_time_seconds + "; path=/";
}

function getCookie(name, default_if_empty) {
    var nameEQ = name + "=";
    var ca = document.cookie.split(';');
    for(var i=0;i < ca.length;i++) {
        var c = ca[i];
        while (c.charAt(0)==' ') c = c.substring(1,c.length);
        if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
    }
    return default_if_empty;
}

function deleteCookie(name) {   
    document.cookie = name +'=; expires=Thu, 01 Jan 1970 00:00:01 GMT; path=/';
}

/* ---- Copy to clipboard ---- */

function copyToClipboard(text, name) {
    navigator.permissions.query({ name: "clipboard-write" }).then((result) => {
        clipboardWrite(text, name)
    }, () => {
        console.log(PaygOps_LNG["FAILED_PERMISSION"])
        clipboardWrite(text, name)
    });
}

function clipboardWrite(text, name) {
    navigator.clipboard.writeText(text).then(() => {
        success_toast(name+PaygOps_LNG["COPIED_TO_CLIPBOARD"])
    }, () => {
        error_toast(PaygOps_LNG["COULD_NOT_COPY_TO_CLIPBOARD"])
    });
}

/* ---- Tabs ---- */
function initTabs() {
    // We set the correct tab (if any) from the page anchor
    var target = window.location.href.split('#');
    if(target) {
        $('button[data-bs-target="#'+target[1]+'"]').each(function() {
            $(this).click()
        })
    }
    // We make sure that the slug is set when selecting tab
    $('.tab-nav:not(.sub-tab)').each(function() {
        $(this).on('click', function() {
            var anchor = $(this).attr('aria-controls')
            window.location.href = '#'+anchor
        })
    })
}

/* ---- Modals ---- */
function refreshModals() {
    $('.active-modal').each(function() {
        $(this).removeClass('active-modal')
        showModal($(this));
    });
}


function showModal(modal_div) {
    var thisModal = bootstrap.Modal.getOrCreateInstance($(modal_div)[0])
    thisModal.show()
    updateAutosize();
}

function closeModal(modal_div) {
    var thisModal = bootstrap.Modal.getOrCreateInstance($(modal_div)[0])
    thisModal.hide()
}

/* ---- Logging ---- */
function debug_log() {
    if(DEBUG_MODE) {
        console.log(...arguments);
    }
}

/* ---- ScrollSpy ---- */
$(document).ready(function(){
    var sectionIds = $('.side-link');
    $(document).scroll(function(){
        sectionIds.each(function(){
            var container = $(this).attr('data-anchor');
            var containerOffset = $(container).offset().top;
            var containerHeight = $(container).outerHeight();
            var containerBottom = containerOffset + containerHeight;
            var scrollPosition = $(document).scrollTop();
            if(scrollPosition < containerBottom - 75 && scrollPosition >= containerOffset - 75){
                $(this).parent().addClass('active');
            } else{
                $(this).parent().removeClass('active');
            }
        });
    });
});

function scrollToElement(div_selector, callback_function) {
    var target = $(div_selector)
    $('html,body').animate({
        scrollTop: target.offset().top - 70 //offsets for fixed header
    }, {
        duration: 100,
        specialEasing: {
          width: "linear",
          height: "easeOutBounce"
        },
        complete: function() { setTimeout(callback_function, 1000) }
    });
}

function scrollToAnchor(target, latestAnchor) {
    scrollToElement(target, function () {
        if($(latestAnchor).hasClass('last-anchor')) {
            $(latestAnchor).parent().addClass('active');
            $('.side-link').each(function(){
                if(this != latestAnchor){
                    $(this).parent().removeClass('active')
                }
            })
        }
    })
}

function reloadPage() {
    // The "true" is a hack because Firefox does agressive caching
    // this prevents many issues, do not remove it. It's ignored by other browsers. 
    window.location.reload(true);
}


/* ---- Form Duplicating ---- */

function bigRandomNumber() {
    // Used to generate IDs to avoid ID clash
    return Math.floor(Math.random()*999999)
}

function cloneAndReplace(template, holder, replace_list) {
    deInitFormElements();
    var tem = $(template).clone()
    $(replace_list).each(function (i) {
        var item = replace_list[i];
        tem = $(tem).html().replace(item[0], item[1])
    })
    $(holder).append($(tem));
    refreshAllFormsElements();
}

function resetForm(form) {
    $(form).trigger('reset')
    $(form).find('.select_2').each(function () {
        $(this).val(null);
        $(this).trigger('change');
    });
}

function toggleChevron(chev) {
    chev = $(chev)
    if(chev.hasClass('card-collapsible')) {
        chev = $(chev.parent().parent().find('.toggle-icon')[0])
    }
    chev.toggleClass('up');
    if (chev.hasClass('up')) {
        chev.text('expand_less');
        updateAutosize();
    } else {
        chev.text('expand_more');
    }
}

function updateTooltip(elem, new_tooltip) {
    $(elem).tooltip('dispose');
    $(elem).attr('title', new_tooltip);
    $(elem).tooltip();
}

function parseDataAttributes(dataAttributes) {
    const parsedDataAttributes = {};
    for (const key in dataAttributes) {
        const value = dataAttributes[key];
        if (!isNaN(value) && value !== '') {
            parsedDataAttributes[key] = parseFloat(value); // Parse as float if it's a number
        } else if (value.toLowerCase() === 'true') {
            parsedDataAttributes[key] = true; // Convert to boolean if it's "true"
        } else if (value.toLowerCase() === 'false') {
            parsedDataAttributes[key] = false; // Convert to boolean if it's "false"
        } else {
            parsedDataAttributes[key] = value; // Keep it as string if not a number or boolean
        }
    }
    return parsedDataAttributes
}

function getSelectData(select_elem) {
    var dataset = $(select_elem).find(':selected')[0].dataset
    return parseDataAttributes(dataset)
}

function captureGPSLocation(button, inputID) {
    if (!navigator.geolocation) {
        toastr.error('GPS Location is not supported by your browser.') ;
        return;
    }

    navigator.geolocation.getCurrentPosition(
        (position) => {
            const { latitude, longitude } = position.coords;
           
            setGPSInputValues(inputID, 
                                latitude, 
                                longitude,
                                true);

            toastr.success('GPS Location captured') ;
        },
        (error) => {
            toastr.error(`Unable to capture GPS Location : ${error.message}`) ;
        }
    );
}


function update_gps_coordinates(input_elem) {
    const inputID = $(input_elem).attr("input-id");
    const value = $(input_elem).val().trim();
    const regex = /^-?\d+(\.\d+)?\s*,\s*-?\d+(\.\d+)?$/;
    if (regex.test(value)) {
        const [latitude, longitude] = value.split(',').map(coord => parseFloat(coord.trim()));
        setGPSInputValues(inputID, 
                            latitude, 
                            longitude, 
                            false);
        debug_log('GPS Coordinates updated: ', latitude, longitude)
    } else {
        error_toast('Invalid GPS format. Please use "longitude ; latitude" format.');
    }
}

function setGPSInputValues(inputID, latitude, longitude, fromDeviceGeoLocation=false) {
    const gpsLocationField = $(`.${inputID}_gps_location`);
    const latitudeField = $(`.${inputID}_lat`);
    const longitudeField = $(`.${inputID}_lon`);

    latitudeField[0].value = latitude;
    longitudeField[0].value = longitude;

    if(fromDeviceGeoLocation) {
        $(gpsLocationField[0]).val(`${latitude}, ${longitude}`);
        $(gpsLocationField[0]).valid();
    }
}

function openMapModal(id_clean) {
    activeGPSID = id_clean;
    showModal($('#select-location'));
    setTimeout(initGPSPickerMap, 500); // Delay to ensure modal is visible before initializing the map
}
  
function initGPSPickerMap() {
    refreshTooltips();
    navigator.geolocation.getCurrentPosition(
        (position) => {
            const { latitude, longitude } = position.coords;
            const initialPosition = { lat: latitude, lng: longitude };
            initGPSPickerMapFromLocation(initialPosition);
        },
        (error) => {
            initGPSPickerMapFromLocation({ lat: 37.7749, lng: -122.4194 });
        }
    );
}

function initGPSPickerMapFromLocation(initialPosition) {
    debug_log('Initializing GPS Picker Map from location: ', initialPosition)
    location_picker_map = new google.maps.Map(document.getElementById('location_picker_map'), {
        zoom: 14,
        center: initialPosition,
        mapTypeId: 'terrain'
    });

    location_picker_marker = new google.maps.Marker({
        position: initialPosition,
        map: location_picker_map,
        draggable: true,
    });

    location_picker_map.addListener('click', function (event) {
        const clickedLocation = event.latLng;
        location_picker_marker.setPosition(clickedLocation);
    });
}

function confirmGPSCoordinates() {
    const selectedPosition = location_picker_marker.getPosition();
    const lat = selectedPosition.lat().toFixed(6);
    const lng = selectedPosition.lng().toFixed(6);
    setGPSInputValues(activeGPSID, 
        lat, 
        lng, 
        true);
    $('#select-location').modal('hide');
}


// --- Functions for handling the camera
let currentFacingMode, currentPictureType, overlayContainer;

function openCameraOverlay(picture_type, fileInputId, picture_instructions) {
    // We set global variables
    currentPictureType = picture_type;
    // We reset the facing mode
    currentFacingMode = "environment";

    // Create the overlay container
    overlayContainer = document.createElement("div");
    overlayContainer.id = "camera-overlay";
    overlayContainer.style.position = "fixed";
    overlayContainer.style.top = "0";
    overlayContainer.style.left = "0";
    overlayContainer.style.width = "100vw";
    overlayContainer.style.height = "100vh";
    overlayContainer.style.backgroundColor = "rgba(0, 0, 0, 0.95)";
    overlayContainer.style.zIndex = "9999";
    overlayContainer.style.display = "flex";
    overlayContainer.style.alignItems = "center";
    overlayContainer.style.justifyContent = "center";
    
    // Add the camera container and video element
    overlayContainer.innerHTML = `
        <div id="camera-container" style="position: relative; width: 100%; max-width: 480px; height: auto;">
            <video id="video" autoplay style="width: 100%; height: auto;"></video>
            <div id="overlay-shape" style="position: absolute; pointer-events: none; border: 2px dashed red;"></div>
        </div>
        <div class="d-flex justify-content-center align-items-start" style="position: absolute; top: 10px; width: 80%;">
            <button class="btn btn-secondary w-100 picture-button" onclick="closeCameraOverlay()" style="max-width: 480px;">
                <i class="material-symbols-rounded inline-icon-small-button btn-label-icon">close</i> 
                <span class="btn-label">Close</span>
            </button>
        </div>
        <div class="d-flex justify-content-center align-items-end" style="position: absolute; bottom: 50px; width: 80%; max-width: 480px;">
            <button class="btn btn-success w-100 picture-button" onclick="captureAndSetImage('${fileInputId}')">
                <i class="material-symbols-rounded inline-icon-small-button btn-label-icon">photo_camera</i> 
                <span class="btn-label">Take Picture</span>
            </button>
            <button class="btn btn-secondary w-30 picture-button" onclick="switchCameraFacingMode()" style="max-width: 480px; margin-left: 10px;">
                <i class="material-symbols-rounded inline-icon-small-button btn-label-icon">cameraswitch</i> 
            </button>
        </div>
        ${picture_instructions ? `<div id="picture-instructions" style="position: absolute; bottom: 100px; width: 80%; color: white; text-align: center; font-size: 12px; border-radius: 10px; background-color: rgba(0, 0, 0, 0.5); padding: 10px; max-width: 480px;">${picture_instructions}</div>` : ''}
    `;
    document.body.appendChild(overlayContainer);
    
    // Start the camera and resize the overlay dynamically
    startCamera();
}

// Function to start the camera
function startCamera() {
    const video = document.getElementById("video");
    // we stop existing streams if any
    if (video.srcObject) {
        video.srcObject.getTracks().forEach(track => track.stop());
    }

    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({
                video:  { facingMode: { ideal: currentFacingMode } }
            })
            .then((stream) => {
                video.srcObject = stream;
                video.play();

                video.addEventListener("loadedmetadata", updateOverlayShape);
                window.addEventListener("resize", updateOverlayShape);
            })
            .catch((err) => {
                console.error("Error accessing camera: ", err.message);
                alert("Camera access is required to use this feature.");
            });
    } else {
        alert("Your browser does not support accessing the camera. Please use a modern browser.");
    }
}

// Function to set the overlay shape based on the picture type
function updateOverlayShape() {
    const video = document.getElementById("video");
    const overlayShape = document.getElementById("overlay-shape");
    // We first update the overall canvas just in case
    const maxWidth = window.innerWidth < 480 ? `${window.innerWidth}px` : '480px';
    const elementsToAdjust = document.querySelectorAll('#camera-container, .picture-button');
    elementsToAdjust.forEach(element => {
        element.style.maxWidth = maxWidth;
    });

    // We then go to update the overlay
    const videoWidth = video.offsetWidth;
    const videoHeight = video.offsetHeight;

    let shapeHeight, shapeWidth, aspectRatio;
    // Adjust shape based on picture type
    switch (currentPictureType) {
        case "face_picture":
            aspectRatio = (3 / 4);
            overlayShape.style.borderRadius = "50%";  // Oval shape
            break;
        case "id_credit_card_picture":
            aspectRatio = (16 / 10);  // 16:10 aspect ratio
            overlayShape.style.borderRadius = "0";  // Rectangle shape
            break;
        case "passport_picture":
            aspectRatio = (7 / 10);  // 7:10 aspect ratio
            overlayShape.style.borderRadius = "0";  // Rectangle shape
            break;
        case "a4_landscape_picture":
            aspectRatio = Math.sqrt(2);  // 1/sqrt(2) aspect ratio
            overlayShape.style.borderRadius = "0";  // Rectangle shape
            break;
        case "a4_portrait_picture":
            aspectRatio = (1 / Math.sqrt(2));  // 1/sqrt(2) aspect ratio
            overlayShape.style.borderRadius = "0";  // Rectangle shape
            break;
        case "":
            overlayShape.style.display = "none";
        default:
            aspectRatio = (3 / 4);  // Default 3:4 aspect ratio
            overlayShape.style.borderRadius = "50%";  // Oval shape
            break;
    }

    const clearanceFactor = 0.1;
    const maxOverlayWidth = videoWidth * (1 - clearanceFactor * 2);
    const maxOverlayHeight = videoHeight * (1 - clearanceFactor * 2);

    // Compare aspect ratio of video to overlay's aspect ratio
    if (videoWidth / videoHeight > aspectRatio) {
        // Video is wider than the overlay's aspect ratio
        shapeHeight = maxOverlayHeight;
        shapeWidth = shapeHeight * aspectRatio;
    } else {
        // Video is narrower than or matches the overlay's aspect ratio
        shapeWidth = maxOverlayWidth;
        shapeHeight = shapeWidth / aspectRatio;
    }

    overlayShape.style.height = `${shapeHeight}px`;
    overlayShape.style.width = `${shapeWidth}px`;
    overlayShape.style.top = `${(videoHeight - shapeHeight) / 2}px`;
    overlayShape.style.left = `${(videoWidth - shapeWidth) / 2}px`;
}

function switchCameraFacingMode() {
    currentFacingMode = currentFacingMode === "environment" ? "user" : "environment";
    startCamera();
}

// Function to capture the image and set it in the file input
function captureAndSetImage(fileInputId) {
    const video = document.getElementById("video");
    
    // Create a canvas element to capture the frame from the video
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");

    // Set canvas dimensions to match the video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    // Draw the video frame onto the canvas
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Convert the canvas image to a base64-encoded data URL
    const imageData = canvas.toDataURL("image/jpeg");

    // Convert base64 data to a Blob (for file-like behavior)
    const byteString = atob(imageData.split(',')[1]);
    const mimeString = imageData.split(',')[0].split(':')[1].split(';')[0];
    const arrayBuffer = new ArrayBuffer(byteString.length);
    const intArray = new Uint8Array(arrayBuffer);

    for (let i = 0; i < byteString.length; i++) {
        intArray[i] = byteString.charCodeAt(i);
    }

    const blob = new Blob([intArray], { type: mimeString });
    const file = new File([blob], "captured-image.jpg", { type: mimeString });

    // Find the file input element by its ID and set the captured image as its value
    const fileInput = document.getElementById(fileInputId);
    const dataTransfer = new DataTransfer();  // Required to simulate file input

    dataTransfer.items.add(file);
    fileInput.files = dataTransfer.files;

    // Optionally, trigger any change event if needed (e.g., for form submission)
    const changeEvent = new Event('change');
    fileInput.dispatchEvent(changeEvent);

    closeCameraOverlay(); // Optionally close the overlay after capture
}

// Function to close the camera overlay
function closeCameraOverlay() {
    const overlayContainer = document.getElementById("camera-overlay");
    const video = document.getElementById("video");
    if (overlayContainer) {
        document.body.removeChild(overlayContainer);
    }
    // Stop all media tracks to release the camera resource
    if (video.srcObject) {
        const stream = video.srcObject;
        const tracks = stream.getTracks();
        tracks.forEach(track => track.stop());  // Stop each track
        video.srcObject = null;  // Disconnect the stream from the video
    }
}

// Query parameters
function getQueryParam(param) {
    var urlParams = new URLSearchParams(window.location.search); 
    return urlParams.get(param);
}

function setQueryParam(param, value) {
    var url = new URL(window.location.href);

    url.searchParams.set(param, value);
    window.history.pushState({}, '', url);

    return url
}

function deleteQueryParam(param) {
    if(!getQueryParam(param)) {
        return
    }

    var url = new URL(window.location.href);

    url.searchParams.delete(param);
    window.history.replaceState({}, '', url);
    window.location.replace(url);
}

// Function to capture event
function captureEvent(event_name, event_data) {
    posthog.capture(event_name, event_data);
}

function getCurrentTime() {
    const now = new Date();
  
    let hours = now.getHours();
    let minutes = now.getMinutes();
  
    hours = hours < 10 ? '0' + hours : hours;
    minutes = minutes < 10 ? '0' + minutes : minutes;
  
    return `${hours}:${minutes}`;
  }

// Helper for checkboxes that apply request params true/false value and reload url on change event
function presetCheckBoxValueFromRequestParam(elementID, requestParamKey, callback) {
    let url = null;
    let value = getQueryParam(`${requestParamKey}`);
    let element = document.getElementById(`${elementID}`);

    if(!element) {
        return
    }

    if(callback) {
        callback(url, elementID, requestParamKey)
    }

   if(value == "true")  {
        url = setQueryParam(`${requestParamKey}`, "true");
        element.checked = true;
    } else if(value == "false") {
        url = setQueryParam(`${requestParamKey}`, "false");
        element.checked = false;
    }
}

function toggleAndReloadURLOnCheckboxValueChange(elementID, requestParamKey, callback, reloadPage=false, resetPage=false) {
    let url = null;
    let element = document.getElementById(`${elementID}`);

    if(!element) {
        return
    }

    let checked = element.checked;

    if(callback) {
        callback(url, elementID, requestParamKey);
    }

    if (checked) {
        url = setQueryParam(`${requestParamKey}`, "true");
    } else {
        url = setQueryParam(`${requestParamKey}`, "false");
    }

    // Reset page incase the page exceeds maximum pages possible
    if(resetPage && getQueryParam("page")) {
        url = setQueryParam("page", 1);
    }

    if(reloadPage) {
        window.location.href = url.toString();
        window.location.reload();
    }
}