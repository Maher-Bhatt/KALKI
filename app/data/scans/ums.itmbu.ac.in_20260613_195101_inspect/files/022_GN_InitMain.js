/* https://ums.itmbu.ac.in/Default/JS/GN_InitMain.js  (HTTP 200, application/javascript) */


var ComponentsDateTimePickers = function () {

    var handleDatePickers = function () {

        if (jQuery().datepicker) {

            //var StartingBirthDate = new Date();
            //StartingBirthDate.setDate(StartingBirthDate.getDate() - 5110);
            //var StartingBirthDateStr = StartingBirthDate.getDate() + "-" + StartingBirthDate.getMonth() + "-" + StartingBirthDate.getFullYear()

            $('.date-picker-first-date').datepicker({
                beforeShowDay: function (d) {
                    if (d.getDate() === 1) {
                        return true;
                    }
                    return false;
                },
                rtl: App.isRTL(),
                //orientation: "left",
                //orientation: "top auto
                orientation: "auto",
                autoclose: true,
                todayHighlight: true,
                pickerPosition: (App.isRTL() ? "bottom-right" : "bottom-left"),
                todayBtn: 'linked'

            });

            $('.date-picker-student-birthdate').datepicker({
                startDate: "01-01-1900",
                endDate: "-14y",
                autoclose: true,
                todayHighlight: true,
                orientation: "auto"

            });
            $('.date-picker-staff-birthdate').datepicker({
                startDate: "01-01-1900",
                endDate: "-15y",
                autoclose: true,
                todayHighlight: true,
                todayBtn: 'linked',
                orientation: "auto"
            });

            $('.date-picker').datepicker({
                rtl: App.isRTL(),
                //orientation: "left",
                //orientation: "top auto",
                orientation: "auto",
                autoclose: true,
                todayHighlight: true,
                pickerPosition: (App.isRTL() ? "bottom-right" : "bottom-left"),
                todayBtn: 'linked'
                //widgetPositioning: {
                //    horizontal: 'auto',
                //    vertical: 'auto'
                //}
            });

            $('.date-picker-nofuture').datepicker({
                startDate: "01-01-1900",
                endDate: "new date()",
                autoclose: true,
                todayHighlight: true,
                todayBtn: 'linked',
                orientation: "auto"
            });



            $('.date-picker-nopastdate').datepicker({
                startDate: "new date()",
                todayHighlight: true,
                todayBtn: 'linked',
                orientation: "auto"
            });
            //$('body').removeClass("modal-open"); // fix bug when inline picker is used in modal
        }

        /* Workaround to restrict daterange past date select: http://stackoverflow.com/questions/11933173/how-to-restrict-the-selectable-date-ranges-in-bootstrap-datepicker */

        // Workaround to fix datepicker position on window scroll
        $(document).scroll(function () {
            $('#form_modal2 .date-picker').datepicker('place'); //#modal is the id of the modal
        });
    }

    var handleTimePickers = function () {

        if (jQuery().timepicker) {
            $('.timepicker-default').timepicker({
                autoclose: true,
                showSeconds: true,
                minuteStep: 1
            });

            $('.timepicker-no-seconds').timepicker({
                autoclose: true,
                minuteStep: 5,
                defaultTime: null
            });

            $('.timepicker-24').timepicker({
                autoclose: true,
                minuteStep: 5,
                showSeconds: false,
                showMeridian: false
            });

            // handle input group button click
            $('.timepicker').parent('.input-group').on('click', '.input-group-btn', function (e) {
                e.preventDefault();
                $(this).parent('.input-group').find('.timepicker').timepicker('showWidget');
            });

            // Workaround to fix timepicker position on window scroll
            $(document).scroll(function () {
                $('#form_modal4 .timepicker-default, #form_modal4 .timepicker-no-seconds, #form_modal4 .timepicker-24').timepicker('place'); //#modal is the id of the modal
            });
        }
    }


    var handleDatetimePicker = function () {

        if (!jQuery().datetimepicker) {
            return;
        }

        $('.datetime-picker-nopastdate').datetimepicker({
            startDate: "new date()",
            todayHighlight: true,
            todayBtn: 'linked',
            isRTL: App.isRTL(),
            format: "dd-mm-yyyy HH:ii P",
            autoclose: true,
            showMeridian: false,
            fontAwesome: true,
            pickerPosition: (App.isRTL() ? "bottom-right" : "bottom-left"),
            todayBtn: true,
            todayHighlight: true
        });

        $(".form_meridian_datetime").datetimepicker({
            isRTL: App.isRTL(),
            format: "dd-mm-yyyy HH:ii P",
            autoclose: true,
            showMeridian: false,
            fontAwesome: true,
            pickerPosition: (App.isRTL() ? "bottom-right" : "bottom-left"),
            todayBtn: true,
            todayHighlight: true
        });

        $('body').removeClass("modal-open"); // fix bug when inline picker is used in modal

        // Workaround to fix datetimepicker position on window scroll
        $(document).scroll(function () {
            $('#form_modal1 .form_datetime, #form_modal1 .form_advance_datetime, #form_modal1 .form_meridian_datetime').datetimepicker('place'); //#modal is the id of the modal
        });


    }

    return {
        //main function to initiate the module
        init: function () {
            handleDatePickers();
            handleTimePickers();
            handleDatetimePicker();
        }
    };

}();


var InitMain = function () {
    return {
        //main function to initiate the module
        init: function () {
            $('[class*=GNMultiSelectDropDown]').multiselect({
                onDropdownShown: function (event) {
                    $('[class*=GNMultiSelectDropDown]').parent().find("button.multiselect-clear-filter").click();
                    $('[class*=GNMultiSelectDropDown]').parent().find("input[type='text'].multiselect-search").focus();
                },
                buttonClass: 'form-control',
                buttonWidth: "100%",
                maxHeight: 300,
                widthSynchronizationMode: 'always',
                enableFiltering: true,
                includeFilterClearBtn: true,
                includeSelectAllOption: true,
                enableCaseInsensitiveFiltering: true,
                nonSelectedText: 'Select One',
            });

            UI_Select2.init();



            UI_TinyMCE.init();
            ComponentsDateTimePickers.init();

            $(function () {
                $('[data-toggle="tooltip"]').tooltip()
            })

            $(document).ready(function () {
                $(".date-picker input").attr("autocomplete", "off");
            });

            $(".page-header .page-header-menu .hor-menu .navbar-nav>li>a").on("click", function () {
                if ($(this).parent().hasClass("classic-menu-dropdown")) {
                    if ($(this).parent().hasClass("open opened")) {
                        $(".classic-menu-dropdown").removeClass("open opened");
                        $(".dropdown-submenu").removeClass("open opened");
                        $(this).parent().removeClass("open opened");
                    }
                    else {
                        $(".classic-menu-dropdown").removeClass("open opened");
                        $(".dropdown-submenu").removeClass("open opened");
                        $(this).parent().addClass("open opened");
                    }
                }
            });

            $(".page-header .page-header-menu .hor-menu .navbar-nav>li>ul>li>a").on("click", function () {
                if ($(this).parent().hasClass("open opened")) {
                    $(".dropdown-submenu").removeClass("open opened");
                    $(this).parent().removeClass("open opened");
                }
                else {
                    $(".dropdown-submenu").removeClass("open opened");
                    $(this).parent().addClass("open opened");
                }
            });


            $('.popovers').popover();

            // Aadhar No Validation By Keyur
            $(document).ready(function () {

                //document.onkeydown = function (e) {
                //    if (event.keyCode == 123) {
                //        return false;
                //    }
                //    if (e.ctrlKey && e.shiftKey && e.keyCode == 'I'.charCodeAt(0)) {
                //        return false;
                //    }
                //    if (e.ctrlKey && e.shiftKey && e.keyCode == 'C'.charCodeAt(0)) {
                //        return false;
                //    }
                //    if (e.ctrlKey && e.shiftKey && e.keyCode == 'J'.charCodeAt(0)) {
                //        return false;
                //    }
                //    if (e.ctrlKey && e.keyCode == 'U'.charCodeAt(0)) {
                //        return false;
                //    }
                //}

                //var currentHtmlContent;
                //var element = new Image();
                //var elementWithHiddenContent = document.querySelector(".HiddenFieldHide");
                //var innerHtml = elementWithHiddenContent.innerHTML;

                //element.__defineGetter__("id", function () {
                //    currentHtmlContent = "";
                //});

                //setInterval(function () {
                //    currentHtmlContent = innerHtml;
                //    console.log(element);
                //    console.clear();
                //    elementWithHiddenContent.innerHTML = currentHtmlContent;
                //}, 1000);

                var AadharNo;
                var LeftPart;
                $(".GNAadharNo").keydown(function (event) {
                    var txtCurrentControl = $(this);

                    if (txtCurrentControl.val().length == 4 && event.keyCode != 8) {
                        AadharNo = txtCurrentControl.val().slice(0, 4);
                        AadharNo += " ";
                        txtCurrentControl.val(AadharNo);
                    }


                    if (txtCurrentControl.val().length == 9 && event.keyCode != 8) {
                        LeftPart = txtCurrentControl.val().slice(0, 5);
                        AadharNo = txtCurrentControl.val().slice(5, 9);
                        AadharNo += " ";
                        AadharNo = LeftPart + AadharNo;
                        txtCurrentControl.val(AadharNo);
                    }
                });
            });

            //Email Validation
            $(".GNTextbox_Email").keyup(function (event) {
                $(this).val($(this).val().trim().replace("/\r?\n|\r/", "").replace(/ /g, ''));
                //$(".GNTextbox_Email").val($(".GNTextbox_Email").val().trim().replace("/\r?\n|\r/", "").replace(/ /g, ''));
            });

            //PCT Calculation - Dynamic Fields
            $('[class*="CalculateFrom"]').keyup(function () {
                var Multiplier = 0;
                var Divider = 0;
                var String = $(this).attr('class').replace('form-control ', '');
                var Index = String.substring(String.lastIndexOf('_') + 1);
                var GroupIdentifier = String.substr(0, String.indexOf('_'));
                if ($("." + GroupIdentifier + "_CalculateFrom_Multiplier_" + Index).val() != '')
                    Multiplier = $("." + GroupIdentifier + "_CalculateFrom_Multiplier_" + Index).val();

                if ($("." + GroupIdentifier + "_CalculateFrom_Divider_" + Index).val() != '')
                    Divider = $("." + GroupIdentifier + "_CalculateFrom_Divider_" + Index).val();

                if (parseFloat(Divider) > 0) {
                    var Percentage = ((parseFloat('100.00').toFixed(2) * parseFloat(Multiplier).toFixed(2)) / parseFloat(Divider).toFixed(2));
                    $("." + GroupIdentifier + "_CalculateTo_" + Index).val(parseFloat(Percentage).toFixed(2));
                }

            });

            $('[class*="CalculateFrom"]').change(function () {
                var Multiplier = 0;
                var Divider = 0;
                var String = $(this).attr('class').replace('form-control ', '');
                var Index = String.substring(String.lastIndexOf('_') + 1);
                var GroupIdentifier = String.substr(0, String.indexOf('_'));
                if ($("." + GroupIdentifier + "_CalculateFrom_Multiplier_" + Index).val() != '')
                    Multiplier = $("." + GroupIdentifier + "_CalculateFrom_Multiplier_" + Index).val();

                if ($("." + GroupIdentifier + "_CalculateFrom_Divider_" + Index).val() != '')
                    Divider = $("." + GroupIdentifier + "_CalculateFrom_Divider_" + Index).val();

                if (parseFloat(Multiplier) > parseFloat(Divider)) {
                    $("." + GroupIdentifier + "_CalculateFrom_Multiplier_" + Index).focus();
                    $("." + GroupIdentifier + "_CalculateFrom_Multiplier_" + Index).next().remove();
                    $("." + GroupIdentifier + "_CalculateFrom_Multiplier_" + Index).after("<span class='spaninvalidValidationClass' style='color:red'>" + $("." + GroupIdentifier + "_CalculateFrom_Multiplier_" + Index).prev().text().trim().replace("*", "") + " must be less than or equal to " + $("." + GroupIdentifier + "_CalculateFrom_Divider_" + Index).prev().text().trim().replace("*", "") + "</span>");
                }
                else {
                    $("." + GroupIdentifier + "_CalculateFrom_Multiplier_" + Index).next().remove();
                }
            });

            $(document).click(function () {
                if ($(".spaninvalidValidationClass").length > 0) {
                    return false;
                }
                else
                    return true;
            });

            /* To Select Option On Tab in Select2 */

            $("body").on('select2:closing', function (e) {
                // save in case we want it
                var $sel2 = $(e.target).data("select2");
                var $sel = $sel2.$element;
                var $selDropdown = $sel2.$results.find(".select2-results__option--highlighted")
                var newValue = $selDropdown.data("data").element.value;

                // must be closed by a mouse or keyboard - listen when that event is finished
                // this must fire once and only once for every possible menu close 
                // otherwise the handler will be sitting around with unintended side affects
                $("html").once('keyup mouseup', function (e) {

                    // if close was due to a tab, use the highlighted value
                    //var KEYS = { UP: 38, DOWN: 40, TAB: 9, ENTER: 13 }
                    //if (e.keyCode === KEYS.TAB || e.keyCode === KEYS.ENTER) {
                    //    if (newValue != undefined) {
                    //        $sel.val(newValue);
                    //        $sel.trigger('change');
                    //        $sel.focus();
                    //    }
                    //}

                });

            });

            $.fn.once = function (events, callback) {
                return this.each(function () {
                    $(this).on(events, myCallback);
                    function myCallback(e) {
                        $(this).off(events, myCallback);
                        callback.call(this, e);
                    }
                });
            };

            /* To Select Option On Tab in Select2 */

            //$('[data-toggle="tooltip"]').click(function () {
            //    $('[data-toggle="tooltip"]').tooltip("hide");

            //});

            //Don't allow to open disable select dropdown on tab 
            $(document).on('select2:opening.disabled', ':disabled', function () { return false; })


            /* To restrict scroll of whole screen while scrolling a div */

            function hasVerticalScrollBar(e) {
                return e.scrollHeight > e.clientHeight;
            }

            function hasHorizontalScrollBar(e) {
                return e.scrollWidth > e.clientWidth;
            }

            $('.scroller').on('mousewheel DOMMouseScroll', function (e) {
                if (hasVerticalScrollBar(this)) {
                    var e0 = e.originalEvent,
                        delta = e0.wheelDelta || -e0.detail;

                    this.scrollTop += (delta < 0 ? 1 : -1) * 30;
                    e.preventDefault();
                }
            });

            //To solved issue of autocomplete in lower resolution
            if (typeof Sys !== 'undefined') {
                Sys.UI.Point = function Sys$UI$Point(x, y) {

                    x = Math.round(x);
                    y = Math.round(y);

                    var e = Function._validateParams(arguments, [
                        { name: "x", type: Number, integer: true },
                        { name: "y", type: Number, integer: true }
                    ]);
                    if (e) throw e;
                    this.x = x;
                    this.y = y;
                }
            }

        }
    };

}();


function CheckAllCheckBox(MasterCheckBox, divParent) {
    var cb = MasterCheckBox.id;
    $("div #" + divParent.id + " input[type='checkbox']").prop("checked", $("#" + cb).prop("checked"));
}