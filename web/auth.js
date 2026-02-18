"use strict";

(function () {
  var form = document.getElementById("auth-form");
  var tabs = Array.from(document.querySelectorAll("[data-auth-tab]"));
  var switchButton = document.getElementById("auth-switch");
  var submitButton = document.getElementById("auth-submit");
  var togglePassword = document.getElementById("auth-toggle-password");
  var passwordInput = document.getElementById("auth-password");
  var currentMode = "signin";

  function workbenchHref() {
    var search = window.location.search || "";
    var hash = window.location.hash || "";
    return "./workbench/" + search + hash;
  }

  function applyMode(mode) {
    currentMode = mode === "signup" ? "signup" : "signin";
    tabs.forEach(function (tab) {
      var isActive = tab.getAttribute("data-auth-tab") === currentMode;
      tab.classList.toggle("active", isActive);
      tab.setAttribute("aria-selected", String(isActive));
    });
    if (submitButton) {
      submitButton.textContent = currentMode === "signup" ? "Create Recon Account" : "Sign In to Recon";
    }
    if (switchButton) {
      switchButton.textContent = currentMode === "signup" ? "Back to sign in \u2192" : "Sign up free \u2192";
    }
  }

  function navigateWorkbench() {
    window.location.href = workbenchHref();
  }

  function hydrateLogoTargets() {
    var target = workbenchHref();
    var logos = Array.from(document.querySelectorAll("recon-logo"));
    logos.forEach(function (logo) {
      logo.setAttribute("href", target);
    });
  }

  if (tabs.length) {
    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        applyMode(tab.getAttribute("data-auth-tab") || "signin");
      });
    });
  }

  if (switchButton) {
    switchButton.addEventListener("click", function () {
      applyMode(currentMode === "signin" ? "signup" : "signin");
    });
  }

  if (togglePassword && passwordInput) {
    togglePassword.addEventListener("click", function () {
      var showing = passwordInput.type === "text";
      passwordInput.type = showing ? "password" : "text";
      togglePassword.setAttribute("aria-label", showing ? "Show password" : "Hide password");
    });
  }

  if (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      navigateWorkbench();
    });
  }

  Array.from(document.querySelectorAll(".auth-link")).forEach(function (link) {
    link.addEventListener("click", function (event) {
      event.preventDefault();
    });
  });

  var googleButton = document.querySelector(".auth-google");
  if (googleButton) {
    googleButton.addEventListener("click", navigateWorkbench);
  }

  hydrateLogoTargets();
  applyMode("signin");
})();
