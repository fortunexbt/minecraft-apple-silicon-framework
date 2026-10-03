'use strict';

const byId = id => document.getElementById(id);
const repo = 'https://github.com/fortunexbt/minecraft-apple-silicon-framework';
let entries = [];
let loadFailed = false;

function node(tag, text, attrs = {}) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
  return el;
}

function asText(value, fallback = '') {
  return typeof value === 'string' && value.trim() ? value.trim() : fallback;
}

function finite(value) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function formatNumber(value, digits = 1) {
  const parsed = finite(value);
  return parsed === null ? '—' : parsed.toLocaleString('en-US', { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

function titleCase(value) {
  return asText(value, 'Unknown').replace(/[_-]+/g, ' ').replace(/\b\w/g, letter => letter.toUpperCase());
}

function hardware(entry) {
  return entry.metadata && entry.metadata.hardware ? entry.metadata.hardware : {};
}

function settings(entry, phase = 'candidate') {
  const metadata = entry.metadata || {};
  const config = metadata[phase] || {};
  return config.settings || {};
}

function shaderName(entry) {
  const shader = (entry.metadata && entry.metadata.candidate && entry.metadata.candidate.shader) || {};
  const name = titleCase(asText(shader.name, 'Shader setup'));
  const version = asText(shader.version);
  return version ? name + ' ' + version : name;
}

function setupTitle(entry) {
  const presentation = entry.presentation || {};
  if (typeof presentation.title === 'string' && presentation.title.trim()) return presentation.title.trim();
  const chip = hardware(entry);
  return shaderName(entry) + ' · ' + titleCase(asText(chip.family, 'Apple Silicon')) + ' ' + titleCase(asText(chip.tier, ''));
}

function githubProfile(handle, minecraftProfile) {
  const safeHandle = /^[A-Za-z0-9-]{1,39}$/.test(handle || '') ? handle : 'unknown';
  const link = node('a', undefined, {
    class: 'contributor',
    href: 'https://github.com/' + encodeURIComponent(safeHandle),
    target: '_blank',
    rel: 'noopener noreferrer'
  });
  let skin = typeof minecraftProfile === 'string' && /^(?:[A-Za-z0-9_]{3,16}|[a-fA-F0-9]{32}|[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})$/.test(minecraftProfile);
  const defaultFace = 'https://mc-heads.net/avatar/MHF_Steve/64';
  const avatar = node('span', safeHandle.slice(0, 2).toUpperCase(), { class: 'avatar skin-avatar', 'aria-hidden': 'true' });
  const image = node('img', undefined, {
    src: skin ? 'https://mc-heads.net/avatar/' + encodeURIComponent(minecraftProfile) + '/64' : defaultFace,
    alt: '',
    loading: 'lazy',
    decoding: 'async',
    referrerpolicy: 'no-referrer',
    width: '38',
    height: '38'
  });
  image.addEventListener('error', () => {
    if (skin) {
      skin = false;
      image.src = defaultFace;
    } else image.remove();
  });
  avatar.append(image);
  link.append(avatar, node('span', '@' + safeHandle));
  return link;
}

function safeScreenshotUrl(value) {
  if (typeof value !== 'string') return null;
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' || url.username || url.password) return null;
    if (url.hostname === 'raw.githubusercontent.com' && url.pathname.length > 1) return url.href;
    if (url.hostname === 'github.com' && url.pathname.startsWith('/user-attachments/')) return url.href;
  } catch {}
  return null;
}

function safeRecipeUrl(value) {
  if (typeof value !== 'string') return null;
  try {
    const url = new URL(value);
    if (url.protocol === 'https:' && url.hostname === 'github.com' && !url.username && !url.password) return url.href;
  } catch {}
  return null;
}

function evidenceUrl(entry) {
  const provided = safeRecipeUrl(entry.evidence);
  if (provided) return provided;
  if (/^[a-f0-9]{64}$/.test(entry.digest || '')) {
    return repo + '/blob/main/contributions/' + entry.digest + '.json';
  }
  return repo + '/tree/main/contributions';
}

function recipeUrl(entry) {
  const presentation = entry.presentation || {};
  return safeRecipeUrl(presentation.recipe_url) || evidenceUrl(entry);
}

function outputResolution(value) {
  if (!Array.isArray(value) || value.length !== 2) return null;
  const width = finite(value[0]);
  const height = finite(value[1]);
  if (width === null || height === null || width <= 0 || height <= 0) return null;
  return [Math.round(width), Math.round(height)];
}

function resolutionInfo(entry) {
  const config = settings(entry);
  const output = outputResolution(config.resolution);
  const scale = finite(config.scale);
  if (!output) return { output: 'Not recorded', internal: null, scale: scale };
  const outputLabel = output[0] + ' × ' + output[1];
  if (scale === null || scale <= 0) return { output: outputLabel, internal: null, scale: null };
  const internal = [Math.round(output[0] * scale), Math.round(output[1] * scale)];
  return { output: outputLabel, internal: '≈' + internal[0] + ' × ' + internal[1], scale: scale };
}

function average(entry, run = 'candidate') {
  const metrics = entry.runs && entry.runs[run] ? entry.runs[run] : {};
  return finite(metrics.average_fps);
}

function worstFps(entry, run = 'candidate') {
  const metrics = entry.runs && entry.runs[run] ? entry.runs[run] : {};
  return finite(metrics.worst_5s_fps);
}

function renderDistance(entry) {
  return finite(settings(entry).render_distance);
}

function chipLabel(entry) {
  const chip = hardware(entry);
  return titleCase(asText(chip.family, 'Apple Silicon')) + ' · ' + titleCase(asText(chip.tier, 'Unknown tier'));
}

function memoryLabel(entry) {
  const gib = finite(hardware(entry).memory_gib);
  return gib === null ? 'Memory not recorded' : formatNumber(gib, 0) + ' GB RAM';
}

function makeFilterOptions(id, values, placeholder, label) {
  const select = byId(id);
  const selected = select.value;
  select.replaceChildren(node('option', placeholder, { value: '' }));
  for (const value of values) select.append(node('option', label(value), { value: String(value) }));
  if (values.some(value => String(value) === selected)) select.value = selected;
}

function populateFilters() {
  const families = [...new Set(entries.map(entry => asText(hardware(entry).family)).filter(Boolean))].sort((a, b) => a.localeCompare(b));
  const tiers = [...new Set(entries.map(entry => asText(hardware(entry).tier)).filter(Boolean))].sort((a, b) => a.localeCompare(b));
  const memories = [...new Set(entries.map(entry => finite(hardware(entry).memory_gib)).filter(value => value !== null))].sort((a, b) => a - b);
  makeFilterOptions('filter-family', families, 'All families', value => value);
  makeFilterOptions('filter-tier', tiers, 'All tiers', titleCase);
  makeFilterOptions('filter-memory', memories, 'Any memory', value => formatNumber(value, 0) + ' GB');
}

function createCover(entry, title) {
  const cover = node('div', undefined, { class: 'setup-cover' });
  const fallback = node('div', undefined, { class: 'cover-placeholder', role: 'img', 'aria-label': 'Screenshot unavailable for this setup' });
  fallback.append(node('span', 'SCREENSHOT UNAVAILABLE', { class: 'placeholder-kicker' }), node('strong', 'Recipe first.', { class: 'placeholder-title' }), node('span', 'View the recipe and evidence', { class: 'placeholder-note' }));
  cover.append(fallback);

  const screenshot = safeScreenshotUrl((entry.presentation || {}).screenshot_url);
  if (screenshot) {
    const image = node('img', undefined, { class: 'setup-image', src: screenshot, alt: title, loading: 'lazy', decoding: 'async' });
    image.addEventListener('load', () => { fallback.hidden = true; });
    image.addEventListener('error', () => image.remove());
    cover.append(image);
  }

  const fps = average(entry);
  const performance = node('div', undefined, { class: 'performance-badge', 'aria-label': fps === null ? 'Candidate average FPS not recorded' : 'Candidate average FPS ' + formatNumber(fps) });
  performance.append(node('strong', fps === null ? '—' : formatNumber(fps)), node('span', 'avg FPS'));
  cover.append(performance);
  return cover;
}

function dataRow(label, value, note) {
  const cell = node('div', undefined, { class: 'spec-item' });
  cell.append(node('span', label, { class: 'spec-label' }), node('strong', value, { class: 'spec-value' }));
  if (note) cell.append(node('small', note, { class: 'spec-note' }));
  return cell;
}

function countMetric(value) {
  if (value && typeof value === 'object') return finite(value.count);
  return finite(value);
}

function detailsFor(entry) {
  const details = node('details', undefined, { class: 'advanced-details' });
  details.append(node('summary', 'More setup and performance details'));
  const metadata = entry.metadata || {};
  const candidate = entry.runs && entry.runs.candidate ? entry.runs.candidate : {};
  const baseline = entry.runs && entry.runs.baseline ? entry.runs.baseline : {};
  const workload = metadata.workload || {};
  const quality = metadata.quality_review || {};
  const rows = [
    ['Mac model', [asText(hardware(entry).model), asText(hardware(entry).model_identifier)].filter(Boolean).join(' · ') || 'Not recorded'],
    ['Measurement', 'CPU frame production; not displayed or generated FPS'],
    ['Minecraft', asText(metadata.minecraft, 'Not recorded')],
    ['Launcher and loader', [asText(metadata.launcher, 'Launcher not recorded'), metadata.loader ? titleCase(asText(metadata.loader.name, '')) + (metadata.loader.version ? ' ' + metadata.loader.version : '') : ''].filter(Boolean).join(' · ')],
    ['Runtime and harness', [asText(metadata.runtime), asText(metadata.harness)].filter(Boolean).join(' · ') || 'Not recorded'],
    ['Test scene', [asText(workload.scene), asText(workload.route), asText(workload.terrain)].filter(Boolean).join(' · ') || 'Not recorded'],
    ['Candidate worst 5 sec FPS', worstFps(entry) === null ? 'Not recorded' : formatNumber(worstFps(entry))],
    ['Candidate p95 / p99 frame time', formatNumber(candidate.p95_ms) + ' / ' + formatNumber(candidate.p99_ms) + ' ms'],
    ['Intervals over 33 / 50 / 100 ms', [countMetric(candidate.over_33), countMetric(candidate.over_50), countMetric(candidate.over_100)].map(value => value === null ? '—' : String(value)).join(' / ')],
    ['Local outliers, baseline → candidate', [countMetric(baseline.local_outliers), countMetric(candidate.local_outliers)].map(value => value === null ? '—' : String(value)).join(' → ')],
    ['Image review', asText(quality.outcome, 'Not recorded')]
  ];
  const list = node('dl');
  for (const [label, value] of rows) list.append(node('dt', label), node('dd', value));
  details.append(list);

  const setupDetails = node('details', undefined, { class: 'settings-details' });
  setupDetails.append(node('summary', 'Baseline and candidate settings'));
  setupDetails.append(node('pre', JSON.stringify({
    baseline: metadata.baseline || {},
    candidate: metadata.candidate || {}
  }, null, 2)));
  details.append(setupDetails);

  const fullEvidence = safeRecipeUrl(entry.evidence) || evidenceUrl(entry);
  details.append(node('a', 'Open full recipe and evidence ↗', { href: fullEvidence, target: '_blank', rel: 'noopener noreferrer', class: 'evidence-link' }));
  return details;
}

function setupPrompt(entry) {
  const recipe = recipeUrl(entry);
  const evidence = evidenceUrl(entry);
  return [
    'Check whether this shared shader setup suits my Mac, then try it in an isolated copy of my game.',
    '',
    'Recipe: ' + recipe,
    'Performance evidence: ' + evidence,
    '',
    'Inspect the actual shader, mod versions, Minecraft version, launcher, hardware, resolution, view distance, test scene, and quality notes in these links. Check compatibility with my installed game and explain any differences or tradeoffs before changing anything. Prepare and verify the setup in an isolated copy of my instance, preserve my worlds and current settings, and confirm the scene renders correctly. Never blindly apply the recipe to my live game or replace mods or versions without explaining the change to me.'
  ].join('\n');
}

function createCard(entry) {
  const title = setupTitle(entry);
  const card = node('article', undefined, { class: 'setup-card' });
  card.append(createCover(entry, title));

  const body = node('div', undefined, { class: 'card-body' });
  const top = node('div', undefined, { class: 'card-top' });
  const titleBlock = node('div', undefined, { class: 'card-title-block' });
  titleBlock.append(node('p', shaderName(entry), { class: 'eyebrow eyebrow-dark shader-kicker' }), node('h3', title));
  top.append(titleBlock, githubProfile(entry.author, (entry.presentation || {}).minecraft_profile));
  body.append(top);

  const hardwareLine = node('div', undefined, { class: 'hardware-line' });
  hardwareLine.append(node('span', chipLabel(entry), { class: 'hardware-chip' }));
  const gpuCores = finite(hardware(entry).gpu_cores);
  if (gpuCores !== null) hardwareLine.append(node('span', formatNumber(gpuCores, 0) + ' GPU cores', { class: 'hardware-chip secondary-chip' }));
  hardwareLine.append(node('span', memoryLabel(entry), { class: 'hardware-chip secondary-chip' }));
  body.append(hardwareLine);

  const resolution = resolutionInfo(entry);
  const scaleNote = resolution.scale === null ? 'Internal resolution not recorded' : resolution.internal + ' internal · ' + formatNumber(resolution.scale * 100, 0) + '% scale';
  const viewDistance = renderDistance(entry);
  const specs = node('div', undefined, { class: 'setup-specs' });
  specs.append(
    dataRow('Output resolution', resolution.output, scaleNote),
    dataRow('View distance', viewDistance === null ? 'Not recorded' : formatNumber(viewDistance, 0) + ' chunks')
  );
  body.append(specs);

  const lower = worstFps(entry);
  body.append(node('p', lower === null ? 'Community performance capture' : 'Worst 5 sec: ' + formatNumber(lower) + ' FPS', { class: 'stability-note' }));
  body.append(detailsFor(entry));

  const actions = node('div', undefined, { class: 'card-actions' });
  const recipe = recipeUrl(entry);
  actions.append(node('a', 'Open recipe ↗', { href: recipe, target: '_blank', rel: 'noopener noreferrer', class: 'recipe-link' }));
  const copy = node('button', 'Ask my agent to try this', { type: 'button', class: 'copy-setup' });
  const status = node('span', '', { class: 'card-copy-status', role: 'status' });
  copy.addEventListener('click', async () => {
    try {
      await copyText(setupPrompt(entry));
      status.textContent = 'Prompt copied. Paste it into your agent.';
    } catch {
      status.textContent = 'Copy failed. Open the recipe link and try again.';
    }
  });
  actions.append(copy, status);
  body.append(actions);
  card.append(body);
  return card;
}

function copyText(value) {
  if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(value);
  return new Promise((resolve, reject) => {
    const field = node('textarea');
    field.value = value;
    field.setAttribute('readonly', '');
    field.style.position = 'fixed';
    field.style.opacity = '0';
    document.body.append(field);
    field.select();
    const copied = document.execCommand('copy');
    field.remove();
    if (copied) resolve();
    else reject(new Error('Clipboard copy failed'));
  });
}

function matchingEntries() {
  const family = byId('filter-family').value;
  const tier = byId('filter-tier').value;
  const memory = byId('filter-memory').value;
  return entries.filter(entry => {
    const chip = hardware(entry);
    return (!family || asText(chip.family) === family)
      && (!tier || asText(chip.tier) === tier)
      && (!memory || String(finite(chip.memory_gib)) === memory);
  });
}

function sortEntries(list) {
  const sort = byId('sort-by').value;
  const score = entry => {
    if (sort === 'worst') return worstFps(entry);
    if (sort === 'distance') return renderDistance(entry);
    return average(entry);
  };
  return list.slice().sort((a, b) => {
    const left = score(a);
    const right = score(b);
    if (left === null && right !== null) return 1;
    if (right === null && left !== null) return -1;
    if (left !== right) return (right || 0) - (left || 0);
    return setupTitle(a).localeCompare(setupTitle(b));
  });
}

function showEmpty(title, message, actionLabel, action) {
  const empty = byId('empty-state');
  empty.replaceChildren(node('span', '✳', { class: 'empty-mark', 'aria-hidden': 'true' }), node('h3', title), node('p', message));
  if (action === 'dialog') empty.append(node('button', actionLabel, { type: 'button', class: 'button button-dark', 'data-dialog': 'participate' }));
  if (action === 'clear') {
    const clear = node('button', actionLabel, { type: 'button', class: 'button button-dark' });
    clear.addEventListener('click', () => {
      byId('filter-family').value = '';
      byId('filter-tier').value = '';
      byId('filter-memory').value = '';
      render();
    });
    empty.append(clear);
  }
  if (action === 'repository') {
    empty.append(node('a', actionLabel, { href: repo, target: '_blank', rel: 'noopener noreferrer', class: 'button button-dark' }));
  }
  empty.hidden = false;
}

function render() {
  const results = byId('results');
  const empty = byId('empty-state');
  const filters = byId('filters');
  results.replaceChildren();
  empty.hidden = true;
  filters.hidden = entries.length === 0 || loadFailed;

  if (loadFailed) {
    byId('count').textContent = 'Library unavailable';
    showEmpty('Could not load the setup library.', 'Reload this page or open the project repository to inspect the published data.', 'Open GitHub ↗', 'repository');
    return;
  }

  if (entries.length === 0) {
    byId('count').textContent = 'No setups yet';
    byId('load-status').textContent = 'No community setups have been published yet.';
    showEmpty('The first setup could be yours.', 'There are no community setup cards yet. Tune your own game with an agent, or share a recipe that another player can try.', 'Start with your setup ↗', 'dialog');
    return;
  }

  const selected = sortEntries(matchingEntries());
  byId('count').textContent = selected.length + (selected.length === 1 ? ' setup' : ' setups');
  byId('load-status').textContent = selected.length + (selected.length === 1 ? ' setup shown.' : ' setups shown.');
  if (selected.length === 0) {
    showEmpty('No setups match those filters.', 'Try another chip family, tier, or memory size.', 'Clear filters', 'clear');
    return;
  }
  const fragment = document.createDocumentFragment();
  for (const entry of selected) fragment.append(createCard(entry));
  results.append(fragment);
}

function openDialog(id) {
  const dialog = byId(id);
  if (dialog && !dialog.open) dialog.showModal();
}

document.addEventListener('click', event => {
  const button = event.target.closest('[data-dialog]');
  if (button) openDialog(button.dataset.dialog);
});
document.querySelectorAll('dialog .close').forEach(button => button.addEventListener('click', () => button.closest('dialog').close()));
document.querySelectorAll('dialog').forEach(dialog => dialog.addEventListener('click', event => {
  if (event.target === dialog) dialog.close();
}));
['filter-family', 'filter-tier', 'filter-memory', 'sort-by'].forEach(id => byId(id).addEventListener('change', render));

async function load() {
  try {
    const response = await fetch('data.json');
    if (!response.ok) throw new Error('Data request failed');
    const data = await response.json();
    if (!Array.isArray(data.entries)) throw new Error('Invalid evidence index');
    entries = data.entries.filter(entry => entry && entry.metadata && entry.runs);
    populateFilters();
    render();
  } catch {
    loadFailed = true;
    byId('load-status').textContent = 'Could not load the setup library.';
    render();
  }
}

byId('copy-prompt').addEventListener('click', async () => {
  try {
    await copyText(byId('agent-prompt').textContent);
    byId('copy-status').textContent = 'Copied — paste it into your agent.';
  } catch {
    byId('copy-status').textContent = 'Select and copy the prompt above.';
  }
});
load();
