"use strict";

(function () {
  var SIZES = {
    sm: 18,
    md: 22,
    lg: 24,
  };

  function safeSize(value) {
    return SIZES[value] ? value : "md";
  }

  function safeVariant(value) {
    if (value === "light" || value === "dark" || value === "auto") {
      return value;
    }
    return "dark";
  }

  function parseRgb(color) {
    var match = String(color).match(/rgba?\(([^)]+)\)/i);
    if (!match) {
      return null;
    }
    var parts = match[1].split(",").map(function (part) {
      return Number(part.trim());
    });
    if (parts.length < 3 || Number.isNaN(parts[0]) || Number.isNaN(parts[1]) || Number.isNaN(parts[2])) {
      return null;
    }
    var alpha = parts.length >= 4 ? parts[3] : 1;
    if (Number.isNaN(alpha) || alpha <= 0) {
      return null;
    }
    return { r: parts[0], g: parts[1], b: parts[2] };
  }

  function relativeLuminance(rgb) {
    function convert(channel) {
      var c = channel / 255;
      return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    }
    var r = convert(rgb.r);
    var g = convert(rgb.g);
    var b = convert(rgb.b);
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  }

  function resolveAutoVariant(element) {
    var node = element.closest(".header-topbar") || element.closest(".header") || document.body;
    while (node) {
      var rgb = parseRgb(window.getComputedStyle(node).backgroundColor);
      if (rgb) {
        return relativeLuminance(rgb) < 0.45 ? "light" : "dark";
      }
      node = node.parentElement;
    }
    return "dark";
  }

  function escapeAttr(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function defaultSrc(variant) {
    return variant === "light"
      ? "./assets/recon-mark-light.svg"
      : "./assets/recon-mark-dark.svg";
  }

  class ReconLogo extends HTMLElement {
    static get observedAttributes() {
      return ["size", "variant", "href", "dark-src", "light-src", "show-label"];
    }

    connectedCallback() {
      this.render();
    }

    attributeChangedCallback() {
      this.render();
    }

    render() {
      var size = safeSize(this.getAttribute("size") || "md");
      var variant = safeVariant(this.getAttribute("variant") || "dark");
      var href = this.getAttribute("href") || "/workbench";
      var darkSrc = this.getAttribute("dark-src") || defaultSrc("dark");
      var lightSrc = this.getAttribute("light-src") || defaultSrc("light");
      var resolvedVariant = variant === "auto" ? resolveAutoVariant(this) : variant;
      var src = resolvedVariant === "light" ? lightSrc : darkSrc;
      var showLabel = this.getAttribute("show-label") !== "false";
      var labelHtml = showLabel ? '<span class="recon-logo-text">Recon</span>' : "";

      this.innerHTML =
        '<a class="recon-logo recon-logo-' +
        escapeAttr(size) +
        '" href="' +
        escapeAttr(href) +
        '" aria-label="Recon Home">' +
        '<img class="recon-logo-mark" src="' +
        escapeAttr(src) +
        '" alt="Recon">' +
        labelHtml +
        "</a>";
    }
  }

  if (!customElements.get("recon-logo")) {
    customElements.define("recon-logo", ReconLogo);
  }
})();
