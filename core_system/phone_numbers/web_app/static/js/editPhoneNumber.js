function updatePhoneOwner(){
    newPersonId = $('#person-list').val();
    if (newPersonId){
        sendUpdate(newPersonId);
    }
}

function sendUpdate(number){
    $.ajax({
        url: "",
        type: "POST",
        data: JSON.stringify({number: number}),
        dataType: "json"
    });
}