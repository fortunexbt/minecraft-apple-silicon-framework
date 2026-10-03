'use strict';
const byId = id => document.getElementById(id);
let entries = [], view = 'pacing';
function node(tag, text, attrs = {}) { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; for (const [k,v] of Object.entries(attrs)) el.setAttribute(k,v); return el; }
function openDialog(id) { byId(id).showModal(); }
document.addEventListener('click', event => { const button = event.target.closest('[data-dialog]'); if (button) openDialog(button.dataset.dialog); });
document.querySelectorAll('dialog .close').forEach(button => button.addEventListener('click', () => button.closest('dialog').close()));
document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => { view = button.dataset.view; document.querySelectorAll('[data-view]').forEach(b => b.setAttribute('aria-pressed', String(b === button))); render(); }));
byId('cohort').addEventListener('change', render);
const number = value => Number.isFinite(value) ? value.toFixed(1) : '—';
function detail(entry) {
  const target = byId('detail-content'); target.replaceChildren();
  target.append(node('span', 'SELF-REPORTED EXPERIMENT', {class:'eyebrow'}), node('h2', entry.author), node('p', 'Matched baseline → candidate. Metrics are recomputed from relative frame intervals. Configuration and visual claims remain operator declarations.'));
  const m = entry.metadata, a = entry.runs.baseline, b = entry.runs.candidate;
  const rows = [ ['Hardware', `${m.hardware.family} ${m.hardware.tier} · ${m.hardware.gpu_cores} GPU cores · ${m.hardware.memory_gib} GiB`], ['Workload', `${m.workload.scene} / ${m.workload.route} / ${m.workload.terrain}`], ['Setup', `${m.launcher} · ${m.minecraft} · ${m.loader.name} ${m.loader.version}`], ['Harness', m.harness], ['Changed fields', m.interventions.join(', ')], ['Quality review', m.quality_review.outcome], ['Average FPS', `${number(a.average_fps)} → ${number(b.average_fps)}`], ['Worst 5s FPS', `${number(a.worst_5s_fps)} → ${number(b.worst_5s_fps)}`], ['p95 / p99 candidate', `${number(b.p95_ms)} / ${number(b.p99_ms)} ms`], ['Intervals over 33 / 50 / 100 ms', `${b.over_33.count} / ${b.over_50.count} / ${b.over_100.count}`], ['Local outliers', `${a.local_outliers.count} → ${b.local_outliers.count}`] ];
  const list = node('dl'); for (const [label,value] of rows) { list.append(node('dt', label), node('dd', value)); } target.append(list);
  const url = `https://github.com/fortunexbt/minecraft-apple-silicon-framework/blob/main/contributions/${entry.digest}.json`;
  target.append(node('a','Inspect full recipe and relative traces ↗',{href:url}),node('pre',JSON.stringify({baseline:m.baseline,candidate:m.candidate},null,2)));
  openDialog('detail');
}
function svgNode(tag, attrs={}, text) { const el=document.createElementNS('http://www.w3.org/2000/svg',tag); for(const [key,value] of Object.entries(attrs)) el.setAttribute(key,value); if(text!==undefined) el.textContent=text; return el; }
function chart(selected) {
  const target=byId('chart'); target.replaceChildren();
  if (!selected.length) { const empty=node('div',undefined,{class:'empty'}); empty.append(node('span','+',{class:'cross'}),node('h2','The next point could be yours.'),node('p','No community experiments have been published in this cohort. Start with a baseline and share a result worth repeating.'),node('button','Make a contribution ↗',{'data-dialog':'participate'})); target.append(empty); return; }
  const svg=svgNode('svg',{viewBox:'0 0 900 330',role:'img','aria-label':view==='pacing'?'Matched baseline and candidate frame pacing':'Candidate improvement over its own baseline'});
  const points=selected.flatMap(e=>['baseline','candidate'].map(run=>({entry:e,run,x:view==='pacing'?e.runs[run].p95_ms:(run==='baseline'?0:(e.runs.candidate.worst_5s_fps/e.runs.baseline.worst_5s_fps-1)*100), y:view==='pacing'?e.runs[run].worst_5s_fps:(run==='baseline'?0:(1-e.runs.candidate.p95_ms/e.runs.baseline.p95_ms)*100)})));
  const xs=points.map(p=>p.x), ys=points.map(p=>p.y); const xmin=Math.min(0,...xs), xmax=Math.max(1,...xs), ymin=Math.min(0,...ys), ymax=Math.max(1,...ys); const xp=x=>75+(x-xmin)/(xmax-xmin)*745, yp=y=>270-(y-ymin)/(ymax-ymin)*220;
  for(let i=0;i<5;i++){ const x=xmin+(xmax-xmin)*i/4,y=ymin+(ymax-ymin)*i/4; svg.append(svgNode('line',{x1:75,x2:820,y1:yp(y),y2:yp(y),stroke:'#c6d9b72a','stroke-dasharray':'3 5'}),svgNode('text',{x:62,y:yp(y)+4,'text-anchor':'end'},number(y)),svgNode('text',{x:xp(x),y:290,'text-anchor':'middle'},number(x))); }
  selected.forEach(entry=>{const pair=points.filter(p=>p.entry===entry); svg.append(svgNode('line',{x1:xp(pair[0].x),y1:yp(pair[0].y),x2:xp(pair[1].x),y2:yp(pair[1].y),stroke:'#daca86',opacity:'.7'}));});
  points.forEach(p=>{const dot=svgNode('circle',{cx:xp(p.x),cy:yp(p.y),r:p.run==='baseline'?5:7,class:p.run==='baseline'?'baseline':'point',tabindex:0,role:'button','aria-label':`${p.entry.author} ${p.run}: open evidence`}); dot.append(svgNode('title',{},`${p.entry.author} · ${p.run}`)); dot.addEventListener('click',()=>detail(p.entry)); dot.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();detail(p.entry);}}); svg.append(dot); });
  svg.append(svgNode('text',{x:450,y:320,'text-anchor':'middle'},view==='pacing'?'p95 frame time (ms) · lower is better':'Worst 5s FPS improvement (%)'),svgNode('text',{x:75,y:22},view==='pacing'?'Worst 5s FPS · higher is better':'p95 frame-time reduction (%) · higher is better')); target.append(svg);
}
function render() {
 const selected=entries.filter(e=>e.cohort===byId('cohort').value); const body=byId('results'); body.replaceChildren();
 if(!selected.length){const row=node('tr');row.append(node('td','No published community results yet. The first contribution starts here.',{colspan:'6',class:'empty-row'}));body.append(row);}
 for(const e of selected){const row=node('tr'),a=e.runs.baseline,b=e.runs.candidate; for(const value of [e.author,e.metadata.interventions.join(', '),`${number(a.worst_5s_fps)} → ${number(b.worst_5s_fps)}`,`${number(a.p95_ms)} → ${number(b.p95_ms)} ms`,e.metadata.quality_review.outcome]) row.append(node('td',value)); const cell=node('td'),button=node('button','Inspect ↗');button.addEventListener('click',()=>detail(e));cell.append(button);row.append(cell);body.append(row);}
 byId('count').textContent=`${entries.length} experiments · ${new Set(entries.map(e=>e.cohort)).size} cohorts`; chart(selected);
}
async function load(){try{const response=await fetch('data.json');if(!response.ok)throw new Error('Data request failed');const data=await response.json();if(!Array.isArray(data.entries))throw new Error('Invalid data');entries=data.entries;const seen=new Set();for(const e of entries){if(!/^[a-f0-9]{64}$/.test(e.digest)||!/^[a-f0-9]{64}$/.test(e.cohort))throw new Error('Invalid identity');if(!seen.has(e.cohort)){seen.add(e.cohort);const m=e.metadata;byId('cohort').append(node('option',`${m.hardware.family} ${m.hardware.tier} · ${m.workload.scene} · ${e.cohort.slice(0,8)}`,{value:e.cohort}));}}if(entries.length){byId('cohort').value=entries[0].cohort;byId('cohort').querySelector('option[value=""]').remove();}render();byId('load-status').textContent='Published after repository review. All current entries remain self-reported.';}catch(error){byId('count').textContent='Evidence unavailable';byId('load-status').textContent='Could not load the public evidence index. Please reload or inspect the GitHub repository.';byId('chart').replaceChildren(node('p','Evidence is unavailable. Reload to retry.'));}}
load();
