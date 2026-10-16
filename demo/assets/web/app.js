/* ===== I18N ===== */
// Force reset to uz if user has old cached language from before uz-default update
const LANG_VERSION = '2';
if (localStorage.getItem('gsp_lang_v') !== LANG_VERSION) {
  localStorage.setItem('gsp_lang', 'uz');
  localStorage.setItem('gsp_lang_v', LANG_VERSION);
}
let currentLang = localStorage.getItem('gsp_lang') || 'uz';

function t(path) {
  const keys = path.split('.');
  let obj = LANG[currentLang];
  for (const k of keys) {
    if (obj == null) return path;
    obj = obj[k];
  }
  return obj != null ? obj : path;
}

function applyI18n() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const val = t(el.getAttribute('data-i18n'));
    if (val !== el.getAttribute('data-i18n')) el.innerHTML = val;
  });
  document.querySelectorAll('[data-i18n-ph]').forEach(el => {
    const val = t(el.getAttribute('data-i18n-ph'));
    if (val !== el.getAttribute('data-i18n-ph')) el.placeholder = val;
  });
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === currentLang);
  });
  const aboutList = document.getElementById('aboutList');
  if (aboutList) {
    const items = t('about.li');
    if (Array.isArray(items)) {
      aboutList.innerHTML = items.map(li => `<li>✓ ${li}</li>`).join('');
    }
  }
  const footerSvcs = t('footer.servicesList');
  if (Array.isArray(footerSvcs)) {
    document.querySelectorAll('.footer-services-list').forEach(ul => {
      ul.innerHTML = footerSvcs.map(s => `<li><a href="index.html#services">${s}</a></li>`).join('');
    });
  }
  const svcOptions = t('contact.svcOptions');
  document.querySelectorAll('.contact-svc-select').forEach(sel => {
    sel.innerHTML = `<option value="">${t('contact.ph.svc')}</option>`;
    if (Array.isArray(svcOptions)) {
      svcOptions.forEach(opt => { sel.innerHTML += `<option>${opt}</option>`; });
    }
  });
  document.documentElement.lang = currentLang;
}

function refreshLawyerLang() {
  const heroTagEl = document.getElementById('heroTag');
  if (!heroTagEl) return;
  const params = new URLSearchParams(window.location.search);
  const lawyer = LAWYERS.find(l => l.slug === params.get('id'));
  if (!lawyer) return;
  heroTagEl.textContent = t('lp.heroTag');
  document.getElementById('heroName').textContent = getLawyerField(lawyer, 'name');
  document.getElementById('heroTitle').textContent = translateStr(lawyer.title, 'lawyers.titleMap');
  const specsEl = document.getElementById('heroSpecs');
  if (specsEl) {
    specsEl.innerHTML = '';
    lawyer.specialization.forEach(s => {
      specsEl.innerHTML += `<span class="spec-tag-hero">${translateStr(s, 'lawyers.specMap')}</span>`;
    });
  }
  const otherGrid = document.getElementById('otherLawyers');
  if (otherGrid) {
    otherGrid.innerHTML = '';
    LAWYERS.filter(l => l.slug !== lawyer.slug && !l.externalUrl).slice(0, 4).forEach(l => otherGrid.appendChild(createLawyerCard(l)));
  }

  const bioEl = document.getElementById('lawyerBio');
  const descEl = document.getElementById('lawyerDesc');
  const helpEl = document.getElementById('lawyerHelp');
  if (bioEl) bioEl.textContent = getLawyerField(lawyer, 'bio');
  if (descEl) descEl.textContent = getLawyerField(lawyer, 'description');
  if (helpEl) helpEl.textContent = getLawyerField(lawyer, 'howIHelp');

  // Re-render experience
  const sideExp = document.getElementById('sideExp');
  if (sideExp) sideExp.textContent = getLawyerExp(lawyer);
  const heroMeta = document.getElementById('heroMeta');
  if (heroMeta) heroMeta.innerHTML = `
    <div class="hero-meta-item"><span>${getLawyerExp(lawyer)}</span><span data-i18n="lp.expLbl">${t('lp.expLbl')}</span></div>
    <div class="hero-meta-item"><span>${lawyer.cases}</span><span data-i18n="lp.casesLbl">${t('lp.casesLbl')}</span></div>
  `;

  // Re-render services
  const svcEl = document.getElementById('lawyerServices');
  if (svcEl) {
    svcEl.innerHTML = '';
    const svcData = getLawyerField(lawyer, 'services');
    const svcArr = Array.isArray(svcData) ? svcData : lawyer.services;
    svcArr.forEach(s => { svcEl.innerHTML += `<div class="service-item">${s}</div>`; });
  }

  // Re-render education
  const eduEl = document.getElementById('lawyerEducation');
  if (eduEl && lawyer.education) {
    eduEl.innerHTML = '';
    lawyer.education.forEach(e => {
      eduEl.innerHTML += `
        <div class="edu-item">
          <div class="edu-dot-wrap"><div class="edu-dot"></div><div class="edu-line"></div></div>
          <div class="edu-content">
            <div class="edu-year">${e.year}</div>
            <div class="edu-degree">${getLocalStr(e.degree)}</div>
            <div class="edu-institution">${getLocalStr(e.institution)}</div>
          </div>
        </div>`;
    });
  }

  // Re-render achievements
  const achEl = document.getElementById('lawyerAchievements');
  if (achEl && lawyer.achievements) {
    achEl.innerHTML = '';
    const achData = getLawyerField(lawyer, 'achievements');
    const achArr = Array.isArray(achData) ? achData : lawyer.achievements;
    achArr.forEach(a => { achEl.innerHTML += `<li>${a}</li>`; });
  }

  // Re-render publications
  const pubEl = document.getElementById('lawyerPublications');
  if (pubEl && lawyer.publications) {
    pubEl.innerHTML = '';
    const openLabel = { ru: 'Открыть', uz: 'Ochish', en: 'Open' };
    lawyer.publications.forEach(p => {
      const inner = `
        <div class="pub-title">${p.title}</div>
        <div class="pub-meta">
          <span class="pub-journal">${p.journal}</span>
          <span class="pub-year">${p.year}</span>
          ${p.url ? `<span class="pub-link">↗ ${openLabel[currentLang] || 'Открыть'}</span>` : ''}
        </div>`;
      if (p.url) {
        pubEl.innerHTML += `<a class="pub-item pub-item-link" href="${p.url}" target="_blank" rel="noopener noreferrer">${inner}</a>`;
      } else {
        pubEl.innerHTML += `<div class="pub-item">${inner}</div>`;
      }
    });
  }

  // Re-render certificates on lang switch
  const certElR = document.getElementById('lawyerCertificates');
  if (certElR && lawyer.certificates && lawyer.certificates.length > 0) {
    certElR.innerHTML = '';
    const viewLabel = { ru: 'Открыть оригинал', uz: "Aslini ochish", en: 'Open original' };
    lawyer.certificates.forEach(c => {
      const titleStr = (typeof c.title === 'object') ? (c.title[currentLang] || c.title.ru) : c.title;
      certElR.innerHTML += `
        <div class="cert-card">
          <a href="${c.file}" target="_blank" rel="noopener noreferrer" class="cert-img-wrap">
            <img src="${c.image}" alt="${titleStr}" class="cert-img" loading="lazy">
            <div class="cert-img-overlay"><span>↗ ${viewLabel[currentLang]}</span></div>
          </a>
          <div class="cert-card-footer">
            <span class="cert-card-title">${titleStr}</span>
          </div>
        </div>`;
    });
  }
}

function setLang(lang) {
  currentLang = lang;
  localStorage.setItem('gsp_lang', lang);
  applyI18n();
  renderDynamic();
  refreshLawyerLang();
}

/* ===== NAVBAR ===== */
function toggleMenu() {
  document.getElementById('navLinks').classList.toggle('open');
  const btn = document.getElementById('navToggle');
  if (btn) btn.classList.toggle('open');
}
window.addEventListener('scroll', () => {
  const nb = document.getElementById('navbar');
  if (nb) nb.style.background = window.scrollY > 50
    ? 'rgba(10,35,50,0.98)'
    : 'rgba(14,45,62,0.95)';
});
document.addEventListener('click', e => {
  const links = document.getElementById('navLinks');
  const toggle = document.querySelector('.nav-toggle');
  if (links && toggle && !links.contains(e.target) && !toggle.contains(e.target)) {
    links.classList.remove('open');
    const btn = document.getElementById('navToggle');
    if (btn) btn.classList.remove('open');
  }
});

/* ===== FORM ===== */
const CONTACT_API_URL = 'https://mail.gsplaw.co.uz/contact-api/contact';

function submitForm(e) {
  e.preventDefault();
  const form = e.target;
  const success = document.getElementById('formSuccess');
  const btn = form.querySelector('button[type="submit"]');
  const inputs = form.querySelectorAll('input');
  const payload = {
    name: inputs[0] ? inputs[0].value : '',
    phone: inputs[1] ? inputs[1].value : '',
    email: inputs[2] ? inputs[2].value : '',
    service: form.querySelector('.contact-svc-select') ? form.querySelector('.contact-svc-select').value : '',
    message: form.querySelector('textarea') ? form.querySelector('textarea').value : ''
  };

  if (btn) btn.disabled = true;

  fetch(CONTACT_API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
    .then((res) => {
      if (!res.ok) throw new Error('request_failed');
      if (success) {
        success.textContent = t('contact.success');
        success.style.display = 'block';
        form.style.display = 'none';
        setTimeout(() => {
          success.style.display = 'none';
          form.style.display = 'flex';
          form.reset();
        }, 5000);
      }
    })
    .catch(() => {
      if (success) {
        success.textContent = t('contact.error') || 'Не удалось отправить. Попробуйте позже.';
        success.style.display = 'block';
        setTimeout(() => { success.style.display = 'none'; }, 5000);
      }
    })
    .finally(() => {
      if (btn) btn.disabled = false;
    });
}

/* ===== HELPERS ===== */
function goToLawyer(lawyer) {
  if (lawyer.externalUrl) {
    window.open(lawyer.externalUrl, '_blank', 'noopener');
  } else {
    window.location.href = `lawyer.html?id=${lawyer.slug}`;
  }
}

function translateStr(str, mapKey) {
  const map = t(mapKey);
  return (map && typeof map === 'object' && map[str]) ? map[str] : str;
}

function getLawyerField(lawyer, field) {
  const val = lawyer[field];
  if (val && typeof val === 'object' && !Array.isArray(val)) return val[currentLang] || val.ru || '';
  return val || '';
}

// Returns a localized string from a {ru,uz,en} object or plain string
function getLocalStr(val) {
  if (val && typeof val === 'object') return val[currentLang] || val.ru || '';
  return val || '';
}

// Returns experience with correct language suffix
function getLawyerExp(lawyer) {
  const raw = lawyer.experience || '';
  // raw is like "13+ лет" or "10+ лет" — strip Russian suffix, add current lang
  const num = raw.replace(/[^\d+]/g, ''); // "13+"
  const suffix = { ru: 'лет', uz: 'yil', en: 'years' };
  return num + ' ' + (suffix[currentLang] || 'лет');
}

function createLawyerCard(lawyer) {
  const card = document.createElement('div');
  card.className = 'lawyer-card';
  card.onclick = () => goToLawyer(lawyer);
  const isExternal = !!lawyer.externalUrl;
  const btnLabel = isExternal ? t('lp.visitWebsite') : t('lawyers.more');
  const translatedTitle = translateStr(lawyer.title, 'lawyers.titleMap');
  const translatedSpecs = lawyer.specialization.map(s => translateStr(s, 'lawyers.specMap'));
  card.innerHTML = `
    <div class="lawyer-avatar-wrap">
      ${lawyer.photo
        ? `<div class="lawyer-avatar lawyer-avatar-photo"><img src="${lawyer.photo}" alt="${getLawyerField(lawyer,'name')}"></div>`
        : `<div class="lawyer-avatar" style="background:${lawyer.accentColor};">${lawyer.initials}</div>`}
      ${isExternal ? '<div class="ext-badge">↗</div>' : ''}
    </div>
    <div class="lawyer-info">
      <h3>${getLawyerField(lawyer,'name')}</h3>
      <p class="lawyer-title">${translatedTitle}</p>
      <div class="lawyer-specs">
        ${translatedSpecs.map(s => `<span class="spec-tag">${s}</span>`).join('')}
      </div>
      <div class="lawyer-meta">
        <span><strong>${getLawyerExp(lawyer)}</strong></span>
        <span><strong>${lawyer.cases}</strong><span>${t('lawyers.casesLbl')}</span></span>
      </div>
    </div>
    <div class="lawyer-card-btn">${btnLabel}</div>
  `;
  return card;
}

/* ===== COUNTER ANIMATION ===== */
function animateCounter(el, target, duration) {
  const isPercent = target.includes('%');
  const isPlus = target.includes('+');
  const isDollar = target.startsWith('$');
  const clean = target.replace(/[^0-9.]/g, '');
  const end = parseFloat(clean);
  if (isNaN(end)) { el.textContent = target; return; }
  const start = 0;
  const startTime = performance.now();
  function step(now) {
    const progress = Math.min((now - startTime) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = Math.round(start + (end - start) * eased);
    let display = isDollar ? '$' : '';
    display += current >= 1000 ? (current / 1000).toFixed(current % 1000 === 0 ? 0 : 0) + (current >= 1000 ? 'M' : '') : current;
    if (target.includes('M')) display = isDollar ? '$' + current + 'M' : current + 'M';
    else display = (isDollar ? '$' : '') + current;
    display += isPlus ? '+' : '';
    display += isPercent ? '%' : '';
    el.textContent = display;
    if (progress < 1) requestAnimationFrame(step);
    else el.textContent = target;
  }
  requestAnimationFrame(step);
}

/* ===== RENDER DYNAMIC ===== */
function renderDynamic() {
  // Hero stats
  const statsEl = document.getElementById('heroStats');
  if (statsEl) {
    statsEl.innerHTML = '';
    FIRM.stats.forEach((s, i) => {
      const labels = t('stats');
      statsEl.innerHTML += `<div class="stat"><span class="stat-num">${s.num}</span><span class="stat-label">${Array.isArray(labels) ? labels[i] : s.label}</span></div>`;
    });
  }

  applyI18n();

  // Metrics
  const mg = document.getElementById('metricsGrid');
  if (mg) {
    mg.innerHTML = '';
    METRICS.forEach(m => {
      mg.innerHTML += `
        <div class="metric-card">
          <span class="metric-icon">${m.icon}</span>
          <span class="metric-num" data-target="${m.num}">${m.num}</span>
          <span class="metric-label">${t('metrics.' + m.key)}</span>
        </div>`;
    });
  }

  // Key partners (first 4 lawyers marked as partners)
  const pg = document.getElementById('partnersGrid');
  if (pg) {
    pg.innerHTML = '';
    const partners = LAWYERS.filter(l => /партнёр|partner|sherik/i.test(l.title)).slice(0, 4);
    partners.forEach(l => {
      const translatedTitle = translateStr(l.title, 'lawyers.titleMap');
      const translatedSpecs = l.specialization.map(s => translateStr(s, 'lawyers.specMap'));
      const photoHtml = l.photo
        ? `<img src="${l.photo}" alt="${getLawyerField(l,'name')}">`
        : `<div class="partner-photo-initials" style="background:${l.accentColor};">${l.initials}</div>`;
      const onclick = l.externalUrl
        ? `window.open('${l.externalUrl}','_blank','noopener')`
        : `window.location.href='lawyer.html?id=${l.slug}'`;
      pg.innerHTML += `
        <div class="partner-card" onclick="${onclick}">
          <div class="partner-photo-area">${photoHtml}</div>
          <div class="partner-card-body">
            <div class="partner-name">${getLawyerField(l,'name')}</div>
            <div class="partner-title">${translatedTitle}</div>
            <div class="partner-specs">
              ${translatedSpecs.slice(0,2).map(s => `<span class="spec-tag">${s}</span>`).join('')}
            </div>
            <p class="partner-bio">${getLawyerField(l, 'bio').substring(0, 110)}...</p>
            <div class="partner-card-footer">
              <div class="partner-stat"><strong>${getLawyerExp(l)}</strong></div>
              <div class="partner-stat"><strong>${l.cases}</strong><span>${t('lawyers.casesLbl')}</span></div>
            </div>
          </div>
        </div>`;
    });
  }

  // Services
  const sg = document.getElementById('servicesGrid');
  if (sg) {
    sg.innerHTML = '';
    const svcItems = t('services.items');
    SERVICES.forEach((s, i) => {
      const item = Array.isArray(svcItems) && svcItems[i] ? svcItems[i] : s;
      sg.innerHTML += `<div class="service-card"><div class="service-icon">${s.icon}</div><h3>${item.title}</h3><p>${item.desc}</p></div>`;
    });
  }

  // Cases
  const cg = document.getElementById('casesGrid');
  if (cg) {
    cg.innerHTML = '';
    const c = t('cases');
    CASES.forEach((cs) => {
      cg.innerHTML += `
        <div class="case-card">
          <div class="case-top" style="background:${cs.color};"></div>
          <div class="case-body">
            <div class="case-header">
              <span class="case-icon">${cs.icon}</span>
              <span class="case-tag" style="color:${cs.color};">${getLocalStr(cs.tag)}</span>
            </div>
            <h3>${getLocalStr(cs.title)}</h3>
            <p>${getLocalStr(cs.desc)}</p>
            <div class="case-footer">
              <div class="case-result" style="border-color:${cs.color};color:${cs.color};">
                ✓ ${getLocalStr(cs.result)}
              </div>
              <div class="case-meta">
                <span>${c.year}: ${cs.year}</span>
                <span>${c.lawyer}: ${cs.lawyer}</span>
              </div>
            </div>
          </div>
        </div>`;
    });
  }

  // Lawyers
  const lg = document.getElementById('lawyersGrid');
  if (lg) {
    lg.innerHTML = '';
    LAWYERS.forEach(l => lg.appendChild(createLawyerCard(l)));
  }

  // News
  const ng = document.getElementById('newsGrid');
  if (ng) {
    ng.innerHTML = '';
    const readLabel = t('news.read');
    NEWS.forEach(n => {
      ng.innerHTML += `
        <a class="news-card" href="${n.url || '#'}" target="_blank" rel="noopener noreferrer">
          <div class="news-card-top" style="background:${n.tagColor};"></div>
          <div class="news-card-body">
            <div class="news-header">
              <span class="news-tag" style="background:${n.tagColor}15;color:${n.tagColor};border-color:${n.tagColor}40;">${getLocalStr(n.tag)}</span>
              <span class="news-date">${getLocalStr(n.date)}</span>
            </div>
            <h3>${getLocalStr(n.title)}</h3>
            <p>${getLocalStr(n.excerpt)}</p>
            <div class="news-footer">
              <span class="news-source">📰 ${n.source}</span>
              <span class="news-read">${readLabel}</span>
            </div>
          </div>
        </a>`;
    });
  }

  // Footer contact info
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  const setHref = (id, val) => { const el = document.getElementById(id); if (el) el.href = val; };
  const addr = typeof FIRM.address === 'object' ? (FIRM.address[currentLang] || FIRM.address.ru) : FIRM.address;
  set('ci-address', addr);
  set('ci-phone1', FIRM.phone1);
  set('ci-phone2', FIRM.phone2);
  set('ci-phone3', FIRM.phone3);
  set('ci-email', FIRM.email);
  setHref('ci-tg', FIRM.telegram);
  setHref('ci-ig', FIRM.instagram);
  setHref('ci-fb', FIRM.facebook);
  setHref('ci-yt', FIRM.youtube);
  set('f-address', addr);
  set('f-email', FIRM.email);
  set('f-phone1', FIRM.phone1);
  set('f-phone2', FIRM.phone2);
  set('f-phone3', FIRM.phone3);
  setHref('f-tg', FIRM.telegram);
  setHref('f-ig', FIRM.instagram);
  setHref('f-fb', FIRM.facebook);
  setHref('f-yt', FIRM.youtube);
  // cases.html footer
  set('f-address-c', addr);
  set('f-email-c', FIRM.email);
  set('f-phone1-c', FIRM.phone1);
  set('f-phone2-c', FIRM.phone2);
  set('f-phone3-c', FIRM.phone3);
}

/* ===== INDEX PAGE ===== */
function initIndex() {
  if (!document.getElementById('heroStats')) return;

  renderDynamic();

  // Smooth scroll
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      const href = a.getAttribute('href');
      if (href === '#') return;
      e.preventDefault();
      const target = document.querySelector(href);
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      document.getElementById('navLinks').classList.remove('open');
    });
  });

  // Intersection observer for scroll animations + counter trigger
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('animate');
        // trigger counter for metric numbers
        entry.target.querySelectorAll('.metric-num[data-target]').forEach(el => {
          animateCounter(el, el.dataset.target, 1200);
        });
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.08 });

  document.querySelectorAll(
    '.service-card, .lawyer-card, .case-card, .news-card, .metric-card, .partner-card'
  ).forEach(el => observer.observe(el));

  // Metric card counter also triggers when section enters view
  const metricObserver = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.querySelectorAll('.metric-num[data-target]').forEach(el => {
          animateCounter(el, el.dataset.target, 1400);
        });
        metricObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.3 });
  const mg = document.getElementById('metricsGrid');
  if (mg) metricObserver.observe(mg);
}

/* ===== LAWYER PAGE ===== */
function initLawyer() {
  if (!document.getElementById('heroName')) return;

  const params = new URLSearchParams(window.location.search);
  const slug = params.get('id');
  const lawyer = LAWYERS.find(l => l.slug === slug);

  if (!lawyer) {
    document.getElementById('heroName').textContent = t('lp.notFound');
    return;
  }
  if (lawyer.externalUrl) {
    window.location.replace(lawyer.externalUrl);
    return;
  }

  document.title = `${getLawyerField(lawyer,'name')} — GSP LAW`;

  const avatar = document.getElementById('heroAvatar');
  if (lawyer.photo) {
    avatar.classList.add('lawyer-avatar-photo');
    avatar.innerHTML = `<img src="${lawyer.photo}" alt="${getLawyerField(lawyer,'name')}">`;
  } else {
    avatar.style.background = lawyer.accentColor;
    avatar.textContent = lawyer.initials;
  }

  document.getElementById('heroTag').textContent = t('lp.heroTag');
  document.getElementById('heroName').textContent = getLawyerField(lawyer,'name');
  document.getElementById('heroTitle').textContent = translateStr(lawyer.title, 'lawyers.titleMap');

  const specsEl = document.getElementById('heroSpecs');
  specsEl.innerHTML = '';
  lawyer.specialization.forEach(s => {
    specsEl.innerHTML += `<span class="spec-tag-hero">${translateStr(s, 'lawyers.specMap')}</span>`;
  });

  document.getElementById('heroMeta').innerHTML = `
    <div class="hero-meta-item"><span>${getLawyerExp(lawyer)}</span><span data-i18n="lp.expLbl">${t('lp.expLbl')}</span></div>
    <div class="hero-meta-item"><span>${lawyer.cases}</span><span data-i18n="lp.casesLbl">${t('lp.casesLbl')}</span></div>
  `;

  document.getElementById('lawyerBio').textContent = getLawyerField(lawyer, 'bio');
  document.getElementById('lawyerDesc').textContent = getLawyerField(lawyer, 'description');
  document.getElementById('lawyerHelp').textContent = getLawyerField(lawyer, 'howIHelp');
  document.getElementById('sideExp').textContent = getLawyerExp(lawyer);
  document.getElementById('sideCases').textContent = lawyer.cases;

  // If lawyer has personal phone, add it to sidebar
  if (lawyer.phone) {
    const contact = document.getElementById('sidebarContact');
    if (contact) {
      const tel = lawyer.phone.replace(/\s/g, '');
      const link = document.createElement('a');
      link.href = `tel:${tel}`;
      link.innerHTML = `<span>📱</span> ${lawyer.phone}`;
      contact.insertBefore(link, contact.firstChild);
    }
  }

  const svc = document.getElementById('lawyerServices');
  const svcData = getLawyerField(lawyer, 'services');
  const svcArr = Array.isArray(svcData) ? svcData : lawyer.services;
  svcArr.forEach(s => {
    svc.innerHTML += `<div class="service-item">${s}</div>`;
  });

  // Education
  const eduEl = document.getElementById('lawyerEducation');
  if (eduEl && lawyer.education) {
    lawyer.education.forEach(e => {
      const deg = getLocalStr(e.degree);
      const inst = getLocalStr(e.institution);
      eduEl.innerHTML += `
        <div class="edu-item">
          <div class="edu-dot-wrap"><div class="edu-dot"></div><div class="edu-line"></div></div>
          <div class="edu-content">
            <div class="edu-year">${e.year}</div>
            <div class="edu-degree">${deg}</div>
            <div class="edu-institution">${inst}</div>
          </div>
        </div>`;
    });
  }

  // Achievements
  const achEl = document.getElementById('lawyerAchievements');
  if (achEl && lawyer.achievements) {
    const achData = getLawyerField(lawyer, 'achievements');
    const achArr = Array.isArray(achData) ? achData : lawyer.achievements;
    achArr.forEach(a => {
      achEl.innerHTML += `<li>${a}</li>`;
    });
  }

  // Publications
  const pubEl = document.getElementById('lawyerPublications');
  if (pubEl && lawyer.publications) {
    const openLabel = { ru: 'Открыть', uz: 'Ochish', en: 'Open' };
    lawyer.publications.forEach(p => {
      const inner = `
        <div class="pub-title">${p.title}</div>
        <div class="pub-meta">
          <span class="pub-journal">${p.journal}</span>
          <span class="pub-year">${p.year}</span>
          ${p.url ? `<span class="pub-link">↗ ${openLabel[currentLang] || 'Открыть'}</span>` : ''}
        </div>`;
      if (p.url) {
        pubEl.innerHTML += `<a class="pub-item pub-item-link" href="${p.url}" target="_blank" rel="noopener noreferrer">${inner}</a>`;
      } else {
        pubEl.innerHTML += `<div class="pub-item">${inner}</div>`;
      }
    });
  }

  // Certificates
  const certSection = document.getElementById('sectionCertificates');
  const certEl = document.getElementById('lawyerCertificates');
  if (certSection && certEl && lawyer.certificates && lawyer.certificates.length > 0) {
    certSection.style.display = '';
    const viewLabel = { ru: 'Открыть оригинал', uz: "Aslini ochish", en: 'Open original' };
    lawyer.certificates.forEach(c => {
      const titleStr = (typeof c.title === 'object') ? (c.title[currentLang] || c.title.ru) : c.title;
      certEl.innerHTML += `
        <div class="cert-card">
          <a href="${c.file}" target="_blank" rel="noopener noreferrer" class="cert-img-wrap">
            <img src="${c.image}" alt="${titleStr}" class="cert-img" loading="lazy">
            <div class="cert-img-overlay"><span>↗ ${viewLabel[currentLang]}</span></div>
          </a>
          <div class="cert-card-footer">
            <span class="cert-card-title">${titleStr}</span>
          </div>
        </div>`;
    });
  }

  document.getElementById('blogTitle').textContent = getLawyerField(lawyer,'name').split(' ')[0];
  const blog = document.getElementById('blogGrid');
  lawyer.blog.forEach(post => {
    blog.innerHTML += `
      <div class="blog-card">
        <div class="blog-card-top" style="background:${lawyer.accentColor};"></div>
        <div class="blog-card-body">
          <p class="blog-tag">${post.tag}</p>
          <h3>${post.title}</h3>
          <p>${post.excerpt}</p>
          <div class="blog-card-footer">
            <span>${post.date}</span>
            <span class="blog-read-more" data-i18n="lp.readMore">${t('lp.readMore')}</span>
          </div>
        </div>
      </div>`;
  });

  const others = LAWYERS.filter(l => l.slug !== slug && !l.externalUrl).slice(0, 4);
  const og = document.getElementById('otherLawyers');
  others.forEach(l => og.appendChild(createLawyerCard(l)));

  applyI18n();
}

/* ===== CASES PAGE ===== */
function initCasesPage() {
  if (!document.getElementById('casesDetailGrid')) return;

  applyI18n();

  // Hero stats
  const hStats = document.getElementById('casesHeroStats');
  if (hStats) {
    const c = t('cases');
    hStats.innerHTML = `
      <div class="cases-hero-stat"><strong>${CASES.length}</strong><span>${c.sTag || 'Кейсов'}</span></div>
      <div class="cases-hero-stat"><strong>94%</strong><span>${t('metrics.winRate')}</span></div>
      <div class="cases-hero-stat"><strong>$250M+</strong><span>${t('metrics.portfolioVal')}</span></div>
    `;
  }

  // Build unique filter tags
  const allTags = CASES.map((cs) => getLocalStr(cs.tag));
  const uniqueTags = [...new Set(allTags)];

  const filtersEl = document.getElementById('casesFilters');
  const cp = t('casesPage');
  filtersEl.innerHTML = `<button class="filter-btn active" data-filter="all">${cp.filterAll || 'All'}</button>`;
  uniqueTags.forEach(tag => {
    filtersEl.innerHTML += `<button class="filter-btn" data-filter="${tag}">${tag}</button>`;
  });

  filtersEl.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      filtersEl.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const filter = btn.dataset.filter;
      document.querySelectorAll('.case-detail-card').forEach(card => {
        if (filter === 'all' || card.dataset.tag === filter) {
          card.classList.remove('hidden');
        } else {
          card.classList.add('hidden');
        }
      });
    });
  });

  // Render detail cards
  const grid = document.getElementById('casesDetailGrid');
  CASES.forEach((cs) => {
    const tag = getLocalStr(cs.tag);
    const card = document.createElement('div');
    card.className = 'case-detail-card';
    card.dataset.tag = tag;
    card.innerHTML = `
      <div class="case-detail-top" style="background:${cs.color};"></div>
      <div class="case-detail-body">
        <div class="case-detail-header">
          <span class="case-detail-icon">${cs.icon}</span>
          <span class="case-detail-tag" style="background:${cs.color}15;color:${cs.color};border-color:${cs.color}40;">${tag}</span>
        </div>
        <h3>${getLocalStr(cs.title)}</h3>
        <div class="case-detail-meta">
          <div class="case-detail-meta-item">
            <span class="meta-label">${cp.durationLabel || 'Длительность'}</span>
            <span class="meta-val">${getLocalStr(cs.duration)}</span>
          </div>
          <div class="case-detail-meta-item">
            <span class="meta-label">${cp.jurLabel || 'Юрисдикция'}</span>
            <span class="meta-val">${getLocalStr(cs.jurisdiction)}</span>
          </div>
          <div class="case-detail-meta-item">
            <span class="meta-label">${cp.lawyerLabel || 'Адвокат'}</span>
            <span class="meta-val">${cs.lawyer}</span>
          </div>
          <div class="case-detail-meta-item">
            <span class="meta-label">${t('cases.year')}</span>
            <span class="meta-val">${cs.year}</span>
          </div>
        </div>
        <div class="case-detail-sections">
          <div class="case-detail-section-block">
            <h4>${cp.challenge || 'Задача'}</h4>
            <p>${getLocalStr(cs.challenge)}</p>
          </div>
          <div class="case-detail-section-block">
            <h4>${cp.approach || 'Наш подход'}</h4>
            <p>${getLocalStr(cs.approach)}</p>
          </div>
        </div>
        <div class="case-detail-result" style="background:${cs.color}12;color:${cs.color};">
          ✓ ${getLocalStr(cs.result)}
        </div>
      </div>`;
    grid.appendChild(card);
  });

  // Animate cards on scroll
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('animate');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.06 });
  document.querySelectorAll('.case-detail-card').forEach(el => observer.observe(el));
}

/* ===== INIT ===== */
document.addEventListener('DOMContentLoaded', () => {
  applyI18n();
  initIndex();
  initLawyer();
});
