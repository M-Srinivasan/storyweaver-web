/**
 * StoryWeaver — script.js
 * Vanilla JS only. No dependencies.
 *
 * Backend integration points are clearly marked with:
 *   // ── BACKEND ──
 * Replace the placeholder fetch calls with real endpoints.
 *
 * The app uses SSE (Server-Sent Events) via EventSource
 * to receive real-time progress from the Python backend.
 *
 * Expected SSE event types (ev.type):
 *   'stage'   → { data: "Stage description string" }
 *   'log'     → { data: "Log line string" }
 *   'outline' → { data: { title, chapters: [{number, title, synopsis}] } }
 *   'chapter' → { data: { number, title, text } }
 *   'done'    → { data: { total_chapters } }
 *   'error'   → { data: "Error message string" }
 */

'use strict';

/* ═══════════════════════════════════════════════════════
   STATE
═══════════════════════════════════════════════════════ */
const state = {
  isGenerating: false,
  totalChapters: 0,
  completedChapters: 0,
  chapters: [],        // { number, title, text }[]
  pov: 'first_person',
  tense: 'past',
  storyEventSource: null,
  pipelineSteps: [],   // step objects for the pipeline UI
};

/* ═══════════════════════════════════════════════════════
   DOM REFS
═══════════════════════════════════════════════════════ */
const $ = id => document.getElementById(id);

const DOM = {
  form:              $('story-form'),
  formSection:       $('form-section'),
  generateBtn:       $('generate_button'),
  progressSection:   $('progress-section'),
  progressSubtitle:  $('progress-subtitle'),
  progressBarFill:   $('progress-bar-fill'),
  progressBarLabel:  $('progress-bar-label'),
  progressBarTrack:  $('progress-bar-track'),
  pipelineList:      $('pipeline-list'),
  logBody:           $('log-body'),
  logToggle:         $('log-toggle'),
  chaptersSection:   $('chapters-section'),
  chaptersSubtitle:  $('chapters-subtitle'),
  chapterCards:      $('chapter-cards'),
  outlinePanel:      $('outline-panel'),
  outlineToggle:     $('outline-toggle'),
  outlineBody:       $('outline-body'),
  doneBanner:        $('done-banner'),
  doneSub:           $('done-sub'),
  chapterModal:      $('chapter-modal'),
  modalContent:      $('modal-content'),
  modalClose:        $('modal-close'),
  heroCta:           $('hero-cta'),
};

/* ═══════════════════════════════════════════════════════
   THEME TOGGLE
═══════════════════════════════════════════════════════ */
function initTheme() {
  const toggleBtn = $('theme-toggle');
  const iconSun = $('theme-icon-sun');
  const iconMoon = $('theme-icon-moon');
  if (!toggleBtn) return;

  // Check saved theme or system preference
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme === 'light') {
    document.documentElement.setAttribute('data-theme', 'light');
    iconSun.classList.add('hidden');
    iconMoon.classList.remove('hidden');
  }

  toggleBtn.addEventListener('click', () => {
    const isLight = document.documentElement.getAttribute('data-theme') === 'light';
    if (isLight) {
      document.documentElement.removeAttribute('data-theme');
      localStorage.setItem('theme', 'dark');
      iconSun.classList.remove('hidden');
      iconMoon.classList.add('hidden');
    } else {
      document.documentElement.setAttribute('data-theme', 'light');
      localStorage.setItem('theme', 'light');
      iconSun.classList.add('hidden');
      iconMoon.classList.remove('hidden');
    }
  });
}

/* ═══════════════════════════════════════════════════════
   SLIDER INITIALIZATION
═══════════════════════════════════════════════════════ */
function initSliders() {
  const sliders = document.querySelectorAll('.range-slider');

  sliders.forEach(slider => {
    const valEl = $(`${slider.id}_val`);
    if (!valEl) return;

    const updateSlider = () => {
      const min = parseFloat(slider.min);
      const max = parseFloat(slider.max);
      const val = parseFloat(slider.value);
      const pct = ((val - min) / (max - min)) * 100;

      // Update CSS custom property for the track fill gradient
      slider.style.setProperty('--fill-pct', `${pct}%`);

      // Update displayed value
      valEl.textContent = val;

      // Update aria
      slider.setAttribute('aria-valuenow', val);
    };

    slider.addEventListener('input', updateSlider);
    // Initialize on load
    updateSlider();
  });
}

/* ═══════════════════════════════════════════════════════
   TOGGLE PILLS (POV / TENSE)
═══════════════════════════════════════════════════════ */
function initTogglePills() {
  document.querySelectorAll('.toggle-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      const group = pill.dataset.group;
      const value = pill.dataset.value;

      // Deactivate all in this group
      document.querySelectorAll(`.toggle-pill[data-group="${group}"]`).forEach(p => {
        p.classList.remove('active');
        p.setAttribute('aria-checked', 'false');
      });

      // Activate clicked
      pill.classList.add('active');
      pill.setAttribute('aria-checked', 'true');

      // Store in state
      state[group] = value;
    });

    // Keyboard: Space/Enter to select
    pill.addEventListener('keydown', e => {
      if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        pill.click();
      }
    });
  });
}

/* ═══════════════════════════════════════════════════════
   SCROLL REVEAL (IntersectionObserver)
═══════════════════════════════════════════════════════ */
function initScrollReveal() {
  const observer = new IntersectionObserver(
    entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
  );

  document.querySelectorAll('[data-reveal]').forEach(el => observer.observe(el));
}

/* ═══════════════════════════════════════════════════════
   HERO CTA SMOOTH SCROLL
═══════════════════════════════════════════════════════ */
function initHeroCta() {
  if (!DOM.heroCta) return;
  DOM.heroCta.addEventListener('click', e => {
    e.preventDefault();
    DOM.formSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
}

/* ═══════════════════════════════════════════════════════
   LOG CONSOLE TOGGLE
═══════════════════════════════════════════════════════ */
function initLogToggle() {
  if (!DOM.logToggle) return;
  DOM.logToggle.addEventListener('click', () => {
    const logBody = $('log-body');
    const isExpanded = DOM.logToggle.getAttribute('aria-expanded') === 'true';
    if (isExpanded) {
      logBody.classList.add('hidden');
      DOM.logToggle.textContent = 'Show';
      DOM.logToggle.setAttribute('aria-expanded', 'false');
    } else {
      logBody.classList.remove('hidden');
      DOM.logToggle.textContent = 'Hide';
      DOM.logToggle.setAttribute('aria-expanded', 'true');
    }
  });
}

/* ═══════════════════════════════════════════════════════
   OUTLINE TOGGLE
═══════════════════════════════════════════════════════ */
function initOutlineToggle() {
  if (!DOM.outlineToggle) return;
  DOM.outlineToggle.addEventListener('click', () => {
    const isExpanded = DOM.outlineToggle.getAttribute('aria-expanded') === 'true';
    DOM.outlineToggle.setAttribute('aria-expanded', String(!isExpanded));
    DOM.outlineBody.classList.toggle('hidden', isExpanded);
  });
}

/* ═══════════════════════════════════════════════════════
   MODAL
═══════════════════════════════════════════════════════ */
function openChapterModal(chapter) {
  const firstSentence = chapter.text.split(/[.!?]/)[0] + '.';
  const wordCount = chapter.text.split(/\s+/).length;

  DOM.modalContent.innerHTML = `
    <p class="modal-eyebrow">Chapter ${chapter.number}</p>
    <h2 class="modal-title" id="modal-title">${escHtml(chapter.title)}</h2>
    <div class="modal-divider"></div>
    <div class="modal-body">${escHtml(chapter.text)}</div>
    <p style="margin-top:32px;font-size:12px;color:var(--text-dim);text-align:right;letter-spacing:.06em">
      ~${wordCount.toLocaleString()} words
    </p>
  `;

  DOM.chapterModal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';

  // Focus trap: move focus to close btn
  requestAnimationFrame(() => DOM.modalClose.focus());
}

function closeModal() {
  DOM.chapterModal.classList.add('hidden');
  document.body.style.overflow = '';
}

function initModal() {
  DOM.modalClose.addEventListener('click', closeModal);

  // Close on overlay click
  DOM.chapterModal.addEventListener('click', e => {
    if (e.target === DOM.chapterModal) closeModal();
  });

  // Close on Escape
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !DOM.chapterModal.classList.contains('hidden')) {
      closeModal();
    }
  });
}

/* ═══════════════════════════════════════════════════════
   PIPELINE BUILDER
   Builds the step list based on the outline data
═══════════════════════════════════════════════════════ */
function buildPipelineSteps(numChapters) {
  state.pipelineSteps = [];

  // Fixed pre-chapter steps
  const fixedSteps = [
    { id: 'story_planner',    label: 'Story Planner' },
    { id: 'world_builder',    label: 'World Builder' },
    { id: 'character_builder', label: 'Character Builder' },
  ];
  fixedSteps.forEach(s => state.pipelineSteps.push({ ...s, status: 'pending' }));

  // Chapter steps
  for (let i = 1; i <= numChapters; i++) {
    state.pipelineSteps.push({ id: `ch${i}_scene`,  label: `Chapter ${i} — Scene Planning`,    status: 'pending' });
    state.pipelineSteps.push({ id: `ch${i}_write`,  label: `Chapter ${i} — Writing`,           status: 'pending' });
    state.pipelineSteps.push({ id: `ch${i}_valid`,  label: `Chapter ${i} — Validating`,        status: 'pending' });
    state.pipelineSteps.push({ id: `ch${i}_bible`,  label: `Chapter ${i} — Updating Story Bible`, status: 'pending' });
  }

  renderPipeline();
}

function renderPipeline() {
  DOM.pipelineList.innerHTML = '';
  state.pipelineSteps.forEach((step, idx) => {
    const li = document.createElement('li');
    li.className = `pipeline-step ${step.status === 'active' ? 'is-active' : ''} ${step.status === 'done' ? 'is-done' : ''}`;
    li.id = `step-${step.id}`;

    const statusText = step.status === 'pending' ? 'Pending'
                     : step.status === 'active'  ? 'In progress'
                     : 'Complete';

    li.innerHTML = `
      <div class="step-indicator" aria-hidden="true"></div>
      <span class="step-name">${escHtml(step.label)}</span>
      <span class="step-status-text">${statusText}</span>
    `;
    DOM.pipelineList.appendChild(li);
  });
}

function setStepStatus(stepId, status) {
  const step = state.pipelineSteps.find(s => s.id === stepId);
  if (step) {
    step.status = status;
    const li = $(`step-${stepId}`);
    if (li) {
      li.className = `pipeline-step ${status === 'active' ? 'is-active' : ''} ${status === 'done' ? 'is-done' : ''}`;
      const statusText = status === 'pending' ? 'Pending' : status === 'active' ? 'In progress' : 'Complete';
      li.querySelector('.step-status-text').textContent = statusText;
    }
  }
}

/* Advance pipeline based on SSE stage messages */
let currentChapterStep = 0;

function advancePipelineFromStage(stageText) {
  const t = stageText.toLowerCase();

  if (t.includes('story plan') || t.includes('planning story')) {
    setStepStatus('story_planner', 'active');
  } else if (t.includes('world') || t.includes('world build')) {
    setStepStatus('story_planner', 'done');
    setStepStatus('world_builder', 'active');
  } else if (t.includes('character')) {
    setStepStatus('world_builder', 'done');
    setStepStatus('character_builder', 'active');
  } else if (t.includes('chapter')) {
    setStepStatus('character_builder', 'done');
    // Extract chapter number if present
    const match = stageText.match(/chapter\s*(\d+)/i);
    const chNum = match ? parseInt(match[1]) : currentChapterStep + 1;
    currentChapterStep = chNum;

    if (t.includes('scene') || t.includes('plan')) {
      setStepStatus(`ch${chNum}_scene`, 'active');
    } else if (t.includes('writ') || t.includes('draft')) {
      setStepStatus(`ch${chNum}_scene`, 'done');
      setStepStatus(`ch${chNum}_write`, 'active');
    } else if (t.includes('valid')) {
      setStepStatus(`ch${chNum}_write`, 'done');
      setStepStatus(`ch${chNum}_valid`, 'active');
    } else if (t.includes('bible') || t.includes('updat')) {
      setStepStatus(`ch${chNum}_valid`, 'done');
      setStepStatus(`ch${chNum}_bible`, 'active');
    }
  }
}

function completeChapterSteps(chNum) {
  setStepStatus(`ch${chNum}_scene`, 'done');
  setStepStatus(`ch${chNum}_write`, 'done');
  setStepStatus(`ch${chNum}_valid`, 'done');
  setStepStatus(`ch${chNum}_bible`, 'done');
}

function completeAllSteps() {
  state.pipelineSteps.forEach(s => s.status = 'done');
  renderPipeline();
}

/* ═══════════════════════════════════════════════════════
   LOG HELPERS
═══════════════════════════════════════════════════════ */
function appendLog(msg, cls = '') {
  const line = document.createElement('div');
  line.className = `log-line ${cls}`;

  // Auto-classify by emoji prefix
  if (!cls) {
    if (msg.includes('✅') || msg.includes('✓')) line.className += ' log-green';
    else if (msg.includes('❌') || msg.includes('⚠️') || msg.includes('Error')) line.className += ' log-red';
    else if (msg.includes('📖') || msg.includes('🎉') || msg.includes('✦')) line.className += ' log-gold';
    else line.className += ' log-dim';
  }

  line.textContent = msg;
  DOM.logBody.appendChild(line);

  // Auto-scroll
  DOM.logBody.scrollTop = DOM.logBody.scrollHeight;
}

/* ═══════════════════════════════════════════════════════
   PROGRESS BAR
═══════════════════════════════════════════════════════ */
function updateProgress(done, total) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  DOM.progressBarFill.style.width = `${pct}%`;
  DOM.progressBarLabel.textContent = `${pct}%`;
  DOM.progressBarTrack.setAttribute('aria-valuenow', pct);
}

/* ═══════════════════════════════════════════════════════
   OUTLINE RENDERER
═══════════════════════════════════════════════════════ */
function renderOutline(data) {
  DOM.outlineBody.innerHTML = '';

  data.chapters.forEach(ch => {
    const item = document.createElement('div');
    item.className = 'outline-item';
    item.innerHTML = `
      <div class="outline-num">Ch ${ch.number}</div>
      <div class="outline-text">
        <strong>${escHtml(ch.title)}</strong>
        <p>${escHtml(ch.synopsis || '')}</p>
      </div>
    `;
    DOM.outlineBody.appendChild(item);
  });

  DOM.outlinePanel.classList.remove('hidden');
}

/* ═══════════════════════════════════════════════════════
   CHAPTER CARD RENDERER
═══════════════════════════════════════════════════════ */
function renderChapterCard(chapter) {
  state.chapters.push(chapter);

  // Reveal chapters section
  DOM.chaptersSection.classList.remove('hidden');

  // Build preview text (first ~30 words)
  const words = chapter.text.split(/\s+/);
  const preview = words.slice(0, 30).join(' ') + (words.length > 30 ? '…' : '');

  // First sentence as teaser
  const sentences = chapter.text.split(/(?<=[.!?])\s+/);
  const teaser = sentences[0] ? sentences[0].slice(0, 120) + (sentences[0].length > 120 ? '…' : '') : '';

  const card = document.createElement('article');
  card.className = 'chapter-card';
  card.setAttribute('aria-label', `Chapter ${chapter.number}: ${chapter.title}`);
  // stagger animation delay
  card.style.animationDelay = `${(state.chapters.length - 1) * 0.08}s`;

  card.innerHTML = `
    <span class="chapter-card-badge">Chapter ${chapter.number}</span>
    <h3 class="chapter-card-title">${escHtml(chapter.title)}</h3>
    <p class="chapter-card-teaser">${escHtml(teaser)}</p>
    <p class="chapter-card-preview">${escHtml(preview)}</p>
    <div class="chapter-card-footer">
      <button class="btn btn-outline btn-read" data-chapter-idx="${state.chapters.length - 1}" aria-label="Read full chapter ${chapter.number}: ${escHtml(chapter.title)}">
        Read Chapter
        <svg viewBox="0 0 16 16" fill="none" class="btn-arrow" aria-hidden="true" style="width:14px;height:14px">
          <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </div>
  `;

  // Wire up read button
  card.querySelector('.btn-read').addEventListener('click', e => {
    const idx = parseInt(e.currentTarget.dataset.chapterIdx);
    openChapterModal(state.chapters[idx]);
  });

  DOM.chapterCards.appendChild(card);

  // Smooth scroll to the new card
  setTimeout(() => card.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 100);
}

/* ═══════════════════════════════════════════════════════
   FINISH UI
═══════════════════════════════════════════════════════ */
function finishUI(totalChapters) {
  completeAllSteps();
  updateProgress(totalChapters, totalChapters);

  DOM.progressSubtitle.textContent = `All ${totalChapters} chapters complete.`;

  // Spin down the generate button
  DOM.generateBtn.classList.remove('loading');
  DOM.generateBtn.disabled = false;
  DOM.generateBtn.querySelector('.btn-submit-text').textContent = 'Weave Another Story';

  // Show done banner
  DOM.doneSub.textContent = `${totalChapters} chapters woven. Your novel is ready to read.`;
  DOM.doneBanner.classList.remove('hidden');
  DOM.doneBanner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  appendLog('✦ Story generation complete.', 'log-gold');

  // Reset state
  state.isGenerating = false;
  if (state.storyEventSource) {
    state.storyEventSource.close();
    state.storyEventSource = null;
  }
}

/* ═══════════════════════════════════════════════════════
   SSE EVENT HANDLER
═══════════════════════════════════════════════════════ */
function handleSSEEvent(ev) {
  switch (ev.type) {

    case 'log':
      // ── BACKEND ──
      // ev.data is a plain string log message from the backend agents
      appendLog(ev.data);
      break;

    case 'stage':
      // ── BACKEND ──
      // ev.data is a string describing the current pipeline stage
      DOM.progressSubtitle.textContent = ev.data;
      appendLog(`[stage] ${ev.data}`, 'log-gold');
      advancePipelineFromStage(ev.data);
      break;

    case 'outline':
      // ── BACKEND ──
      // ev.data: { title?: string, chapters: [{number, title, synopsis}] }
      state.totalChapters = ev.data.chapters.length;
      buildPipelineSteps(state.totalChapters);
      renderOutline(ev.data);
      appendLog(`✦ Outline generated — ${state.totalChapters} chapters planned.`, 'log-gold');
      break;

    case 'chapter':
      // ── BACKEND ──
      // ev.data: { number, title, text }
      state.completedChapters++;
      completeChapterSteps(ev.data.number);
      renderChapterCard(ev.data);
      updateProgress(state.completedChapters, state.totalChapters);
      appendLog(`✅ Chapter ${ev.data.number} — "${ev.data.title}" complete.`, 'log-green');
      break;

    case 'done':
      // ── BACKEND ──
      // ev.data: { total_chapters }
      finishUI(ev.data.total_chapters || state.completedChapters);
      break;

    case 'error':
      // ── BACKEND ──
      // ev.data: error message string
      appendLog(`❌ Error: ${ev.data}`, 'log-red');
      DOM.progressSubtitle.textContent = 'An error occurred — see log below.';
      DOM.generateBtn.classList.remove('loading');
      DOM.generateBtn.disabled = false;
      state.isGenerating = false;
      if (state.storyEventSource) {
        state.storyEventSource.close();
        state.storyEventSource = null;
      }
      break;

    default:
      appendLog(`[event:${ev.type}] ${JSON.stringify(ev.data)}`, 'log-dim');
  }
}

/* ═══════════════════════════════════════════════════════
   SSE STREAM LISTENER
═══════════════════════════════════════════════════════ */
function startSSEStream() {
  // ── BACKEND ──
  // Connect to the SSE stream endpoint. The backend sends newline-delimited
  // JSON objects in the format: data: {"type":"...", "data":...}\n\n
  const es = new EventSource('/stream');
  state.storyEventSource = es;

  es.onmessage = e => {
    try {
      const parsed = JSON.parse(e.data);
      handleSSEEvent(parsed);
      if (parsed.type === 'done' || parsed.type === 'error') {
        es.close();
        state.storyEventSource = null;
      }
    } catch (err) {
      appendLog(`[parse error] ${e.data}`, 'log-red');
    }
  };

  es.onerror = () => {
    if (state.isGenerating) {
      appendLog('⚠️ Connection interrupted. Retrying…', 'log-red');
    }
    // SSE auto-reconnects on error unless we close it
    // Only close if generation is done
    if (!state.isGenerating) {
      es.close();
      state.storyEventSource = null;
    }
  };
}

/* ═══════════════════════════════════════════════════════
   FORM SUBMISSION
═══════════════════════════════════════════════════════ */
function collectFormData() {
  return {
    // ── BACKEND ──
    // These field names match the Python backend's expected payload.
    // Adjust if your backend uses different keys.
    user_description:   $('story_description').value.trim(),
    number_of_chapters: parseInt($('number_of_chapters').value),
    number_of_main:     parseInt($('number_of_main').value),
    number_of_side:     parseInt($('number_of_side').value),
    number_of_passing:  parseInt($('number_of_passing').value),
    pov:                state.pov,
    tense:              state.tense,
    writing_style:      $('writing_style').value.trim(),
  };
}

function validateForm(data) {
  if (!data.user_description) {
    flashField('story_description', 'Please describe your story premise.');
    return false;
  }
  return true;
}

function flashField(fieldId, message) {
  const field = $(fieldId);
  if (!field) return;

  field.style.borderColor = 'rgba(196,123,110,0.8)';
  field.style.boxShadow   = '0 0 0 3px rgba(196,123,110,0.15)';
  field.focus();

  // Show tooltip-style error
  const existing = field.parentElement.querySelector('.field-error');
  if (!existing) {
    const err = document.createElement('p');
    err.className = 'field-error';
    err.style.cssText = 'color:#c47b6e;font-size:12px;margin-top:6px;';
    err.textContent = message;
    field.parentElement.insertBefore(err, field.nextSibling);
  }

  setTimeout(() => {
    field.style.borderColor = '';
    field.style.boxShadow = '';
    const err = field.parentElement.querySelector('.field-error');
    if (err) err.remove();
  }, 3000);
}

async function handleSubmit(e) {
  e.preventDefault();
  if (state.isGenerating) return;

  const formData = collectFormData();
  if (!validateForm(formData)) return;

  // ── UI: loading state ──
  state.isGenerating = true;
  DOM.generateBtn.disabled = true;
  DOM.generateBtn.classList.add('loading');
  DOM.generateBtn.querySelector('.btn-submit-text').textContent = 'Weaving…';

  // Build initial pipeline (5 chapter estimate; will rebuild when outline arrives)
  buildPipelineSteps(formData.number_of_chapters);

  // Show progress section
  DOM.progressSection.classList.remove('hidden');
  DOM.progressSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

  // Reset chapter state
  state.completedChapters = 0;
  state.totalChapters = formData.number_of_chapters;
  state.chapters = [];
  DOM.chapterCards.innerHTML = '';
  DOM.outlinePanel.classList.add('hidden');
  DOM.doneBanner.classList.add('hidden');
  DOM.logBody.innerHTML = '';

  appendLog('✦ Initialising story agents…', 'log-gold');

  try {
    // ── BACKEND ──
    // POST to /generate to kick off the generation pipeline.
    // The backend should start the agents and return 200 OK immediately.
    // Progress is then streamed via SSE at /stream.
    const response = await fetch('/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData),
    });

    if (!response.ok) {
      let errMsg = `HTTP ${response.status}`;
      try { const j = await response.json(); errMsg = j.error || errMsg; } catch {}
      throw new Error(errMsg);
    }

    // Start listening to the SSE stream
    startSSEStream();

  } catch (err) {
    appendLog(`❌ Failed to start generation: ${err.message}`, 'log-red');
    DOM.generateBtn.classList.remove('loading');
    DOM.generateBtn.disabled = false;
    DOM.generateBtn.querySelector('.btn-submit-text').textContent = 'Weave My Story';
    state.isGenerating = false;
  }
}

/* ═══════════════════════════════════════════════════════
   OPTIONAL: STATUS POLLING (fallback if SSE isn't used)
   Uncomment and adapt this block if your backend
   doesn't support SSE and instead exposes a polling endpoint.
═══════════════════════════════════════════════════════ */
/*
let pollInterval = null;

async function pollStatus() {
  try {
    // ── BACKEND ──
    // Replace with your actual status endpoint.
    // Expected response shape:
    // {
    //   stage: "Writing Chapter 2",
    //   progress_pct: 42,
    //   log: ["line 1", "line 2"],
    //   outline: { chapters: [{number, title, synopsis}] },
    //   completed_chapters: [{number, title, text}],
    //   is_done: false,
    //   error: null
    // }
    const res = await fetch('/api/status');
    const data = await res.json();

    if (data.stage)    handleSSEEvent({ type: 'stage',   data: data.stage });
    if (data.log)      data.log.forEach(line => appendLog(line));
    if (data.outline)  handleSSEEvent({ type: 'outline', data: data.outline });
    if (data.completed_chapters) {
      data.completed_chapters.forEach(ch => handleSSEEvent({ type: 'chapter', data: ch }));
    }
    if (data.is_done)  {
      handleSSEEvent({ type: 'done', data: { total_chapters: data.total_chapters } });
      clearInterval(pollInterval);
    }
    if (data.error)    handleSSEEvent({ type: 'error',   data: data.error });

  } catch (err) {
    appendLog(`⚠️ Poll error: ${err.message}`, 'log-red');
  }
}

function startPolling() {
  pollInterval = setInterval(pollStatus, 2000);
}
*/

/* ═══════════════════════════════════════════════════════
   UTILITY
═══════════════════════════════════════════════════════ */
function escHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/* ═══════════════════════════════════════════════════════
   INIT
═══════════════════════════════════════════════════════ */
function init() {
  initTheme();
  initSliders();
  initTogglePills();
  initScrollReveal();
  initHeroCta();
  initLogToggle();
  initOutlineToggle();
  initModal();

  // Form submission
  DOM.form.addEventListener('submit', handleSubmit);

  // "Weave Another Story" resets state
  document.addEventListener('click', e => {
    if (e.target.matches('[onclick="location.reload()"]')) return; // handled inline
  });
}

// Run after DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
