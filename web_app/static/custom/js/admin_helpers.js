function addVariable(elem, callback) {
    var card = $(elem).parents('.template-badge-holder');
    var name = $(elem).clone().children().remove().end().text().trim();
    var variable = $(elem).attr('data-variable');
    var varChip = $('.templateVar .badge').clone();
    varChip.text(name);
    varChip.attr('data-variable', variable);
    tem = $(card).find('.template:not(.disabled)')
    tem.insertAtCaret(varChip);
    if(callback) {
        callback(tem)
    }
    copyTextToInput(tem);
    return false;
}

function triggerInput(tem) {
    $(tem).trigger('input')
}

function copyTextToInput(elem) {
    var input_field = $(elem).next()
    out = $(elem).clone()
    $(out).find('.badge').each(function () {
        vari = $(this).attr('data-variable');
        txt = '{'+vari+'}';  
        $(this).replaceWith(txt);
    })
    // Get the innerHTML instead of the text
    var input_raw = out.prop('innerHTML');
    // Replace &nbsp; with a space, <div> with an empty string, and <br> with a newline
    input_raw = input_raw.replace(/&nbsp;/g, ' ')  // Replace &nbsp; with a space
                         .replace(/<div[^>]*>/g, '') // Remove <div> tags
                         .replace(/<\/div>/g, '')    // Remove closing </div> tags
                         .replace(/<span[^>]*>/g, '') // Remove <span> tags
                         .replace(/<\/span>/g, '')    // Remove closing </span> tags
                         .replace(/<br\s*\/?>/g, '\n'); // Replace <br> with a newline
    input_field.val(input_raw)
    input_field.trigger('input')
}

function addCallback(tem) {
    validate(tem);
    preview(tem);
}

/* ---- Add at caret function ---- */
(function($) {
    function focus(target) {
        if (!document.activeElement || document.activeElement !== target) {
            target.focus();
        }
    }
  
    $.fn.caret = function(pos, node) {
        var target = this[0];
        if (arguments.length == 0) {
            //get
            if (target) {
                if (window.getSelection) {
                    focus(target);
                    var selection = window.getSelection();
                    var range1 = selection.getRangeAt(0),
                    range2 = range1.cloneRange();
                    node = range1.endContainer;
                    if (node.isSameNode(target)) {return [range1.endOffset, NaN]}
                    if (!range1.endContainer.isSameNode(target.firstChild)) {
                        range2.selectNodeContents(node);
                    } else {
                        range2.selectNodeContents(target);
                    }
                    range2.setEnd(range1.endContainer, range1.endOffset);
                    return [node, range2.toString().length];
                }
            }
            //not supported
            return;
        }
        //set
        if (target) {
            if (window.getSelection) {
                focus(target);
                window.getSelection().collapse(node, pos);
            }
        }
        return this;
    }
    $.fn.insertAtCaret = function(el) {
        [node, pos] = this.caret();
        if (!isNaN(pos)) { // the caret is in a text node
            parent = node.parentNode
            prestr =  node.textContent.substring(0, pos);
            poststr =  node.textContent.substring(pos);
            post = document.createTextNode(poststr);
            parent.replaceChild(post, node);
        } else { // the caret is the parent element
            parent = this[0];
            prestr = '';
            post = document.createTextNode('');
            parent.insertBefore(post, parent.childNodes[node]);
        }
        parent.insertBefore(el[0], post);
        if (prestr) parent.insertBefore(document.createTextNode(prestr), el[0]);
        this.caret(0, post);
        for (let i = 0; i < parent.childNodes.length; i++) {
            if (parent.childNodes[i].textContent == '') {
                parent.removeChild(parent.childNodes[i])
            }
        }
    }
  })(jQuery);