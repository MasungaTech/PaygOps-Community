// Icon picker data source handler

var IconPickerData = null;
var transformedIcons = null;

function formatIcon(icon) {
    return '<i class="material-symbols-rounded black-text tiny">' + icon + '</i> <span>' + icon.replaceAll('_', ' ') + '</span>';
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

$(document).ready(function() {
    // Initialize icon picker data source
    $.fn.select2.amd.require(['select2/data/array', 'select2/utils'], function(ArrayData, Utils) {
        IconPickerData = function($element, options) {
            IconPickerData.__super__.constructor.call(this, $element, options);
        };

        Utils.Extend(IconPickerData, ArrayData);

        IconPickerData.prototype.query = debounce(function(params, callback) {
            var data = {
                results: []
            };

            if (!window.ICON_PICKER_DATA) {
                console.error('ICON_PICKER_DATA not initialized');
                callback(data);
                return;
            }

            // Cache transformed icons if not already done
            if (!transformedIcons) {
                transformedIcons = window.ICON_PICKER_DATA.map(function(icon) {
                    return {
                        id: icon,
                        text: formatIcon(icon)
                    };
                });
            }

            if (params.term) {
                var term = params.term.toLowerCase().replaceAll(' ', '_');
                data.results = transformedIcons
                    .filter(function(item) {
                        return item.id.includes(term);
                    });
            } else {
                data.results = transformedIcons
            }
            callback(data);
        }, 150); // Debounce search for 150ms

        // Register the data adapter
        $.fn.select2.amd.define('IconPickerData', ['select2/data/array', 'select2/utils'], function(ArrayData, Utils) {
            return IconPickerData;
        });
    });
}); 

function initIconPicker($select){
    var initialValue = $select.data('initial-value');
    // Wait for ICON_PICKER_DATA to be available
    var checkIconPickerData = setInterval(function() {
        if (window.ICON_PICKER_DATA) {
            clearInterval(checkIconPickerData);
            
            // Initialize select2 with icon picker data source
            $select.select2({
                dataAdapter: $.fn.select2.amd.require('IconPickerData'),
                escapeMarkup: function(markup) {
                    return markup;
                },
                dropdownParent: $select.parent(),
                minimumInputLength: 0,
                maximumInputLength: 50
            });

            // Set initial value if provided
            if (initialValue) {
                // Create a properly formatted option for the initial value
                var formattedOption = new Option(formatIcon(initialValue), initialValue, true, true);
                $select.append(formattedOption);
                $select.trigger('change');
            }
        }
    }, 100);

    // Clear interval after 5 seconds to prevent infinite checking
    setTimeout(function() {
        clearInterval(checkIconPickerData);
    }, 5000);
}