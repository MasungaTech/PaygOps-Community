function filter_paste(event) {
    const sel = window.getSelection();
    if (!sel.rangeCount) return false;
    sel.deleteFromDocument();
    sel.getRangeAt(0).insertNode(document.createTextNode(event.clipboardData.getData('text/plain')));
    event.preventDefault();
}

function filterControlChars(text) {
    return text.replaceAll(/[\u0009\u00A0]/g, '\u0020').replaceAll(/[\u0000-\u0008\u000e-\u001a\u001c-\u001f]/g, "").replaceAll(/[\u000b\u000c]/g, '\u000a');
}

function updateCounter(container, txt) {
    txt = filterControlChars(txt);
    var count = SmsCounter.count(txt)
    $(container).find('.charcount-wrapper .charcount').text(count.length);
    $(container).find('.charcount-wrapper .smscount').text(count.messages);
    $(container).find('.charcount-wrapper .warning').addClass('hide')
    if (count.encoding == 'UTF16') {
        $(container).find('.charcount-wrapper .warning').removeClass('hide')
    }
}