var upload_callback = null;

/* ----- Picture Specific ----- */

var picture_uuid_input = null;
var picture_input = null;

function uploadPictureAndGetUUID(file_input, upload_route, callback_function) {
    upload_callback = callback_function;
    if ( !( window.File && window.FileReader && window.FileList && window.Blob ) ) {
        toast(PaygOps_LNG["PICTURE_UPLOAD_NOT_SUPPORTED"]);
        return false;
    }
    picture_input = file_input;
    picture_uuid_input = $(file_input).parent('div:first').parent('div:first').find('.picture-uploader-input');
    if(file_input.files.length > 0) {
        $(picture_input).removeClass('uploaded');
        processPictureUpload(file_input.files, upload_route);
    } else {
        $(picture_input).addClass('uploaded');
        if(upload_callback) {
            upload_callback();
        }
    }
}

function processPictureUpload(files, uploadRoute){
    var ext = files[0].name.substr(files[0].name.lastIndexOf('.')+1).toLowerCase();
    var QUALITY = 65;
    var MAX_LENGTH = 1536;
    if(ext == 'jpg' || ext == 'jpeg' || ext == 'png' || ext == 'gif' || ext == 'tiff') {
        var reader = new FileReader();
        reader.readAsArrayBuffer(files[0]);
        reader.onload = function (event) {
            var blob = new Blob([event.target.result]);
            window.URL = window.URL || window.webkitURL;
            var blobURL = window.URL.createObjectURL(blob);
            var image = new Image();
            image.src = blobURL;

            image.onload = function () {
                var outputExt = 'jpg';
                var base = jic.compress(image, QUALITY, outputExt, MAX_LENGTH).src;
                if(ext == 'jpg' || ext == 'jpeg'){
                    var origBase64 = 'data:image/jpeg;base64,' + ExifRestorer.encode64(new Uint8Array(event.target.result));
                    base = ExifRestorer.restore(origBase64, base);
                } else{
                    base = base.replace("data:image/jpeg;base64,", "");
                }
                jic.upload(base,
                    uploadRoute,
                    'pic',
                    files[0].name+'.'+outputExt,
                    pictureUploadSuccess,
                    uploadError,
                    uploadProgress
                );
            }
        }
    } else {
        toast(PaygOps_LNG["INVALID_IMAGE_FORMAT"]);
    }
}

/* ----- Signature Specific ----- */

var signature_uuid_input = null;
var signature_pad = null;

function uploadSignatureAndGetUUID(signaturePad, callback_function) {
    upload_callback = callback_function;
    signature_pad = signaturePad;
    signature_uuid_input = $(signature_pad).parent('div:first').parent('div:first').find('.signature-uploader-input');
    processSignatureUpload();
}

function processSignatureUpload() {
    if ($(signature_pad).hasClass('disabled') || signature_pad.signaturePad.isEmpty()) {
        $(signature_pad).addClass('uploaded');
        if(upload_callback) {
            upload_callback();
        }
        return
    }
    jic.upload(
        signature_pad.signaturePad.toDataURL("image/jpeg", 1).split(',')[1],
        '/files/upload/picture/',
        'pic',
        'signature.jpg',
        signatureUploadSuccess,
        uploadError,
        uploadProgress
    );
}

function clearSignaturePad(clear_button) {
    let pad = $(clear_button).parent('div:first').find('.signature-pad')[0];
    pad.signaturePad.clear();
    let pad_input = getSignatureInputFromPad(pad);
    pad_input.val('').change();
    pad_input.triggerHandler('input')
    var preview = $(pad).parent('div:first').find('.signature-pad-value')[0]
    if(preview) {
        $(preview).addClass('hide')
    }
    $(pad).removeClass('hide')
    resizeCanvas();
}

function clearPicture(clear_button) {
    let pad_input = $(clear_button).parent('div:first').parent('div:first').find('.picture-uploader-input')[0];
    $(pad_input).val('').change();
    $(clear_button).parent('div:first').find('.picture-existing').remove();
}


/* ----- Shared ----- */

function pictureUploadSuccess(response){
    $('.toast').remove();
    picture_uuid_input.val(response);
    $(picture_input).addClass('uploaded');
    var picture_preview = $(picture_input).parent().find('.picture-existing').remove()
    picture_preview = $(picture_input).after('<div class="input-group-text picture-existing"><i class="material-symbols-rounded" data-bs-toggle="tooltip" data-bs-html="true" title="" data-bs-original-title="<img src=&quot;/files/pictures/'+response+'.jpg&quot; class=&quot;picture-tooltip&quot;>">visibility</i></div><div class="input-group-text picture-existing" onclick="clearPicture(this);"><i class="material-symbols-rounded" data-bs-toggle="tooltip" data-bs-html="true" title="" data-bs-original-title="'+PaygOps_LNG["DELETE_PICTURE"]+'">delete</i></div>')
    refreshTooltips();
    success_toast(PaygOps_LNG["PICTURE_SUCCESS"])
    if(upload_callback) {
        upload_callback();
    }
};

function signatureUploadSuccess(response){
    $('.toast').remove();
    signature_uuid_input.val(response);
    $(signature_pad).addClass('uploaded');
    success_toast(PaygOps_LNG["SIGNATURE_SUCCESS"])
    if(upload_callback) {
        upload_callback();
    }
};

function uploadError(response){
    $('.toast').remove()
    error_toast(PaygOps_LNG["UPLOAD_FAILED"]);
};

function uploadProgress(progress){
    $('.toast').remove()
    let progressPercentage = progress.toFixed(0);
    toast(PaygOps_LNG["UPLOADING_PHOTO"] + " " + progressPercentage + "%")
};