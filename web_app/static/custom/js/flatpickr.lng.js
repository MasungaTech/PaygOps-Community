var CustomLNG = {
    weekdays: {
      shorthand: [PaygOps_LNG["Sun"], PaygOps_LNG["Mon"], PaygOps_LNG["Tue"], PaygOps_LNG["Wed"], PaygOps_LNG["Thu"], PaygOps_LNG["Fri"], PaygOps_LNG["Sat"]],
      longhand: [PaygOps_LNG["Sunday"], PaygOps_LNG["Monday"], PaygOps_LNG["Tuesday"], PaygOps_LNG["Wednesday"], PaygOps_LNG["Thursday"], PaygOps_LNG["Friday"], PaygOps_LNG["Saturday"]],
    },
    months: {
      shorthand: [PaygOps_LNG["Jan"], PaygOps_LNG["Feb"], PaygOps_LNG["Mar"], PaygOps_LNG["Apr"], PaygOps_LNG["May_SHORT"], PaygOps_LNG["Jun"], PaygOps_LNG["Jul"], PaygOps_LNG["Aug"], PaygOps_LNG["Sep"], PaygOps_LNG["Oct"], PaygOps_LNG["Nov"], PaygOps_LNG["Dec"]],
      longhand: [PaygOps_LNG["January"], PaygOps_LNG["February"], PaygOps_LNG["March"], PaygOps_LNG["April"], PaygOps_LNG["May"], PaygOps_LNG["June"], PaygOps_LNG["July"], PaygOps_LNG["August"], PaygOps_LNG["September"], PaygOps_LNG["October"], PaygOps_LNG["November"], PaygOps_LNG["December"]],
    },
    daysInMonth: [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31],
    firstDayOfWeek: 0,
    ordinal: (nth) => {
      const s = nth % 100;
      if (s > 3 && s < 21) return PaygOps_LNG["ORDINAL_ABB"];
      switch (s % 10) {
        case 1:
          return PaygOps_LNG["FIRST_ABB"];
        case 2:
          return PaygOps_LNG["SECOND_ABB"];
        case 3:
          return PaygOps_LNG["THIRD_ABB"];
        default:
          return PaygOps_LNG["ORDINAL_ABB"];
      }
    },
    rangeSeparator: PaygOps_LNG["TO_SEPARATOR"],
    weekAbbreviation: PaygOps_LNG["WEEK_ABB"],
    scrollTitle: PaygOps_LNG["SCROLL_TITLE"],
    toggleTitle: PaygOps_LNG["TOGGLE_TITLE"],
    amPM: ["AM", "PM"],
    yearAriaLabel: PaygOps_LNG["YEAR"],
    monthAriaLabel: PaygOps_LNG["MONTH"],
    hourAriaLabel: PaygOps_LNG["HOUR"],
    minuteAriaLabel: PaygOps_LNG["MINUTE"],
    time_24hr: true,
};

flatpickr.localize(CustomLNG);