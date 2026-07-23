/* ============================================================================
   BIOMEND Formación Continua — Interacciones (rediseño "Biomend Landing")
   ========================================================================== */
(function () {
  'use strict';

  function initIcons() {
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      try { window.lucide.createIcons(); } catch (e) { /* noop */ }
    }
  }

  /* ── Navegación: sombra al hacer scroll + menú móvil ───────────────────── */
  function initNav() {
    var nav = document.getElementById('nav');
    var toggle = document.getElementById('navToggle');
    var mobile = document.getElementById('navMobile');

    if (toggle && mobile) {
      var setOpen = function (open) {
        mobile.classList.toggle('is-open', open);
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        document.body.classList.toggle('nav-open', open);
        var icon = toggle.querySelector('[data-lucide], .lucide');
        if (icon) {
          icon.setAttribute('data-lucide', open ? 'x' : 'menu');
          initIcons();
        }
      };
      toggle.addEventListener('click', function () {
        setOpen(!mobile.classList.contains('is-open'));
      });
      mobile.querySelectorAll('a').forEach(function (a) {
        a.addEventListener('click', function () { setOpen(false); });
      });
      window.addEventListener('resize', function () {
        if (window.innerWidth > 960 && mobile.classList.contains('is-open')) {
          setOpen(false);
        }
      });
    }

    if (nav) {
      var onScroll = function () {
        nav.classList.toggle('is-scrolled', window.scrollY > 24);
      };
      window.addEventListener('scroll', onScroll, { passive: true });
      onScroll();
    }
  }

  /* ── Reveal on scroll (con stagger entre hermanos) ─────────────────────── */
  function initReveal() {
    var items = Array.prototype.slice.call(document.querySelectorAll('[data-reveal]'));
    if (!items.length) return;

    var reveal = function (el) {
      if (el.classList.contains('bm-in')) return;
      if (el.dataset.bmStaggered !== '1') {
        var parent = el.parentElement;
        var sibs = parent ? Array.prototype.slice.call(parent.querySelectorAll(':scope > [data-reveal]')) : [el];
        var idx = Math.max(0, sibs.indexOf(el));
        el.style.transitionDelay = Math.min(idx, 7) * 85 + 'ms';
        el.dataset.bmStaggered = '1';
      }
      el.classList.add('bm-in');
    };

    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) { reveal(entry.target); io.unobserve(entry.target); }
        });
      }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
      items.forEach(function (el) { io.observe(el); });
    } else {
      items.forEach(reveal);
    }
  }

  /* ── FAQ acordeón ──────────────────────────────────────────────────────── */
  function initFaq() {
    document.querySelectorAll('[data-faq]').forEach(function (item) {
      var btn = item.querySelector('.faq-item__btn');
      if (!btn) return;
      btn.addEventListener('click', function () {
        var isOpen = item.classList.contains('is-open');
        var group = item.closest('[data-faq-group]');
        if (group) {
          group.querySelectorAll('[data-faq].is-open').forEach(function (other) {
            if (other !== item) other.classList.remove('is-open');
          });
        }
        item.classList.toggle('is-open', !isOpen);
      });
    });
  }

  /* ── Carruseles (programas / egresados) ─────────────────────────────────── */
  function initCarousel() {
    document.querySelectorAll('[data-carousel]').forEach(function (carousel) {
      var track = carousel.querySelector('[data-carousel-track]');
      var slides = carousel.querySelectorAll('.carousel__slide');
      var dots = carousel.querySelectorAll('[data-carousel-dot]');
      var prev = carousel.querySelector('[data-carousel-prev]');
      var next = carousel.querySelector('[data-carousel-next]');
      var count = slides.length;
      if (!track || count === 0) return;

      var interval = parseInt(carousel.getAttribute('data-interval') || '10000', 10);
      if (isNaN(interval) || interval < 2000) interval = 10000;

      var index = 0;
      var timer = null;

      var apply = function () {
        track.style.transform = 'translateX(-' + (index * 100) + '%)';
        dots.forEach(function (d, i) {
          var on = i === index;
          d.classList.toggle('is-active', on);
          d.setAttribute('aria-selected', on ? 'true' : 'false');
        });
      };
      var goTo = function (i) { index = (i + count) % count; apply(); restart(); };
      var start = function () {
        if (count <= 1) return;
        timer = setInterval(function () { index = (index + 1) % count; apply(); }, interval);
      };
      var restart = function () { clearInterval(timer); start(); };

      if (prev) prev.addEventListener('click', function () { goTo(index - 1); });
      if (next) next.addEventListener('click', function () { goTo(index + 1); });
      dots.forEach(function (d, i) { d.addEventListener('click', function () { goTo(i); }); });
      carousel.addEventListener('mouseenter', function () { clearInterval(timer); });
      carousel.addEventListener('mouseleave', start);

      apply();
      start();
    });
  }

  /* ── Subida de documentos: refleja el nombre del archivo ───────────────── */
  function initFileInputs() {
    document.querySelectorAll('.doc input[type="file"]').forEach(function (input) {
      input.addEventListener('change', function () {
        var label = input.closest('.doc');
        if (!label) return;
        var hint = label.querySelector('.doc__hint');
        var iconEl = label.querySelector('.doc__ico i, .doc__ico [data-lucide]');
        if (input.files && input.files.length) {
          label.classList.add('is-filled');
          if (hint) hint.textContent = input.files[0].name;
          if (iconEl) { iconEl.setAttribute('data-lucide', 'check-circle-2'); initIcons(); }
        } else {
          label.classList.remove('is-filled');
          if (hint) hint.textContent = 'PDF, JPG, PNG · máx. 5 MB';
        }
      });
    });
  }

  /* ── Pestañas de inscripción (Inscripción / Iniciar sesión) ────────────── */
  function initTabs() {
    var tabs = document.querySelectorAll('[data-tab]');
    if (!tabs.length) return;
    tabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        var target = tab.getAttribute('data-tab');
        tabs.forEach(function (t) { t.classList.toggle('is-active', t === tab); });
        document.querySelectorAll('[data-panel]').forEach(function (p) {
          p.classList.toggle('is-active', p.getAttribute('data-panel') === target);
        });
      });
    });
  }

  /* ── Copiar enlace de acceso ───────────────────────────────────────────── */
  function initCopyLink() {
    document.querySelectorAll('[data-copy]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var value = btn.getAttribute('data-copy');
        var labelEl = btn.querySelector('[data-copy-label]');
        var iconEl = btn.querySelector('i, [data-lucide]');
        try {
          if (navigator.clipboard) navigator.clipboard.writeText(value);
        } catch (e) { /* noop */ }
        if (labelEl) labelEl.textContent = 'Copiado';
        if (iconEl) { iconEl.setAttribute('data-lucide', 'check'); initIcons(); }
        setTimeout(function () {
          if (labelEl) labelEl.textContent = 'Copiar enlace';
          if (iconEl) { iconEl.setAttribute('data-lucide', 'copy'); initIcons(); }
        }, 2000);
      });
    });
  }

  /* ── Figuras animadas en fondos oscuros (salud / academia) ─────────────── */
  function initDarkFloaters() {
    var icons = [
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 3v18M3 12h18"/><circle cx="12" cy="12" r="9"/></svg>',
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M19.5 12.5c1.6-1.7 1.6-4.4 0-6.1-1.7-1.7-4.4-1.7-6.1 0L12 8l-1.4-1.6c-1.7-1.7-4.4-1.7-6.1 0-1.6 1.7-1.6 4.4 0 6.1L12 21l7.5-8.5z"/></svg>',
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4.5 4.5c3 3 3 12 0 15M19.5 4.5c-3 3-3 12 0 15"/><path d="M8 8.5c2.5 1.2 5.5 1.2 8 0M8 15.5c2.5-1.2 5.5-1.2 8 0"/><circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none"/></svg>',
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M6 4h4v4H6zM14 4h4v4h-4zM6 16h4v4H6zM14 16h4v4h-4z"/><path d="M10 6h4M10 18h4M8 10v4M16 10v4"/></svg>',
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4 19V7a2 2 0 0 1 2-2h9l5 5v9a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"/><path d="M14 5v5h5"/></svg>'
    ];
    document.querySelectorAll('.section--dark, .hero--dark, .footer.section--dark').forEach(function (section) {
      if (section.querySelector('.dark-floaters')) return;
      var wrap = document.createElement('div');
      wrap.className = 'dark-floaters';
      wrap.setAttribute('aria-hidden', 'true');
      icons.forEach(function (svg, i) {
        var el = document.createElement('div');
        el.className = 'dark-floater dark-floater--' + (i + 1);
        el.innerHTML = svg;
        wrap.appendChild(el);
      });
      section.insertBefore(wrap, section.firstChild);
    });
  }

  /* ── Init ──────────────────────────────────────────────────────────────── */
  function init() {
    initIcons();
    initNav();
    initDarkFloaters();
    initReveal();
    initFaq();
    initCarousel();
    initFileInputs();
    initTabs();
    initCopyLink();
    // Re-render de iconos por si Lucide cargó tarde (CDN).
    setTimeout(initIcons, 400);
    setTimeout(initIcons, 1200);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
