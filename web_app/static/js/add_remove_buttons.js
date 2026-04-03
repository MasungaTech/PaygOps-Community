/**
 * Created by benjamindavid on 11/08/2016.
 */
function updateAllButtons() {
    $(".removeAnswer").each(function (f) {
        var thisGroup = $(this).parent();
        var lastinput = thisGroup.find('input').last()[0];
        if (!lastinput) {
            lastinput = thisGroup.find('textarea').last()[0];
        }
        var qID = thisGroup.attr('data-qname');
        var filter_expression = new RegExp('(\\[' + qID + ']|' + qID + ')\\[(\\d+)\\]');
        var lastCount = parseInt((filter_expression).exec(lastinput.name)[2]);
        updateButtons(thisGroup, lastCount + 1);
    });
}

function updateButtons(group, currentcounter) {
    var minanswers = group.attr('data-minAnswers');
    var maxanswers = group.attr('data-maxAnswers');
    var addButton = group.find('.addAnswer');
    var removeButton = group.find('.removeAnswer');
    if (currentcounter <= minanswers || currentcounter <= 1) {
        removeButton.addClass('disabled');
    } else {
        removeButton.removeClass('disabled');
    }
    if (currentcounter >= maxanswers) {
        addButton.addClass('disabled');
    } else {
        addButton.removeClass('disabled');
    }
    refreshSelects();
    $('.datepicker').datepicker();
}


function setupNewCopy(copied, filter_expression, isMultiple) {
    var replacedName2;
    var currentcounter2;
    if (copied.name !== '') {
        var nameData = (filter_expression).exec(copied.name);
        currentcounter2 = parseInt(nameData[2]) + 1;
        replacedName2 = nameData[1] + '[' + currentcounter2 + ']';

        copied.name = copied.name.replace(filter_expression, replacedName2);
        copied.value = '';
        // If it's not a multiple then we remove the required tags on the question
        if (!isMultiple) {
            $(copied).removeClass("req");
        }
    }

    if (copied.id !== undefined) {
        copied.id = copied.id.replace(filter_expression, replacedName2);
    }

    return replacedName2, currentcounter2
}

function addFunctionsToButtons() {
    $(".removeAnswer").each(function (f) {
        $(this).unbind('click');
    });
    $(".addAnswer").each(function (f) {
        $(this).unbind('click');
    });

    $(".removeAnswer").on('click', function (f) {
        f.preventDefault();
        var group = $(this).parent();
        var qID = group.attr('data-qname');
        var filter_expression = new RegExp('(\\[' + qID + ']|' + qID + ')\\[(\\d+)\\]');
        var minanswers = group.attr('data-minAnswers');
        var thisGroup = group.children('.answerContainer').children(".answer:last");
        var lastinput = thisGroup.find('input')[0];
        if (!lastinput) {
            lastinput = thisGroup.find('textarea')[0];
        }
        if (!lastinput.name) {
            lastinput = thisGroup.find('input')[1];
        }
        if (!lastinput.name) {
            lastinput = thisGroup.find('input')[2];
        }
        var lastCount = (filter_expression).exec(lastinput.name)[2];
        var currentcounter = parseInt(lastCount) + 1;
        if (currentcounter > minanswers) {
            thisGroup.remove();
            updateButtons(group, currentcounter - 1);
        }
    });

    $(".addAnswer").on('click', function (f) {
        var group = $(this).parent();
        f.preventDefault();
        var isMultiple = group.attr('data-multiple');

        var qID = group.attr('data-qname');
        var filter_expression = new RegExp('(\\[' + qID + ']|' + qID + ')\\[(\\d+)\\]');
        var maxanswers = group.attr('data-maxAnswers');
        var currentcounter;
        var replacedName;
        var lastChild = group.children('.answerContainer').children(".answer:last");

        lastChild.find('select').each(function () {
            var selectInstance = M.FormSelect.getInstance(this);
            if(selectInstance !== undefined) {
                selectInstance.destroy();
            }
            if ($(this).hasClass('select_2')) {
                try {
                    $(this).select2('destroy');
                }
                catch(err) {
                    console.log('select not init');
                }
            }
        });

        var thisClone = lastChild.clone(true);

        thisClone.find('.card').remove()

        // If it's a multiple we remove the * on the title
        if (isMultiple) {
            thisClone.find('h5').each(function () {
                $(this).html($(this).html().replace('*', ''));
            }).end();
        }
        thisClone.find('input').each(function () {
            replacedName, currentcounter = setupNewCopy(this, filter_expression, isMultiple);
        }).end();
        thisClone.find('textarea').each(function () {
            replacedName, currentcounter = setupNewCopy(this, filter_expression, isMultiple);
        }).end();

        thisClone.find('label').each(function () {
            // If it's not a multiple then we remove the * on the question
            if (!isMultiple) {
                $(this).html($(this).html().replace('*', ''));
            }
            if ($(this).attr('for') !== undefined) {
                $(this).attr('for', $(this).attr('for').replace(filter_expression, replacedName));
            }
        }).end();

        thisClone.find('select').each(function () {
            if (this.name !== '') {
                var nameData = (filter_expression).exec(this.name);
                currentcounter = parseInt(nameData[2]) + 1;
                replacedName = nameData[1] + '[' + currentcounter + ']';

                this.name = this.name.replace(filter_expression, replacedName);
                this.value = '';
                // If it's not a multiple then we remove the required tags on the question
                if (!isMultiple) {
                    $(this).removeClass("req");
                }
            }

            if (this.id !== undefined) {
                this.id = this.id.replace(filter_expression, replacedName);
            }
        }).end();

        if (currentcounter < maxanswers) {
            thisClone.appendTo(group.children('.answerContainer'));
            updateButtons(group, currentcounter + 1);
        }
    });
    updateAllButtons();
}

$(document).ready(function () {
    addFunctionsToButtons();
});
