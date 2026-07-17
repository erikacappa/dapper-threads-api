<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Custom Card Skin Designer &middot; Dapper Threads</title>
<style>
  :root{
    --ink:#2b2420; --paper:#faf6ef; --line:#e4dccb; --accent:#8a6a3b; --accent-dark:#5c4526;
    --danger:#b0442f; --ok:#3c6e4f;
  }
  *{box-sizing:border-box;}
  body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;background:var(--paper);color:var(--ink);}
  header{display:flex;align-items:center;justify-content:space-between;padding:18px 32px;border-bottom:1px solid var(--line);background:#fff;}
  .brand{display:flex;align-items:baseline;gap:14px;}
  .brand h1{font-size:20px;margin:0;letter-spacing:.5px;}
  .brand span{font-size:11px;letter-spacing:2px;color:#8a7f6c;display:block;text-transform:uppercase;}
  .brand .sub{font-size:13px;color:#8a7f6c;border-left:1px solid var(--line);padding-left:14px;}
  header a.shop{font-size:13px;color:var(--accent-dark);text-decoration:none;border:1px solid var(--line);padding:8px 14px;border-radius:6px;}
  main{max-width:1100px;margin:0 auto;padding:28px 24px 80px;}
  .notice{background:#fbeee9;border:1px solid #eccdc2;color:#7a3222;padding:14px 16px;border-radius:8px;font-size:14px;margin-bottom:26px;}
  .notice a{color:#7a3222;font-weight:600;}
  section.block{margin-bottom:28px;}
  .step-head{display:flex;align-items:center;gap:12px;margin-bottom:14px;}
  .step-num{width:26px;height:26px;border-radius:50%;background:var(--ink);color:#fff;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:600;flex:none;}
  .step-title{font-size:15px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;}
  .step-desc{font-size:13px;color:#7a7060;margin:2px 0 16px 38px;}
  .card{background:#fff;border:1px solid var(--line);border-radius:10px;padding:22px;}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
  label.field{display:block;font-size:11px;font-weight:700;letter-spacing:.6px;text-transform:uppercase;color:#8a7f6c;margin-bottom:6px;}
  input[type=text],input[type=email],input[type=number]{
    width:100%;padding:10px 12px;border:1px solid var(--line);border-radius:7px;font-size:14px;background:#fdfbf7;color:var(--ink);
  }
  input:focus{outline:2px solid #d8c7a1;outline-offset:1px;}
  .design-card{background:#fff;border:1px solid var(--line);border-radius:10px;padding:22px;margin-bottom:18px;position:relative;}
  .design-card h3{margin:0 0 16px;font-size:14px;letter-spacing:.5px;}
  .design-remove{position:absolute;top:18px;right:20px;font-size:12px;color:#9a4130;background:none;border:none;cursor:pointer;text-decoration:underline;}
  .designer-grid{display:grid;grid-template-columns:1fr 1fr;gap:32px;align-items:start;}
  @media (max-width:820px){ .designer-grid{grid-template-columns:1fr;} .grid2{grid-template-columns:1fr;} }
  .field-label{font-size:11px;font-weight:700;letter-spacing:.6px;text-transform:uppercase;color:#8a7f6c;margin-bottom:8px;}
  .chip-choices{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:18px;}
  .chip-choice{border:2px solid var(--line);border-radius:10px;padding:14px;text-align:center;cursor:pointer;background:#fff;}
  .chip-choice.selected{border-color:var(--ink);}
  .chip-swatch{height:70px;border-radius:8px;margin-bottom:10px;display:flex;align-items:center;justify-content:center;font-size:26px;}
  .chip-standard .chip-swatch{background:#e7e2f2;}
  .chip-large .chip-swatch{background:#deede4;}
  .chip-choice .label{font-size:11px;font-weight:700;letter-spacing:.5px;}
  .qty-row{margin-bottom:18px;}
  .qty-row input{width:110px;}
  .dropzone{display:block;border:2px dashed #cbb27e;border-radius:10px;padding:26px;text-align:center;background:#fbf7ee;cursor:pointer;margin-bottom:20px;}
  .dropzone .icon{font-size:26px;}
  .dropzone .cta{color:var(--accent-dark);font-weight:700;}
  .dropzone .hint{font-size:11px;color:#9a8f7a;letter-spacing:.5px;margin-top:6px;text-transform:uppercase;}
  .dropzone.has-file{border-style:solid;}
  .dropzone input[type=file]{display:none;}
  .filename{font-size:12px;color:#5c5344;margin-top:8px;word-break:break-all;}
  .adjust-title{font-size:11px;font-weight:700;letter-spacing:.6px;text-transform:uppercase;color:#8a7f6c;margin:4px 0 12px;}
  .slider-row{display:grid;grid-template-columns:70px 1fr 46px;align-items:center;gap:10px;margin-bottom:10px;font-size:13px;}
  .slider-row input[type=range]{width:100%;}
  .slider-row .val{text-align:right;color:var(--accent-dark);font-weight:600;font-size:13px;}
  .reset-btn{width:100%;padding:9px;border:1px solid var(--line);border-radius:7px;background:#fff;font-size:13px;cursor:pointer;margin-top:4px;}
  .reset-btn:hover{background:#f4efe4;}
  .preview-col{position:sticky;top:20px;}
  .preview-label{font-size:11px;font-weight:700;letter-spacing:.6px;text-transform:uppercase;color:#8a7f6c;margin-bottom:10px;}
  .preview-frame{position:relative;border-radius:14px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,.12);cursor:grab;line-height:0;}
  .preview-frame:active{cursor:grabbing;}
  .preview-frame canvas{width:100%;height:auto;display:block;}
  .chip-guide{position:absolute;border:1.5px dashed rgba(255,255,255,.85);background:rgba(255,255,255,.18);border-radius:4px;pointer-events:none;}
  .preview-caption{text-align:center;font-size:12px;color:#9a8f7a;margin-top:10px;letter-spacing:.3px;}
  .add-design-btn{display:block;width:100%;padding:16px;border:2px dashed #cbb27e;border-radius:10px;background:#fbf7ee;color:var(--accent-dark);font-weight:700;font-size:14px;cursor:pointer;margin-bottom:28px;}
  .add-design-btn:hover{background:#f5edd9;}
  .submit-card{background:#fff;border:1px solid var(--line);border-radius:10px;padding:24px;}
  .submit-desc{font-size:13px;color:#6b6151;margin-bottom:16px;}
  .submit-btn{width:100%;padding:15px;border:none;border-radius:8px;background:var(--ink);color:#fff;font-size:15px;font-weight:700;cursor:pointer;}
  .submit-btn:disabled{opacity:.5;cursor:not-allowed;}
  .submit-btn:not(:disabled):hover{background:#463d33;}
  .validation-msg{font-size:12px;color:var(--danger);margin-top:10px;text-align:center;}
  .footer-meta{display:flex;gap:28px;justify-content:center;margin-top:26px;font-size:12px;color:#8a7f6c;flex-wrap:wrap;}
  .footer-meta b{color:var(--ink);}
  .modal-overlay{position:fixed;inset:0;background:rgba(30,25,18,.55);display:none;align-items:center;justify-content:center;z-index:50;}
  .modal-overlay.show{display:flex;}
  .modal{background:#fff;border-radius:14px;padding:36px;max-width:420px;text-align:center;}
  .modal .emoji{font-size:40px;}
  .modal h2{margin:12px 0 8px;}
  .modal p{font-size:14px;color:#6b6151;line-height:1.5;}
  .modal button{margin-top:18px;padding:11px 26px;border:none;border-radius:8px;background:var(--ink);color:#fff;font-weight:700;cursor:pointer;}
  .bg-swatches{display:flex;gap:8px;margin-bottom:16px;}
  .bg-swatch{width:26px;height:26px;border-radius:6px;border:2px solid var(--line);cursor:pointer;box-shadow:inset 0 0 0 1px rgba(0,0,0,.06);}
  .bg-swatch.selected{border-color:var(--ink);}
</style>
</head>
<body>

<header>
  <div class="brand">
    <div>
      <h1>Dapper Threads</h1>
      <span>Custom Card Skins</span>
    </div>
    <div class="sub">Design Submission</div>
  </div>
  <a class="shop" href="https://www.DapperThreadsUS.com" target="_blank" rel="noopener">Shop at DapperThreadsUS.com &rarr;</a>
</header>

<main>
  <div class="notice">
    🛒 <strong>A completed purchase is required before submitting your design.</strong>
    Please visit <a href="https://www.DapperThreadsUS.com" target="_blank" rel="noopener">DapperThreadsUS.com</a>
    to purchase your custom card skin first, then return here with your order number.
    Submissions without a valid order number will not be processed.
  </div>

  <section class="block">
    <div class="step-head"><div class="step-num">1</div><div class="step-title">Order Information</div></div>
    <div class="card">
      <div class="grid2">
        <div>
          <label class="field">First Name *</label>
          <input type="text" id="firstName" autocomplete="given-name">
        </div>
        <div>
          <label class="field">Last Name *</label>
          <input type="text" id="lastName" autocomplete="family-name">
        </div>
        <div>
          <label class="field">Email Address *</label>
          <input type="email" id="email" autocomplete="email">
        </div>
        <div>
          <label class="field">Order # *</label>
          <input type="text" id="orderNumber">
        </div>
      </div>
    </div>
  </section>

  <section class="block">
    <div class="step-head"><div class="step-num">2</div><div class="step-title">Your Designs</div></div>
    <div class="step-desc">Add one design slot per card skin design. If you're ordering the same design on multiple cards, enter the quantity in that slot. Add as many different designs as your order includes.</div>
    <div id="designsContainer"></div>
    <button type="button" class="add-design-btn" id="addDesignBtn">+ Add Another Design</button>
  </section>

  <section class="block">
    <div class="step-head"><div class="step-num">3</div><div class="step-title">Submit Your Order</div></div>
    <div class="submit-card">
      <div class="submit-desc">When you're happy with all your previews, click below to submit. Each design will download to your device and we'll receive your order details. Your order will ship within 10 business days.</div>
      <button type="button" class="submit-btn" id="submitBtn">&#10003; Submit My Order</button>
      <div class="validation-msg" id="validationMsg"></div>
    </div>
  </section>

  <div class="footer-meta">
    <div>Bleed <b>1mm</b></div>
    <div>Output <b>300dpi PNG</b></div>
    <div>Card <b>85.6&times;53.98mm</b></div>
  </div>
</main>

<div class="modal-overlay" id="successModal">
  <div class="modal">
    <div class="emoji">🎉</div>
    <h2>Order Submitted!</h2>
    <p>Your designs have been submitted! Print-ready PDFs with cut lines have been emailed to us and copies have downloaded to your device. We'll be in touch if we have any questions.</p>
    <p>Your order will ship within 10 business days.</p>
    <button type="button" id="modalDoneBtn">Done</button>
  </div>
</div>

<!--
  Static hidden form so Netlify's build-time HTML parser registers this form.
  Field names must exactly match what the real submission FormData uses below.
-->
<form name="card-skin-order" data-netlify="true" netlify-honeypot="bot-field" hidden>
  <input type="text" name="first-name">
  <input type="text" name="last-name">
  <input type="email" name="email">
  <input type="text" name="order-number">
  <input type="text" name="designs-summary">
  <input type="file" name="design-file-1">
  <input type="file" name="design-file-2">
  <input type="file" name="design-file-3">
  <input type="file" name="design-file-4">
  <input type="file" name="design-file-5">
  <input type="file" name="design-file-6">
  <input type="file" name="design-file-7">
  <input type="file" name="design-file-8">
  <input type="file" name="design-file-9">
  <input type="file" name="design-file-10">
  <input type="text" name="overflow-notice">
  <input name="bot-field">
</form>

<script>
(function(){
  "use strict";

  // ── Card geometry (mm) — must match dapper-threads-api/app.py exactly ────
  const CARD_W = 85.6, CARD_H = 53.98, CORNER = 3.18;
  const BLEED = 1.0, CHIP_BLEED = 1.0;
  const PAGE_W = CARD_W + BLEED*2;   // 87.6
  const PAGE_H = CARD_H + BLEED*2;   // 55.98
  const DPI = 300;
  const PXW = Math.round(PAGE_W / 25.4 * DPI);  // 1035
  const PXH = Math.round(PAGE_H / 25.4 * DPI);  // 661
  const MM_TO_PX = PXW / PAGE_W;

  const CHIPS = {
    standard: { x: 8.38,  y: 17.98,  w: 13.02, h: 10.04, r: 1.5 },
    large:    { x: 7.865, y: 16.325, w: 14.79, h: 13.67, r: 1.5 },
  };

  const RENDER_API = "https://dapper-threads-api.onrender.com/generate-pdf";
  const MAX_DESIGNS = 10;
  const BG_COLORS = ["#000000", "#ffffff", "#4a4a4a"];

  let designs = [];   // { id, chipType, quantity, file, imgEl, scale, moveX, moveY, rotate, bgColor }
  let nextId = 1;

  function roundRectPath(ctx, x, y, w, h, r){
    ctx.beginPath();
    ctx.moveTo(x+r, y);
    ctx.arcTo(x+w, y,   x+w, y+h, r);
    ctx.arcTo(x+w, y+h, x,   y+h, r);
    ctx.arcTo(x,   y+h, x,   y,   r);
    ctx.arcTo(x,   y,   x+w, y,   r);
    ctx.closePath();
  }

  // ── THE FIX ───────────────────────────────────────────────────────────────
  // Previous (broken) implementation computed a "cover fit" source crop once,
  // then scaled the *already-cropped* rectangle up/down. Reducing scale below
  // 100% just shrank that same crop on screen — it never revealed the parts
  // of the original photo that the crop excluded, and it left the untouched
  // canvas area fully transparent, which later collapsed to solid black once
  // the PDF pipeline flattened the PNG to RGB.
  //
  // Fixed approach: always draw the FULL source image (never pre-cropped).
  // "Scale" now zooms the whole image in/out around the card's center, and a
  // clip path constrains what's visible to the card+bleed shape. An opaque
  // background is always painted first, so any area the image doesn't reach
  // renders as an intentional, visible color — never a silent transparent
  // gap that turns black downstream.
  function drawDesign(canvas, design){
    const ctx = canvas.getContext('2d');
    ctx.save();
    ctx.clearRect(0, 0, PXW, PXH);

    // 1. Always-opaque background fill first.
    ctx.fillStyle = design.bgColor || '#000000';
    ctx.fillRect(0, 0, PXW, PXH);

    // 2. Clip to the card+bleed rounded-rect silhouette.
    roundRectPath(ctx, 0, 0, PXW, PXH, (CORNER + BLEED) * MM_TO_PX);
    ctx.clip();

    if (design.imgEl){
      const iw = design.imgEl.naturalWidth, ih = design.imgEl.naturalHeight;
      if (iw && ih){
        const imageAspect = iw / ih, canvasAspect = PXW / PXH;
        let baseW, baseH;
        if (imageAspect > canvasAspect){ baseH = PXH; baseW = PXH * imageAspect; }
        else                           { baseW = PXW; baseH = PXW / imageAspect; }

        const drawW = baseW * design.scale;
        const drawH = baseH * design.scale;
        const cx = PXW / 2 + design.moveX * MM_TO_PX;
        const cy = PXH / 2 + design.moveY * MM_TO_PX;

        ctx.translate(cx, cy);
        ctx.rotate(design.rotate * Math.PI / 180);
        ctx.drawImage(design.imgEl, -drawW / 2, -drawH / 2, drawW, drawH);
      }
    }
    ctx.restore();
  }

  function redraw(design){
    if (!design.canvasEl) return;
    drawDesign(design.canvasEl, design);
  }

  // ── UI construction ───────────────────────────────────────────────────────
  function chipSwatchEmoji(type){ return type === 'large' ? '💳' : '🔲'; }

  function createDesignCard(design){
    const el = document.createElement('div');
    el.className = 'design-card';
    el.dataset.id = design.id;
    el.innerHTML = `
      <h3>Design ${design.indexLabel}</h3>
      <button type="button" class="design-remove" data-action="remove">Remove this design</button>
      <div class="designer-grid">
        <div>
          <div class="field-label">Chip Size</div>
          <div class="chip-choices">
            <div class="chip-choice chip-standard selected" data-chip="standard">
              <div class="chip-swatch">🔲</div>
              <div class="label">STANDARD CHIP</div>
            </div>
            <div class="chip-choice chip-large" data-chip="large">
              <div class="chip-swatch">💳</div>
              <div class="label">LARGE CHIP</div>
            </div>
          </div>

          <div class="qty-row">
            <label class="field-label">Quantity</label>
            <input type="number" min="1" step="1" value="1" class="qtyInput">
          </div>

          <label class="dropzone" data-action="dropzone">
            <div class="icon">🖼️</div>
            <div><span class="cta">Click to upload</span> or drag image here</div>
            <div class="hint">JPG &middot; PNG &middot; WEBP &middot; up to 25MB</div>
            <div class="filename"></div>
            <input type="file" accept="image/jpeg,image/png,image/webp" class="fileInput">
          </label>

          <div class="field-label">Card Background</div>
          <div class="bg-swatches">
            ${BG_COLORS.map((c,i)=>`<div class="bg-swatch${i===0?' selected':''}" style="background:${c}" data-bg="${c}"></div>`).join('')}
          </div>

          <div class="adjust-title">Adjust Position</div>
          <div class="slider-row">
            <span>Scale</span>
            <input type="range" class="scaleSlider" min="20" max="300" value="100">
            <span class="val scaleVal">100%</span>
          </div>
          <div class="slider-row">
            <span>Move X</span>
            <input type="range" class="moveXSlider" min="-40" max="40" value="0">
            <span class="val moveXVal">0</span>
          </div>
          <div class="slider-row">
            <span>Move Y</span>
            <input type="range" class="moveYSlider" min="-40" max="40" value="0">
            <span class="val moveYVal">0</span>
          </div>
          <div class="slider-row">
            <span>Rotate</span>
            <input type="range" class="rotateSlider" min="-180" max="180" value="0">
            <span class="val rotateVal">0&deg;</span>
          </div>
          <button type="button" class="reset-btn" data-action="reset">Reset position</button>
        </div>

        <div class="preview-col">
          <div class="preview-label">Live Preview</div>
          <div class="preview-frame">
            <canvas width="${PXW}" height="${PXH}"></canvas>
            <div class="chip-guide"></div>
          </div>
          <div class="preview-caption">Drag on card to reposition</div>
        </div>
      </div>
    `;
    return el;
  }

  function positionChipGuide(el, design){
    const guide = el.querySelector('.chip-guide');
    const chip = CHIPS[design.chipType];
    const pctX = (BLEED + chip.x) / PAGE_W * 100;
    const pctY = (BLEED + chip.y) / PAGE_H * 100;
    const pctW = chip.w / PAGE_W * 100;
    const pctH = chip.h / PAGE_H * 100;
    guide.style.left = pctX + '%';
    guide.style.top = pctY + '%';
    guide.style.width = pctW + '%';
    guide.style.height = pctH + '%';
  }

  function summaryLine(d, idx){
    const label = d.chipType === 'large' ? 'Large Chip' : 'Standard Chip';
    return `Design ${idx+1}: ${label}, Qty ${d.quantity}`;
  }

  function updateIndexLabels(){
    designs.forEach((d, i) => {
      d.indexLabel = i + 1;
      const h3 = d.el.querySelector('h3');
      if (h3) h3.textContent = `Design ${d.indexLabel}`;
      const removeBtn = d.el.querySelector('[data-action="remove"]');
      if (removeBtn) removeBtn.style.display = designs.length > 1 ? '' : 'none';
    });
  }

  function addDesign(){
    if (designs.length >= MAX_DESIGNS) return;
    const design = {
      id: nextId++, indexLabel: designs.length + 1,
      chipType: 'standard', quantity: 1, file: null, imgEl: null,
      scale: 1, moveX: 0, moveY: 0, rotate: 0, bgColor: BG_COLORS[0],
    };
    const el = createDesignCard(design);
    design.el = el;
    design.canvasEl = el.querySelector('canvas');
    document.getElementById('designsContainer').appendChild(el);
    wireDesignCard(design);
    positionChipGuide(el, design);
    redraw(design);
    designs.push(design);
    updateIndexLabels();
    updateAddButtonState();
  }

  function removeDesign(design){
    design.el.remove();
    designs = designs.filter(d => d.id !== design.id);
    updateIndexLabels();
    updateAddButtonState();
  }

  function updateAddButtonState(){
    document.getElementById('addDesignBtn').style.display =
      designs.length >= MAX_DESIGNS ? 'none' : '';
  }

  function loadFile(design, file){
    design.file = file;
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = function(){
      design.imgEl = img;
      design.el.querySelector('.dropzone').classList.add('has-file');
      design.el.querySelector('.filename').textContent = file.name;
      redraw(design);
    };
    img.src = url;
  }

  function wireDesignCard(design){
    const el = design.el;

    el.querySelectorAll('.chip-choice').forEach(choice => {
      choice.addEventListener('click', () => {
        el.querySelectorAll('.chip-choice').forEach(c => c.classList.remove('selected'));
        choice.classList.add('selected');
        design.chipType = choice.dataset.chip;
        positionChipGuide(el, design);
      });
    });

    el.querySelectorAll('.bg-swatch').forEach(sw => {
      sw.addEventListener('click', () => {
        el.querySelectorAll('.bg-swatch').forEach(s => s.classList.remove('selected'));
        sw.classList.add('selected');
        design.bgColor = sw.dataset.bg;
        redraw(design);
      });
    });

    el.querySelector('.qtyInput').addEventListener('input', e => {
      design.quantity = Math.max(1, parseInt(e.target.value, 10) || 1);
    });

    const fileInput = el.querySelector('.fileInput');
    const dropzone = el.querySelector('[data-action="dropzone"]');
    fileInput.addEventListener('change', e => {
      if (e.target.files && e.target.files[0]) loadFile(design, e.target.files[0]);
    });
    dropzone.addEventListener('dragover', e => e.preventDefault());
    dropzone.addEventListener('drop', e => {
      e.preventDefault();
      if (e.dataTransfer.files && e.dataTransfer.files[0]) loadFile(design, e.dataTransfer.files[0]);
    });

    function bindSlider(cls, key, valEl, fmt){
      const input = el.querySelector(cls);
      input.addEventListener('input', () => {
        design[key] = parseFloat(input.value);
        el.querySelector(valEl).textContent = fmt(design[key]);
        redraw(design);
      });
    }
    // Scale slider stores whole percent (20-300); convert to a multiplier on read.
    el.querySelector('.scaleSlider').addEventListener('input', function(){
      design.scale = parseFloat(this.value) / 100;
      el.querySelector('.scaleVal').textContent = this.value + '%';
      redraw(design);
    });
    bindSlider('.moveXSlider', 'moveX', '.moveXVal', v => Math.round(v));
    bindSlider('.moveYSlider', 'moveY', '.moveYVal', v => Math.round(v));
    bindSlider('.rotateSlider', 'rotate', '.rotateVal', v => Math.round(v) + '°');

    el.querySelector('[data-action="reset"]').addEventListener('click', () => {
      design.scale = 1; design.moveX = 0; design.moveY = 0; design.rotate = 0;
      el.querySelector('.scaleSlider').value = 100;
      el.querySelector('.moveXSlider').value = 0;
      el.querySelector('.moveYSlider').value = 0;
      el.querySelector('.rotateSlider').value = 0;
      el.querySelector('.scaleVal').textContent = '100%';
      el.querySelector('.moveXVal').textContent = '0';
      el.querySelector('.moveYVal').textContent = '0';
      el.querySelector('.rotateVal').textContent = '0°';
      redraw(design);
    });

    el.querySelector('[data-action="remove"]').addEventListener('click', () => removeDesign(design));

    // Drag-to-reposition directly on the preview.
    const frame = el.querySelector('.preview-frame');
    let dragging = false, lastX = 0, lastY = 0;
    frame.addEventListener('mousedown', e => {
      dragging = true; lastX = e.clientX; lastY = e.clientY;
    });
    window.addEventListener('mousemove', e => {
      if (!dragging) return;
      const rect = frame.getBoundingClientRect();
      const mmPerPxOnScreen = PAGE_W / rect.width;
      design.moveX += (e.clientX - lastX) * mmPerPxOnScreen;
      design.moveY += (e.clientY - lastY) * mmPerPxOnScreen;
      design.moveX = Math.max(-40, Math.min(40, design.moveX));
      design.moveY = Math.max(-40, Math.min(40, design.moveY));
      lastX = e.clientX; lastY = e.clientY;
      el.querySelector('.moveXSlider').value = design.moveX;
      el.querySelector('.moveYSlider').value = design.moveY;
      el.querySelector('.moveXVal').textContent = Math.round(design.moveX);
      el.querySelector('.moveYVal').textContent = Math.round(design.moveY);
      redraw(design);
    });
    window.addEventListener('mouseup', () => { dragging = false; });
  }

  document.getElementById('addDesignBtn').addEventListener('click', addDesign);

  // ── Submission ─────────────────────────────────────────────────────────────
  function validate(){
    const first = document.getElementById('firstName').value.trim();
    const last = document.getElementById('lastName').value.trim();
    const email = document.getElementById('email').value.trim();
    const orderNumber = document.getElementById('orderNumber').value.trim();
    if (!first || !last || !email || !orderNumber){
      return 'Please fill in your order details and upload at least one design.';
    }
    if (designs.length === 0 || !designs.some(d => d.file)){
      return 'Please fill in your order details and upload at least one design.';
    }
    for (const d of designs){
      if (!d.file) return `Design ${d.indexLabel} is missing an uploaded image.`;
    }
    return null;
  }

  function canvasToBlob(canvas){
    return new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
  }

  async function handleSubmit(){
    const msgEl = document.getElementById('validationMsg');
    const err = validate();
    if (err){ msgEl.textContent = err; return; }
    msgEl.textContent = '';

    const submitBtn = document.getElementById('submitBtn');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Submitting…';

    const first = document.getElementById('firstName').value.trim();
    const last = document.getElementById('lastName').value.trim();
    const email = document.getElementById('email').value.trim();
    const orderNumber = document.getElementById('orderNumber').value.trim();

    try {
      // Render each design's canvas to a final PNG blob (freshest draw first).
      const blobs = [];
      for (const d of designs){
        redraw(d);
        const blob = await canvasToBlob(d.canvasEl);
        const fname = `DapperThreads_${first}${last}_Order${orderNumber}_Design${d.indexLabel}_${d.chipType}chip_qty${d.quantity}_300dpi.png`;
        blobs.push({ design: d, blob, fname });
      }

      // Trigger local downloads.
      blobs.forEach(({ blob, fname }) => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = fname;
        document.body.appendChild(a);
        a.click();
        a.remove();
      });

      // 1) Netlify Forms submission (record-keeping).
      const netlifyForm = new FormData();
      netlifyForm.append('form-name', 'card-skin-order');
      netlifyForm.append('first-name', first);
      netlifyForm.append('last-name', last);
      netlifyForm.append('email', email);
      netlifyForm.append('order-number', orderNumber);
      netlifyForm.append('designs-summary', designs.map((d,i) => summaryLine(d,i)).join(' | '));
      let overflow = '';
      blobs.slice(0, 10).forEach(({ blob, fname }, i) => {
        netlifyForm.append(`design-file-${i+1}`, blob, fname);
      });
      if (blobs.length > 10){
        overflow = `${blobs.length - 10} additional design(s) not attached — see Render API submission.`;
      }
      netlifyForm.append('overflow-notice', overflow);
      netlifyForm.append('bot-field', '');
      await fetch('/', { method: 'POST', body: netlifyForm }).catch(() => {});

      // 2) Render API submission (this is what actually generates print PDFs & emails).
      const apiForm = new FormData();
      apiForm.append('first_name', first);
      apiForm.append('last_name', last);
      apiForm.append('email', email);
      apiForm.append('order_number', orderNumber);
      apiForm.append('designs', JSON.stringify(designs.map((d,i) => ({
        design_index: d.indexLabel, chip_type: d.chipType, quantity: d.quantity,
      }))));
      blobs.forEach(({ blob, fname }, i) => {
        apiForm.append(`image_${i+1}`, blob, fname);
      });
      await fetch(RENDER_API, { method: 'POST', body: apiForm }).catch(() => {});

      document.getElementById('successModal').classList.add('show');
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = '✓ Submit My Order';
    }
  }

  document.getElementById('submitBtn').addEventListener('click', handleSubmit);
  document.getElementById('modalDoneBtn').addEventListener('click', () => {
    document.getElementById('successModal').classList.remove('show');
  });

  // Start with one design slot.
  addDesign();
})();
</script>
</body>
</html>
