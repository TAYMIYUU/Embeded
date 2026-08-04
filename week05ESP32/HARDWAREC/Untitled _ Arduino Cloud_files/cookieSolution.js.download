var arduinoCookieSolution = (function (exports) {
  'use strict';

  function loadJS(url, {async = false}) {
    return new Promise((resolve, reject) => {
      // Create a new script element
      const script = window.document.createElement('script');
      script.src = url;
      script.onload = resolve;
      script.async = async;

      // Inject the script into the DOM
      const ref = window.document.getElementsByTagName('script')[0];
      ref.parentNode.insertBefore(script, ref);
      setTimeout(reject, 2000);
    });
  }

  function initCookieConsent(coppa) {
    window._iub = window._iub || [];
    // docs: https://www.iubenda.com/it/help/623-come-configurare-la-cookie-solution-guida-avanzata#stile-testo
    window._iub.csConfiguration = window._iub.csConfiguration || {};
    Object.assign(window._iub.csConfiguration, {
      googleConsentMode: "template",
      cookiePolicyId: 11225532,
      lang: "en",
      purposes: coppa ? "1, 4" : "1, 4, 5",
      siteId: 2023027,
      reloadOnConsent: window._iub.csConfiguration.reloadOnConsent || false ,
      cookiePolicyUrl: "https://www.arduino.cc/en/cookie-policy",
      countryDetection: true,
      floatingPreferencesButtonDisplay: false
    });

    window._iub.csConfiguration.banner = window._iub.csConfiguration.banner || {};
    Object.assign(window._iub.csConfiguration.banner, {
      applyStyles: false,

      rejectButtonDisplay: true,
      customizeButtonDisplay: true,
      position: "float-bottom-left",
      acceptButtonDisplay: true,
      backgroundOverlay: false,
      closeButtonDisplay: true,
      // header
      logo: "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDIiIGhlaWdodD0iMjAiIHZpZXdCb3g9IjAgMCA0MiAyMCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGcgY2xpcC1wYXRoPSJ1cmwoI2NsaXAwXzQyNV82MTQpIj4KPHBhdGggZD0iTTQxLjk5OTkgMTAuMDAxMUM0MS45OTk5IDQuNDg2MzIgMzcuMzU4NyAwIDMxLjY1NDIgMEMzMS4xMjc1IDAgMzAuNTkyMiAwLjAzNTk2MzggMzAuMDYyNiAwLjExMjkyM0MyNS42Mjk2IDAuNzQ2NTE3IDIyLjY2MzIgMy45NDI2MiAyMS4wMDI4IDYuMzkzNkMxOS4zMzY2IDMuOTQyNjIgMTYuMzcwMyAwLjc0NjUxNyAxMS45Mzg3IDAuMTEyOTIzQzExLjQwOTEgMC4wMzU5NjM4IDEwLjg3MjQgMCAxMC4zNDcxIDBDNC42Mzk3MiAwIDAgNC40ODYzMiAwIDEwLjAwMTFDMCAxNS41MTY2IDQuNjM5NzEgMjAgMTAuMzQyOCAyMEMxMC44NzI0IDIwIDExLjQwOTEgMTkuOTY2OSAxMS45Mzg3IDE5Ljg5MDdDMTYuMzcwMyAxOS4yNTM1IDE5LjMzNjYgMTYuMDU2IDIxLjAwMjggMTMuNjAyOEMyMi42NjMyIDE2LjA1NiAyNS42Mjk2IDE5LjI1MzUgMzAuMDYyNiAxOS44OTA3QzMwLjU5MjIgMTkuOTY2OSAzMS4xMjc1IDIwIDMxLjY1ODUgMjBDMzcuMzYxNiAyMCA0MS45OTk5IDE1LjUxNjYgNDEuOTk5OSAxMC4wMDExWk0xMS40MzY0IDE2LjM3ODlDMTEuMDc0NyAxNi40MzE0IDEwLjcwNTkgMTYuNDU4NyAxMC4zNDI4IDE2LjQ1ODdDNi41OTE0NSAxNi40NTg3IDMuNTM3NTUgMTMuNTU4OSAzLjUzNzU1IDEwLjAwMTFDMy41Mzc1NSA2LjQ0MTA4IDYuNTkxNDUgMy41NDEzIDEwLjM0NzEgMy41NDEzQzEwLjcwNzMgMy41NDEzIDExLjA3NDcgMy41NzA3OCAxMS40Mzc4IDMuNjIwNDJDMTUuNjE0IDQuMjE4MDUgMTguMTcxMyA4LjM0NjIxIDE5LjAzODIgOS45OTg5M0MxOC4xNjk5IDExLjY1NTkgMTUuNjE0IDE1Ljc4MTkgMTEuNDM2NCAxNi4zNzg5Wk0yMi45NjQ2IDEwLjAwMTFDMjMuODMxNCA4LjM0NjIxIDI2LjM4NzMgNC4yMTgwNSAzMC41NjM1IDMuNjIwNDJDMzAuOTI1MSAzLjU3MDc4IDMxLjI5NTQgMy41NDEzIDMxLjY1NDIgMy41NDEzQzM1LjQwODQgMy41NDEzIDM4LjQ2MjMgNi40NDEwOCAzOC40NjIzIDEwLjAwMTFDMzguNDYyMyAxMy41NTg5IDM1LjQwODQgMTYuNDU4NyAzMS42NTg1IDE2LjQ1ODdDMzEuMjk2OCAxNi40NTg3IDMwLjkyOCAxNi40MzE0IDMwLjU2MzUgMTYuMzc4OUMyNi4zODczIDE1Ljc4MTkgMjMuODI4NSAxMS42NTIzIDIyLjk2NDYgMTAuMDAxMVoiIGZpbGw9IndoaXRlIi8+CjxwYXRoIGQ9Ik0xMy43MDgyIDkuMDIzNDRINy40OTU2MVYxMS4wM0gxMy43MDgyVjkuMDIzNDRaIiBmaWxsPSJ3aGl0ZSIvPgo8cGF0aCBkPSJNMzIuMzQzMSAxMS4wMzAySDM0LjQ0MjZWOS4wMjM2NkgzMi4zNDMxVjYuOTEyMTFIMzAuMzM1M1Y5LjAyMzY2SDI4LjIzMjlWMTEuMDMwMkgzMC4zMzUzVjEzLjE0MThIMzIuMzQzMVYxMS4wMzAyWiIgZmlsbD0id2hpdGUiLz4KPHBhdGggZD0iTTQxLjEzNiAxLjIxNTA0QzQxLjE5OTMgMS4xODM4NCA0MS4yNDY4IDEuMTQxMjggNDEuMjgxNCAxLjA4NjY2QzQxLjMxNDUgMS4wMzIwNSA0MS4zMzE4IDAuOTY5NjM2IDQxLjMzMTggMC45MDM2OTVDNDEuMzMxOCAwLjgwMDEyOCA0MS4yOTQzIDAuNzA5MzQ2IDQxLjIxOTUgMC42MzM0NzRDNDEuMTQ2MSAwLjU3NTc5IDQxLjAxOTMgMC41MTg1MDUgNDAuODM5NCAwLjUxODU1NUM0MC43NzE3IDAuNTE4NTU1IDQwLjcxMTIgMC41MTk5OCA0MC42NTggMC41MjM1NEM0MC42MDQ3IDAuNTI3MDc1IDQwLjU1NDMgMC41MzEzMzcgNDAuNTA1NCAwLjUzNzcyN1YxLjYyNjRINDAuNzgzMlYxLjI2OTY2SDQwLjg5NTVMNDEuMDg5OSAxLjYyNjRINDEuNDA2Nkw0MS4xMzYgMS4yMTUwNFpNODEuODU4MSAxLjA2NzUyQzQwLjgyMDcgMS4wNjc1MiA0MC43OTE5IDEuMDY1MzggNDAuNzc0NiAxLjA1OTAyVjAuNzY2MDkyQzQwLjc5MTkgMC43NjA0MjYgNDAuODIzNiAwLjc1Njg2OSA0MC44NjY3IDAuNzU2ODY5QzQwLjk4NDggMC43NTY4NjkgNDEuMDQzOCAwLjgwNzk0OSA0MS4wNDM4IDAuOTEyMTkyQzQxLjA0MzggMS4wMTY0NiA0MC45ODE5IDEuMDY3NTIgNDAuODU4MSAxLjA2NzUyWk00MC44OTUgMEM0MC4yODQ1IDAgMzkuNzkgMC40OTU1OTcgMzkuNzkgMS4xMDc1QzM5Ljc5IDEuNzE4NjkgNDAuMjg0NSAyLjIxNDk5IDQwLjg5NSAyLjIxNDk5QzQxLjUwNDggMi4yMTQ5OSA0MiAxLjcxODY5IDQyIDEuMTA3NUM0MiAwLjQ5NTU5NyA0MS41MDQ4IDAgNDAuODk1IDBaTTQwLjg5NSAxLjk2ODU3QzQwLjQzMTYgMS45Njg1NyA0MC4wNTU5IDEuNTgzMDIgNDAuMDU1OSAxLjEwNzVDNDAuMDU1OSAwLjYzMTk3MyA0MC40MzE2IDAuMjQ1NzIgNDAuODk1IDAuMjQ1NzJDNDEuMzU3NyAwLjI0NTcyIDQxLjczMzQgMC42MzE5NTYgNDEuNzMzNCAxLjEwNzVDNDEuNzMzNCAxLjU4MzA0IDQxLjM1NzcgMS45Njg1NyA0MC44OTUgMS45Njg1N1oiIGZpbGw9IndoaXRlIi8+CjwvZz4KPGRlZnM+CjxjbGlwUGF0aCBpZD0iY2xpcDBfNDI1XzYxNCI+CjxyZWN0IHdpZHRoPSI0MiIgaGVpZ2h0PSIyMCIgZmlsbD0id2hpdGUiLz4KPC9jbGlwUGF0aD4KPC9kZWZzPgo8L3N2Zz4K",
      brandTextColor: "white"
    });

    window._iub.csConfiguration.callback = window._iub.csConfiguration.callback || {};
    Object.assign(window._iub.csConfiguration.callback, {
      onBannerShown: () => {
        const closeBtn = document.querySelector(".iubenda-cs-close-btn");
        closeBtn.removeAttribute("style");
        closeBtn.classList = "iubenda-cs-accept-btn iubenda-cs-close-btn-second";

        document.querySelector(".iubenda-cs-close-btn")?.style.setProperty("display", "block", "important");
        const closeButton = document.querySelector(".iubenda-cs-close-btn");
        if (closeButton) {
          closeButton.style.display = "block";
          closeButton.style.opacity = "1";
          closeButton.style.visibility = "visible";
        }
      },

      // push events to google tag manager to enable the firing of specific tags according to the preference given by the user
      onPreferenceExpressedOrNotNeeded: preference => {
        const dataLayer = window.dataLayer || [];

        if (window._iub.cs.api.ccpaApplies()) {
          document.querySelector("body").classList.add("ccpaApplies");
        }

        if (preference) {
          let uspr_refused = preference.uspr ? !preference.uspr.s || !preference.uspr.sh : false;
          if (preference.consent === true) {
            dataLayer.push({
              event: "iubenda_consent_given"
            });
          } else if (preference.consent === false) {
            dataLayer.push({
              event: "iubenda_consent_rejected"
            });
          } else if (preference.purposes) {
            for (const purposeId in preference.purposes) {
              if (preference.purposes[purposeId]) {
                if ((purposeId == "4" || purposeId == "5") && uspr_refused) {
                  continue; // skip purposes 4 and 5 if US privacy opt-out is active
                }
                dataLayer.push({
                  event: "iubenda_consent_given_purpose_" + purposeId
                });
              }
            }
          }
        } else {
          dataLayer.push({
            event: "iubenda_preference_not_needed"
          });
        }
      }
    });

    return loadJS("https://embeds.iubenda.com/widgets/9a0b3c88-6db6-11ee-8bfc-5ad8d8c564c0.js", {async: true});
  }

  exports.initCookieConsent = initCookieConsent;

  Object.defineProperty(exports, '__esModule', { value: true });

  return exports;

})({});
