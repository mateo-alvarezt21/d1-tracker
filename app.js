(() => {
  'use strict';

  // ===== State =====
  const state = {
    view: 'landing',
    loading: false,
    loadingMsg: '',
    step: 1,
    budget: 150000,
    days: 7,
    people: 4,
    calories: 2000,
    diet: [],
    checked: {},
    recipe: null,
    copied: false,
  };

  let loadingTimer = null;
  let loadingMsgTimer = null;
  let copiedTimer = null;

  // ===== Datos reales de D1 (generados en app-data.js desde data/d1_catalog.json) =====
  const D = window.D1_DATA || {};
  const dietList = D.dietList;
  const dayNames = D.dayNames;
  const recipes = D.recipes;
  const products = D.products;
  const mealPools = D.mealPools;
  const mealTypes = D.mealTypes;
  const catOrder = D.catOrder;

  // ===== Helpers =====
  function fmt(n) { return '$' + Math.round(n).toLocaleString('es-CO'); }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  // ===== Plan sensible al presupuesto =====
  // Modos ordenados de más completo a más austero. Se elige el más completo
  // cuya lista de compras QUEPA en el presupuesto. Si ni el más austero cabe,
  // se muestra igual el austero y se avisa que se excede. Con poca plata el
  // plan se repite y se vuelve sencillo; con más, gana variedad y platos fuertes.
  const PLAN_MODES = [
    { key: 'holgado',   label: 'Plan completo',  tierOf: () => 'estandar',                                   width: 99 },
    { key: 'mixto',     label: 'Plan balanceado', tierOf: (t) => (t === 'Almuerzo' ? 'estandar' : 'economica'), width: 3 },
    { key: 'economico', label: 'Plan económico',  tierOf: () => 'economica',                                  width: 2 },
    { key: 'austero',   label: 'Plan austero',    tierOf: () => 'economica',                                  width: 1 },
  ];

  // Porción del día = (personas / 2)  ×  factor calórico.
  // Las recetas son porciones base modestas; para llegar a la meta de kcal/día
  // se sirven porciones más grandes (más arroz/pasta/panela = calorías baratas).
  // El factor se acota para evitar extremos poco realistas.
  const CAL_MIN = 0.6, CAL_MAX = 3;
  function dayPortion(baseCal) {
    const calFactor = Math.min(CAL_MAX, Math.max(CAL_MIN, state.calories / Math.max(1, baseCal)));
    return { calFactor, portion: Math.max(0.25, (state.people / 2) * calFactor) };
  }

  function pickMeal(type, tier, dayIdx, width) {
    const pool = (mealPools[tier] && mealPools[tier][type]) || [];
    const fallback = (mealPools.estandar && mealPools.estandar[type]) || [];
    const list = pool.length ? pool : fallback;
    const w = Math.max(1, Math.min(width, list.length));
    return list[dayIdx % w];
  }

  function planForMode(mode) {
    return Array.from({ length: state.days }, (_, i) => {
      const ids = mealTypes.map((type) => pickMeal(type, mode.tierOf(type), i, mode.width));
      const baseCal = ids.reduce((a, id) => a + recipes[id].cal, 0);
      const { calFactor, portion } = dayPortion(baseCal);
      const meals = ids.map((id) => {
        const r = recipes[id];
        const cal = Math.round(r.cal * calFactor);
        return { id, type: r.type, name: r.name, cal, calLabel: cal + ' kcal', costLabel: fmt(r.cost * portion) };
      });
      const dayCal = Math.round(baseCal * calFactor);
      const subtotal = ids.reduce((a, id) => a + recipes[id].cost * portion, 0);
      return { name: dayNames[i % 7], num: i + 1, meals, dayCal, portion, subtotalLabel: fmt(subtotal) };
    });
  }

  // La lista de compras se DERIVA del plan: suma los ingredientes reales
  // (fracción de paquete × porción del día) de cada plato. Plan y lista cuadran.
  function basketFromPlan(plan) {
    const usage = {}; // sku -> paquetes (fraccionarios) necesarios
    plan.forEach((day) => day.meals.forEach((meal) => {
      (recipes[meal.id].ing || []).forEach(({ sku, frac }) => {
        usage[sku] = (usage[sku] || 0) + frac * day.portion;
      });
    }));
    const byCat = {};
    Object.keys(usage).forEach((sku) => {
      const p = products[sku];
      if (!p) return;
      const qty = Math.max(1, Math.ceil(usage[sku]));
      const item = { id: sku, name: p.name, unit: 'und', price: p.price, qty, sub: qty * p.price, tienda: !!p.tienda };
      (byCat[p.cat] = byCat[p.cat] || []).push(item);
    });
    return catOrder
      .filter((c) => byCat[c])
      .map((c) => ({ name: c, items: byCat[c].sort((a, b) => b.sub - a.sub) }));
  }

  function basketCost(basket) {
    return basket.reduce((a, cat) => a + cat.items.reduce((b, it) => b + it.sub, 0), 0);
  }

  // Elige el modo más completo cuya lista quepa en el presupuesto.
  // Devuelve { mode, plan, basket, cost, over }.
  function resolvePlan() {
    let last = null;
    for (const mode of PLAN_MODES) {
      const plan = planForMode(mode);
      const basket = basketFromPlan(plan);
      const cost = basketCost(basket);
      last = { mode, plan, basket, cost, over: cost > state.budget };
      if (cost <= state.budget) return last;
    }
    return last; // ni el más austero cabe: se muestra igual y se avisa
  }

  function computePlan() { return resolvePlan().plan; }
  function computeBasket() { return resolvePlan().basket; }

  function computeFeasibility(shopData) {
    const estFull = shopData.reduce((a, cat) => a + cat.items.reduce((b, it) => b + it.sub, 0), 0);
    const budgetOk = state.budget >= estFull;
    const shortfall = Math.max(0, estFull - state.budget);
    const perDayCost = estFull / state.days;
    const affordableDays = Math.max(1, Math.floor(state.budget / perDayCost));
    const suggestedBudget = Math.ceil(estFull / 1000) * 1000;
    return { estFull, budgetOk, shortfall, affordableDays, suggestedBudget };
  }

  function computeTotals(shopData) {
    const total = shopData.reduce((a, cat) => a + cat.items.reduce((b, it) => b + (state.checked[it.id] ? 0 : it.sub), 0), 0);
    const over = total > state.budget;
    const pct = Math.min(100, (total / state.budget) * 100);
    const barColor = over ? '#E30613' : '#1aa563';
    const totalColor = over ? '#E30613' : '#1aa563';
    const diff = Math.abs(state.budget - total);
    const budgetMsg = over
      ? ('Te excedes por ' + fmt(diff) + ' — reduce días/personas o marca lo que ya tienes.')
      : ('Te quedan ' + fmt(diff) + ' dentro del presupuesto');
    return { total, over, pct, barColor, totalColor, budgetMsg };
  }

  function copyList() {
    const data = computeBasket();
    let out = '🛒 MI CANASTA D1 — Lista de compras\n' + state.days + (state.days === 1 ? ' día' : ' días') + ' · ' + state.people + (state.people === 1 ? ' persona' : ' personas') + '\n';
    let total = 0;
    data.forEach((cat) => {
      const items = cat.items.filter((it) => !state.checked[it.id]);
      if (!items.length) return;
      out += '\n' + cat.name.toUpperCase() + '\n';
      items.forEach((it) => { total += it.sub; out += '• ' + it.name + '  (x' + it.qty + ')  ' + fmt(it.sub) + '\n'; });
    });
    out += '\nTOTAL: ' + fmt(total) + '  ·  Presupuesto: ' + fmt(state.budget) + '\n';
    const done = () => {
      state.copied = true;
      renderCopyButtons();
      clearTimeout(copiedTimer);
      copiedTimer = setTimeout(() => { state.copied = false; renderCopyButtons(); }, 2200);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(out).then(done).catch(() => fallbackCopy(out, done));
    } else {
      fallbackCopy(out, done);
    }
  }
  function fallbackCopy(text, done) {
    try {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      done();
    } catch (e) { /* clipboard unavailable */ }
  }

  // runLoading acepta un mensaje o una lista de mensajes que van rotando para
  // dar sensación de trabajo (aunque el cálculo sea instantáneo).
  function runLoading(msgs, after) {
    const list = Array.isArray(msgs) ? msgs.slice() : [msgs];
    const stepMs = 620;
    state.loading = true;
    state.loadingMsg = list[0];
    renderLoading();
    clearTimeout(loadingTimer);
    clearInterval(loadingMsgTimer);
    let idx = 0;
    loadingMsgTimer = setInterval(() => {
      idx += 1;
      if (idx < list.length) { state.loadingMsg = list[idx]; renderLoading(); }
    }, stepMs);
    const total = Math.max(1500, list.length * stepMs + 150);
    loadingTimer = setTimeout(() => {
      clearInterval(loadingMsgTimer);
      state.loading = false;
      renderLoading();
      after();
    }, total);
  }

  // ===== DOM refs =====
  const el = {
    landing: document.getElementById('landing'),
    appView: document.getElementById('app-view'),
    startAppBtn: document.getElementById('start-app-btn'),
    logoHome: document.getElementById('logo-home'),
    headerChipText: document.getElementById('header-chip-text'),
    progressSteps: document.getElementById('progress-steps'),
    step1: document.getElementById('step1'),
    step2: document.getElementById('step2'),
    step3: document.getElementById('step3'),
    budgetInput: document.getElementById('budget-input'),
    budgetHelper: document.getElementById('budget-helper'),
    dayPills: document.getElementById('day-pills'),
    peoplePills: document.getElementById('people-pills'),
    calValue: document.getElementById('cal-value'),
    calorieSlider: document.getElementById('calorie-slider'),
    dietPills: document.getElementById('diet-pills'),
    feasibilityCard: document.getElementById('feasibility-card'),
    generateBtn: document.getElementById('generate-btn'),
    loadingOverlay: document.getElementById('loading-overlay'),
    loadingMsg: document.getElementById('loading-msg'),
    recipeOverlay: document.getElementById('recipe-overlay'),
    recipePanel: document.getElementById('recipe-panel'),
    recipeMeta: document.getElementById('recipe-meta'),
    recipeName: document.getElementById('recipe-name'),
    recipeNutrition: document.getElementById('recipe-nutrition'),
    recipeIngredients: document.getElementById('recipe-ingredients'),
    recipeClose: document.getElementById('recipe-close'),
  };

  function daysLabel() { return state.days + ' días'; }
  function peopleLabel() { return state.people + (state.people === 1 ? ' persona' : ' personas'); }

  // ===== Render: view switch =====
  function renderViewSwitch() {
    el.landing.classList.toggle('hidden', state.view !== 'landing');
    el.appView.classList.toggle('hidden', state.view !== 'app');
  }

  // ===== Render: header =====
  function renderHeader() {
    el.headerChipText.textContent = peopleLabel() + ' · ' + daysLabel();

    const labels = ['Configurar', 'Lista', 'Plan', 'Recetas'];
    el.progressSteps.innerHTML = labels.map((label, i) => {
      const num = i + 1;
      const active = num === 4 ? !!state.recipe : (state.step === num && !state.recipe);
      const done = num < 4 && state.step > num;
      const accent = active ? '#E30613' : (done ? '#1A1A1A' : '#ccc');
      const labelWeight = active ? '900' : '700';
      const labelColor = active ? '#1A1A1A' : '#999';
      const connector = num < 4
        ? '<div class="progress-connector" style="background:' + (done ? '#1A1A1A' : '#eee') + ';"></div>'
        : '';
      return (
        '<div class="progress-step">' +
          '<button class="progress-btn" data-step-nav="' + num + '">' +
            '<span class="progress-num" style="background:' + accent + ';">' + num + '</span>' +
            '<span class="progress-label" style="font-weight:' + labelWeight + '; color:' + labelColor + ';">' + label + '</span>' +
          '</button>' +
          connector +
        '</div>'
      );
    }).join('');
  }

  // ===== Render: Step 1 =====
  function renderPillRow(container, count, current, attr) {
    container.innerHTML = Array.from({ length: count }, (_, i) => i + 1).map((v) =>
      '<button class="pill-btn' + (v === current ? ' active' : '') + '" data-' + attr + '="' + v + '">' + v + '</button>'
    ).join('');
  }

  function renderDietPills() {
    el.dietPills.innerHTML = dietList.map((label) => {
      const active = state.diet.includes(label);
      return '<button class="diet-pill' + (active ? ' active' : '') + '" data-diet="' + escapeHtml(label) + '">' + escapeHtml(label) + '</button>';
    }).join('');
  }

  function renderFeasibility() {
    const shopData = computeBasket();
    const { estFull, budgetOk, shortfall, affordableDays, suggestedBudget } = computeFeasibility(shopData);
    const totalColor = budgetOk ? '#1aa563' : '#E30613';
    const perPersonDay = estFull / (state.days * state.people);

    let html = '';
    html += '<div class="feasibility-head">';
    html += '<span class="feasibility-label">Costo estimado del plan</span>';
    html += '<span class="feasibility-total" style="color:' + totalColor + ';">' + fmt(estFull) + '</span>';
    html += '</div>';
    html += '<div class="feasibility-sub">≈ ' + fmt(perPersonDay) + ' por persona al día</div>';

    if (budgetOk) {
      html += '<div class="feasibility-ok">' +
        '<span class="feasibility-ok-icon">✓</span>' +
        '<span class="feasibility-ok-text">¡Te alcanza! Tu presupuesto cubre este mercado y te sobran ' + fmt(state.budget - estFull) + '.</span>' +
        '</div>';
    } else {
      const affordableDaysLabel = affordableDays + (affordableDays === 1 ? ' día' : ' días');
      html += '<div class="feasibility-low">' +
        '<div class="feasibility-low-row">' +
          '<span class="feasibility-low-icon">⚠</span>' +
          '<div>' +
            '<div class="feasibility-low-title">Este presupuesto no alcanza</div>' +
            '<div class="feasibility-low-text">Te faltan <b>' + fmt(shortfall) + '</b> para cubrir ' + daysLabel() + ' con ' + peopleLabel() + '. Con lo que tienes alcanzaría para unos <b>' + affordableDaysLabel + '</b>.</div>' +
          '</div>' +
        '</div>' +
        '<div class="feasibility-actions">' +
          '<button class="btn-fix-budget" data-action="fix-budget" data-value="' + suggestedBudget + '">Subir a ' + fmt(suggestedBudget) + '</button>' +
          '<button class="btn-fix-days" data-action="fix-days" data-value="' + affordableDays + '">Ajustar a ' + affordableDaysLabel + '</button>' +
        '</div>' +
      '</div>';
    }
    el.feasibilityCard.innerHTML = html;
  }

  function renderStep1() {
    if (el.budgetInput.value !== String(state.budget)) el.budgetInput.value = state.budget;
    el.budgetHelper.textContent = fmt(state.budget) + ' COP disponibles';
    renderPillRow(el.dayPills, 31, state.days, 'days');
    renderPillRow(el.peoplePills, 8, state.people, 'people');
    renderDietPills();

    const sliderVal = String(state.calories);
    if (el.calorieSlider.value !== sliderVal) el.calorieSlider.value = sliderVal;
    const pct = ((state.calories - 1200) / (3000 - 1200)) * 100;
    el.calorieSlider.style.setProperty('--p', pct + '%');
    el.calValue.innerHTML = state.calories.toLocaleString('es-CO') + ' <span class="cal-unit">kcal</span>';

    renderFeasibility();
  }

  // ===== Render: Plan de comidas (paso 3) =====
  const BUDGET_NOTE = {
    holgado: { icon: '🍽️', text: 'Buen presupuesto: platos variados y completos para toda la semana.' },
    mixto: { icon: '⚖️', text: 'Presupuesto medido: almuerzos completos y desayunos/cenas más sencillos para que rinda.' },
    economico: { icon: '💪', text: 'Presupuesto ajustado: plan económico con platos sencillos y rendidores (arroz con huevo, lenteja, pasta).' },
    austero: { icon: '🫘', text: 'Presupuesto muy ajustado: repetimos los platos más sencillos y baratos para que rinda al máximo.' },
  };
  function renderPlanView() {
    const resolved = resolvePlan();
    const plan = resolved.plan;
    const note = BUDGET_NOTE[resolved.mode.key] || BUDGET_NOTE.economico;
    let html = '';
    html += '<div class="step2-head">';
    html += '<div><h1 class="step2-title">Tu plan de comidas</h1>';
    html += '<p class="step2-sub">' + daysLabel() + ' · ' + peopleLabel() + ' · objetivo ' + state.calories + ' kcal/día</p></div>';
    html += '<button class="btn-go-shopping" data-action="go-list">← Volver a la lista</button>';
    html += '</div>';
    html += '<div class="plan-budget-note"><span class="plan-budget-icon">' + note.icon + '</span><span>' + note.text + '</span></div>';
    if (resolved.over) {
      html += '<div class="plan-budget-warn"><span class="plan-budget-icon">⚠️</span><span>Aun con el plan más austero te excedes por <b>' + fmt(resolved.cost - state.budget) + '</b>. Sube el presupuesto o reduce los días.</span></div>';
    }
    // Resumen calórico: promedio real del plan vs la meta del usuario.
    const avgCal = Math.round(plan.reduce((a, d) => a + d.dayCal, 0) / Math.max(1, plan.length));
    const calOk = avgCal >= state.calories * 0.95;
    html += '<div class="plan-cal-note ' + (calOk ? 'ok' : 'warn') + '">' +
      '<span class="plan-budget-icon">' + (calOk ? '✅' : '⚠️') + '</span>' +
      '<span>Aporta <b>~' + avgCal.toLocaleString('es-CO') + ' kcal/día</b> por persona (tu meta: ' + state.calories.toLocaleString('es-CO') + ' kcal). ' +
      (calOk ? 'Cumple tu meta.' : 'No llega a la meta ni con porciones grandes — baja la meta o sube el presupuesto.') +
      '</span></div>';
    html += '<div class="plan-row">';
    plan.forEach((day) => {
      html += '<div class="day-card">';
      html += '<div class="day-card-head"><span class="day-card-name">' + day.name + '</span><span class="day-card-num">Día ' + day.num + '</span></div>';
      html += '<div class="day-card-meals">';
      day.meals.forEach((meal) => {
        html += '<div class="meal-card">' +
          '<div class="meal-top"><span class="meal-type">' + meal.type + '</span><span class="meal-cal-badge">' + meal.calLabel + '</span></div>' +
          '<div class="meal-name">' + escapeHtml(meal.name) + '</div>' +
          '<div class="meal-bottom"><span class="meal-cost">' + meal.costLabel + '</span>' +
          '<a class="meal-recipe-link" data-action="open-recipe" data-recipe="' + meal.id + '">Ver receta →</a></div>' +
        '</div>';
      });
      html += '</div>';
      html += '<div class="day-card-foot"><span class="day-card-foot-label">Subtotal · ' + day.dayCal.toLocaleString('es-CO') + ' kcal</span><span class="day-card-foot-value">' + day.subtotalLabel + '</span></div>';
      html += '</div>';
    });
    html += '</div>';
    el.step3.innerHTML = html;
  }

  // ===== Render: Lista de compras (paso 2, antes del plan) =====
  function renderShoppingView() {
    const shopData = computeBasket();
    const { totalColor, total, pct, barColor, budgetMsg } = computeTotals(shopData);

    let html = '<div class="step3-inner">';
    html += '<div class="step3-head">';
    html += '<div style="flex:1; min-width:200px;"><h1 class="step3-title">Lista de compras</h1>';
    html += '<p class="step3-sub">Marca lo que ya tienes en casa para ajustar el total.</p></div>';
    html += '<div class="step3-head-btns">';
    html += '<button class="btn-copy' + (state.copied ? ' copied' : '') + '" data-action="copy-list">' + (state.copied ? '¡Copiado! ✓' : 'Copiar lista 📋') + '</button>';
    html += '<button class="btn-go-plan" data-action="go-plan">Ver plan de comidas →</button>';
    html += '</div>';
    html += '</div>';

    // Aviso claro e intuitivo según si el mercado cabe o no en el presupuesto.
    const over = total > state.budget;
    const diff = Math.abs(state.budget - total);
    if (over) {
      html += '<div class="list-aviso warn">' +
        '<span class="plan-budget-icon">⚠️</span>' +
        '<span>Este mercado cuesta <b>' + fmt(total) + '</b> y tu presupuesto es <b>' + fmt(state.budget) + '</b> — te faltan <b>' + fmt(diff) + '</b>. ' +
        'Marca abajo lo que ya tengas en casa, reduce los días o sube el presupuesto.</span></div>';
    } else {
      html += '<div class="list-aviso ok">' +
        '<span class="plan-budget-icon">✅</span>' +
        '<span>¡Tu mercado cabe en el presupuesto! Cuesta <b>' + fmt(total) + '</b> y te sobran <b>' + fmt(diff) + '</b>.</span></div>';
    }

    html += '<div class="cat-list">';
    shopData.forEach((cat) => {
      html += '<div class="cat-card">';
      html += '<div class="cat-head"><span class="cat-dot"></span><span class="cat-name">' + cat.name + '</span><span class="cat-count">' + cat.items.length + ' productos</span></div>';
      cat.items.forEach((it) => {
        const have = !!state.checked[it.id];
        html += '<div class="item-row' + (have ? ' have' : '') + '" data-action="toggle-item" data-id="' + it.id + '">' +
          '<div class="item-box' + (have ? ' have' : '') + '">' + (have ? '✓' : '') + '</div>' +
          '<div class="item-name-col">' +
            '<div class="item-name' + (have ? ' have' : '') + '">' + escapeHtml(it.name) + '</div>' +
            '<div class="item-qty">x' + it.qty + ' ' + it.unit + ' · ' + fmt(it.price) + ' c/u' + (it.tienda ? ' <span class="item-tienda">tienda</span>' : '') + '</div>' +
          '</div>' +
          '<div class="item-sub' + (have ? ' have' : '') + '">' + fmt(it.sub) + '</div>' +
        '</div>';
      });
      html += '</div>';
    });
    html += '</div></div>';

    html += '<div class="sticky-bar"><div class="sticky-bar-inner">';
    html += '<div class="sticky-top">';
    html += '<div><span class="sticky-total-label">Total estimado</span><span class="sticky-total-value" style="color:' + totalColor + ';">' + fmt(total) + '</span></div>';
    html += '<div><div class="sticky-budget-label">Presupuesto</div><div class="sticky-budget-value">' + fmt(state.budget) + '</div></div>';
    html += '</div>';
    html += '<div class="sticky-bar-track"><div class="sticky-bar-fill" style="width:' + pct + '%; background:' + barColor + ';"></div></div>';
    html += '<div class="sticky-bottom">';
    html += '<div class="sticky-budget-msg" style="color:' + totalColor + ';">' + budgetMsg + '</div>';
    html += '<button class="btn-go-plan" data-action="go-plan">Ver plan de comidas →</button>';
    html += '</div></div></div>';

    el.step2.innerHTML = html;
  }

  function renderCopyButtons() {
    document.querySelectorAll('[data-action="copy-list"]').forEach((btn) => {
      btn.classList.toggle('copied', state.copied);
      btn.textContent = state.copied ? '¡Copiado! ✓' : 'Copiar lista 📋';
    });
  }

  // ===== Render: step panel visibility =====
  function renderStepPanels() {
    el.step1.classList.toggle('hidden', state.step !== 1);
    el.step2.classList.toggle('hidden', state.step !== 2);
    el.step3.classList.toggle('hidden', state.step !== 3);
    if (state.step === 1) renderStep1();
    if (state.step === 2) renderShoppingView();
    if (state.step === 3) renderPlanView();
  }

  // ===== Render: loading =====
  function renderLoading() {
    el.loadingOverlay.classList.toggle('hidden', !state.loading);
    el.loadingMsg.textContent = state.loadingMsg;
  }

  // ===== Render: recipe modal =====
  function renderRecipe() {
    const open = !!state.recipe;
    el.recipeOverlay.classList.toggle('hidden', !open);
    if (!open) return;
    const r = recipes[state.recipe];
    el.recipeMeta.textContent = r.type + ' · ' + r.time;
    el.recipeName.textContent = r.name;
    el.recipeNutrition.innerHTML =
      '<div class="nut-cell cal"><div class="nut-value">' + r.cal + '</div><div class="nut-label">kcal</div></div>' +
      '<div class="nut-cell"><div class="nut-value">' + r.nut.protein + '</div><div class="nut-label">Proteína</div></div>' +
      '<div class="nut-cell"><div class="nut-value">' + r.nut.carbs + '</div><div class="nut-label">Carbos</div></div>' +
      '<div class="nut-cell"><div class="nut-value">' + r.nut.fat + '</div><div class="nut-label">Grasa</div></div>';
    el.recipeIngredients.innerHTML = r.ingredients.map((ing) =>
      '<div class="ing-row"><span class="dot-yellow-tiny"></span><span class="ing-text">' + escapeHtml(ing) + '</span></div>'
    ).join('');
  }

  // ===== Master render (for things touched by multiple actions) =====
  function render() {
    renderViewSwitch();
    renderHeader();
    renderStepPanels();
    renderLoading();
    renderRecipe();
  }

  // ===== Actions =====
  function setStep(n) { state.step = n; state.recipe = null; render(); }

  el.startAppBtn.addEventListener('click', () => {
    runLoading(['Preparando tu canasta…', 'Abriendo las tiendas D1…', 'Ya casi…'],
      () => { state.view = 'app'; state.step = 1; render(); });
    render();
  });

  el.logoHome.addEventListener('click', () => { state.view = 'landing'; state.recipe = null; render(); });

  el.generateBtn.addEventListener('click', () => {
    runLoading(
      ['Generando tu lista…', 'Investigando en el supermercado D1…', 'Comparando precios reales…', 'Cuadrando tu presupuesto…', 'Ya casi…'],
      () => { setStep(2); });
    render();
  });

  el.budgetInput.addEventListener('input', (e) => {
    state.budget = parseInt(e.target.value || '0', 10) || 0;
    el.budgetHelper.textContent = fmt(state.budget) + ' COP disponibles';
    renderFeasibility();
  });

  el.calorieSlider.addEventListener('input', (e) => {
    state.calories = parseInt(e.target.value, 10);
    const pct = ((state.calories - 1200) / (3000 - 1200)) * 100;
    el.calorieSlider.style.setProperty('--p', pct + '%');
    el.calValue.innerHTML = state.calories.toLocaleString('es-CO') + ' <span class="cal-unit">kcal</span>';
    renderFeasibility(); // el costo ahora depende de la meta calórica
  });

  el.dayPills.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-days]');
    if (!btn) return;
    state.days = parseInt(btn.dataset.days, 10);
    renderStep1();
  });

  el.peoplePills.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-people]');
    if (!btn) return;
    state.people = parseInt(btn.dataset.people, 10);
    renderStep1();
  });

  el.dietPills.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-diet]');
    if (!btn) return;
    const label = btn.dataset.diet;
    const idx = state.diet.indexOf(label);
    if (idx === -1) state.diet.push(label); else state.diet.splice(idx, 1);
    renderDietPills();
  });

  el.feasibilityCard.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-action]');
    if (!btn) return;
    if (btn.dataset.action === 'fix-budget') {
      state.budget = parseInt(btn.dataset.value, 10);
      renderStep1();
    } else if (btn.dataset.action === 'fix-days') {
      state.days = parseInt(btn.dataset.value, 10);
      renderStep1();
    }
  });

  el.progressSteps.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-step-nav]');
    if (!btn) return;
    const num = parseInt(btn.dataset.stepNav, 10);
    if (num === 4) {
      runLoading(['Abriendo la receta…', 'Alistando los ingredientes…'], () => { state.recipe = 'l1'; render(); });
    } else {
      setStep(num);
    }
  });

  // Paso 2 = Lista de compras
  el.step2.addEventListener('click', (e) => {
    const copyBtn = e.target.closest('[data-action="copy-list"]');
    if (copyBtn) { copyList(); return; }
    const goPlan = e.target.closest('[data-action="go-plan"]');
    if (goPlan) {
      runLoading(
        ['Armando tu plan de comidas…', 'Eligiendo las mejores recetas…', 'Cuadrando calorías y presupuesto…', 'Ya casi…'],
        () => setStep(3));
      return;
    }
    const toggleRow = e.target.closest('[data-action="toggle-item"]');
    if (toggleRow) {
      const id = toggleRow.dataset.id;
      state.checked[id] = !state.checked[id];
      renderShoppingView();
    }
  });

  // Paso 3 = Plan de comidas
  el.step3.addEventListener('click', (e) => {
    const goList = e.target.closest('[data-action="go-list"]');
    if (goList) { setStep(2); return; }
    const recipeLink = e.target.closest('[data-action="open-recipe"]');
    if (recipeLink) {
      const id = recipeLink.dataset.recipe;
      runLoading(['Abriendo la receta…', 'Alistando los ingredientes…'], () => { state.recipe = id; render(); });
    }
  });

  el.recipeOverlay.addEventListener('click', (e) => {
    if (e.target === el.recipeOverlay) { state.recipe = null; render(); }
  });
  el.recipeClose.addEventListener('click', () => { state.recipe = null; render(); });

  // ===== Init =====
  render();
})();
