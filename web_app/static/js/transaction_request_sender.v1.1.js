function submitTransactionRequestAndGetAnswer(json_data, request_url, thisUUID, return_function) {
        var URL = PAYGAPIURL+request_url+thisUUID;
        $.ajax({
            url: URL,
            type: "POST",
            data: json_data,
            contentType: "application/json",
            beforeSend: function(xhr) { xhr.setRequestHeader("Authorization", "Bearer "+JWTKey); },
            success: function (result) {
                getHumanAnswer(request_url, thisUUID, return_function);
            },
            error: function (xhr, ajaxOptions, error) {
                return_function('An error occured. Detail: '+JSON.parse(xhr.responseText).error_message);
            }
        });
 }

function getHumanAnswer(request_url, thisUUID, return_function) {
     var URL = PAYGAPIURL+request_url+thisUUID+"?human_answer=True";
     var transaction_route = request_url+thisUUID
     $.ajax({
            url: URL,
            type: "GET",
            beforeSend: function(xhr) { xhr.setRequestHeader("Authorization", "Bearer "+JWTKey); },
            success: function (result) {
                var show_send_sms = result.client_answer.length > 0 && result.human_answer != ''
                if (result.success) return_function(result.human_answer || 'Done!', show_send_sms, transaction_route)
                else return_function(result.human_answer)
            },
            error: function (xhr, ajaxOptions, error) {
                return_function('An error occured. Detail: '+JSON.parse(xhr.responseText).error_message);
            }
     });
}

function sendAnswerToClient(transaction_route) {
    showLoadingTransaction()
    var URL = PAYGAPIURL+transaction_route;
    $.ajax({
        url: URL,
        type: "PUT",
        data: JSON.stringify({'sent_to_client': true}),
        contentType: "application/json",
        beforeSend: function(xhr) { xhr.setRequestHeader("Authorization", "Bearer "+JWTKey); },
        success: function (result) {
            msg = result.success ? 'The following SMS was sent: ' + result.sent_to_client.Body : 'No message to sent to the client (it might be disabled in custom SMS).' ;
            return_function(msg);
        },
        error: function (xhr, ajaxOptions, error) {
            var details = 'Unkown error'
            console.log(xhr)
            try {
                details = xhr.responseJSON.message ? xhr.responseJSON.message : JSON.parse(xhr.responseText).error_message
            }
            catch(err) {
                if (xhr.status != 0) details = xhr.status+" "+xhr.statusText
            }
            return_function('An error occured. Detail: '+details);
        }
    });
}
