// Detect the base URL automatically. If we are running through the combined web server (port 8080), 
// the API is at /api. If we are running standalone, we use the fallback.
const API = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? (window.location.port === '8080' ? '/api' : 'http://localhost:8080/api')
  : (window.location.origin + '/api'); 
console.log('Using API:', API);
let selectedFile = null;
let selectedTech = 'spike';  // Default to spike
let startTime    = null;

// ── Scroll helper ─────────────────────────────────────────────────────────────
function scrollToUpload() {
  document.getElementById('uploadSection').scrollIntoView({ behavior: 'smooth' });
}

// ── DOM Ready - Setup all event listeners ────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
  console.log('DOM loaded, setting up event listeners...');
  
  // ── Technique pills ─────────────────────────────────────────────────────────
  const techButtons = document.querySelectorAll('.tech-pill');
  console.log('Found', techButtons.length, 'technique buttons');
  
  techButtons.forEach(btn => {
    console.log('Setting up button:', btn.dataset.tech);
    btn.addEventListener('click', e => {
      e.stopPropagation();
      console.log('Button clicked:', btn.dataset.tech);
      
      // Only remove active from non-special pills (spike, serve, block, dig)
      if (!btn.classList.contains('special')) {
        document.querySelectorAll('.tech-pill:not(.special)').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      } else {
        // Special pills (match, team) toggle independently
        document.querySelectorAll('.tech-pill:not(.special)').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tech-pill.special').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      }
      selectedTech = btn.dataset.tech;
      console.log('Selected technique updated to:', selectedTech);
    });
  });

  // ── File handling ───────────────────────────────────────────────────────────
  const fileInput = document.getElementById('fileInput');
  const uploadZone = document.getElementById('uploadZone');
  
  if (fileInput) {
    console.log('Setting up file input listener');
    fileInput.addEventListener('change', e => {
      console.log('File input changed', e.target.files);
      if (e.target.files[0]) handleFile(e.target.files[0]);
    });
  } else {
    console.error('fileInput element not found!');
  }

  if (uploadZone) {
    console.log('Setting up upload zone listeners');
    uploadZone.addEventListener('dragover',  e => { e.preventDefault(); uploadZone.classList.add('drag-over'); });
    uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
    uploadZone.addEventListener('drop', e => {
      e.preventDefault(); uploadZone.classList.remove('drag-over');
      console.log('File dropped', e.dataTransfer.files);
      if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
    });
  } else {
    console.error('uploadZone element not found!');
  }
});

function handleFile(file) {
  selectedFile = file;
  document.getElementById('fileName').textContent = file.name;
  document.getElementById('fileSize').textContent = fmtSize(file.size);
  document.getElementById('filePreview').classList.add('show');
  document.getElementById('analyseBtn').classList.add('show');
  document.getElementById('errorBox').classList.remove('show');
}

function fmtSize(b) {
  return b < 1048576 ? (b/1024).toFixed(1)+' KB' : (b/1048576).toFixed(1)+' MB';
}

function resetUpload() {
  selectedFile = null;
  document.getElementById('fileInput').value = '';
  document.getElementById('filePreview').classList.remove('show');
  document.getElementById('analyseBtn').classList.remove('show');
  document.getElementById('errorBox').classList.remove('show');
}

// ── View Toggle ──────────────────────────────────────────────────────────────
function setView(view) {
  const vid = document.getElementById('resultVideo');
  const map = document.getElementById('shotMapContainer');
  const btnVid = document.getElementById('btnShowVideo');
  const btnMap = document.getElementById('btnShowMap');

  if (view === 'video') {
    vid.style.display = 'block';
    map.style.display = 'none';
    btnVid.style.opacity = '1';
    btnMap.style.opacity = '0.5';
  } else {
    vid.style.display = 'none';
    map.style.display = 'block';
    btnVid.style.opacity = '0.5';
    btnMap.style.opacity = '1';
  }
}

// ── Analysis ──────────────────────────────────────────────────────────────────
async function startAnalysis() {
  if (!selectedFile) return;
  
  console.log('Starting analysis with technique:', selectedTech);
  
  // Customise progress steps for Team/Match
  if (selectedTech === 'team' || selectedTech === 'match') {
    const steps = [
      'Detecting court & corners',
      'Multi-player tracking (ByteTrack)',
      'Jersey recognition (TrOCR)',
      'Warping to 2D court map',
      'Generating team heatmaps',
      'Finalizing tactical report'
    ];
    document.querySelectorAll('.steps li').forEach((li, i) => {
      li.innerHTML = `<span class="step-icon">${i+1}</span> ${steps[i]}`;
    });
  } else {
    // Reset to default steps
    const steps = [
      'Checking video quality',
      'Detecting technique & timing',
      'Extracting 3D pose skeleton',
      'Comparing to elite athletes',
      'Generating AI coaching',
      'Rendering annotated video'
    ];
    document.querySelectorAll('.steps li').forEach((li, i) => {
      li.innerHTML = `<span class="step-icon">${i+1}</span> ${steps[i]}`;
    });
  }

  startTime = Date.now();
  showSection('progress');
  animateSteps();

  const form = new FormData();
  form.append('video', selectedFile);

  // Team tracking mode
  if (selectedTech === 'team') {
    try {
      const res = await fetch(`${API}/visualise/tracking`, { 
        method: 'POST', 
        body: form,
        headers: { 'ngrok-skip-browser-warning': 'true' }
      });
      if (!res.ok) { showError('Team tracking failed — make sure multiple players are visible'); return; }
      const blob = URL.createObjectURL(await res.blob());
      const players = res.headers.get('X-Players-Detected') || '?';
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1) + 's';
      showResults({
        videoUrl: blob, verdict: players + ' PLAYERS', score: players + ' tracked',
        technique: 'team', elapsed,
        coaching: { headline: `Tracked ${players} players with colour-coded skeletons and movement trails.`, fixes: [], next_session_focus: 'Review player positioning and court coverage' },
        metrics: {},
      });
    } catch (err) { showError('Could not connect to the analysis server.'); }
    return;
  }

  // Full match mode
  if (selectedTech === 'match') {
    try {
      const res = await fetch(`${API}/analyse/match?mode=match`, { method: 'POST', body: form });
      if (!res.ok) { const e = await res.json().catch(()=>({})); showError(e?.detail?.error || 'Match analysis failed'); return; }
      const data = await res.json();
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1) + 's';
      showMatchResults(data, elapsed);
    } catch (err) { showError('Could not connect to the analysis server.'); }
    return;
  }

  try {
    // Step 1: Start async job
    const technique = selectedTech !== 'auto' ? `&technique=${selectedTech}` : '';
    console.log('Starting async job:', `${API}/analyse/auto/async${technique}`);
    
    const startRes = await fetch(`${API}/analyse/auto/async?output=json${technique}`, {
      method: 'POST', 
      body: form
    });

    if (!startRes.ok) {
      const err = await startRes.json().catch(() => ({}));
      const msg = err?.detail?.quality?.issues?.[0] || err?.detail?.error || err?.detail || 'Analysis failed';
      showError(typeof msg === 'string' ? msg : JSON.stringify(msg));
      return;
    }

    const { job_id } = await startRes.json();
    console.log('Job started:', job_id);

    // Step 2: Poll for results
    let attempts = 0;
    const maxAttempts = 120; // 4 minutes max (2s intervals)
    
    const pollJob = async () => {
      attempts++;
      
      try {
        const jobRes = await fetch(`${API}/job/${job_id}`);
        const job = await jobRes.json();
        
        console.log(`Poll ${attempts}: ${job.status}`);
        
        if (job.status === 'completed') {
          const data = job.result;
          
          if (data.bad_video_advice) { 
            showError(data.bad_video_advice); 
            return; 
          }

          const seg = (data.segments || []).find(s => s.analysis);
          if (!seg) {
            showError('No technique detected. Make sure the athlete is clearly visible performing a volleyball technique, with a side-on camera angle.');
            return;
          }

          // Step 3: Get annotated video
          const form2 = new FormData();
          form2.append('video', selectedFile);
          
          const vidRes = await fetch(`${API}/analyse/auto?output=video${technique}`, {
            method: 'POST', 
            body: form2
          });

          let videoUrl = null;
          if (vidRes.ok && (vidRes.headers.get('content-type') || '').includes('video')) {
            const blob = await vidRes.blob();
            videoUrl = URL.createObjectURL(blob);
          }

          const elapsed = ((Date.now() - startTime) / 1000).toFixed(1) + 's';
          completeAllSteps();
          
          setTimeout(() => {
            showResults({
              videoUrl,
              verdict:   seg.analysis.verdict,
              score:     seg.analysis.score,
              technique: seg.technique,
              coaching:  seg.analysis.coaching || {},
              metrics:   seg.analysis.metrics  || {},
              elapsed,
            });
          }, 500);
          
        } else if (job.status === 'failed') {
          showError(job.error || 'Analysis failed');
          
        } else if (job.status === 'processing' || job.status === 'pending') {
          // Continue polling
          if (attempts < maxAttempts) {
            setTimeout(pollJob, 2000); // Poll every 2 seconds
          } else {
            showError('Analysis timeout - please try again with a shorter video');
          }
        }
        
      } catch (err) {
        console.error('Polling error:', err);
        if (attempts < maxAttempts) {
          setTimeout(pollJob, 2000);
        } else {
          showError('Connection error during analysis');
        }
      }
    };
    
    // Start polling after 2 seconds
    setTimeout(pollJob, 2000);

  } catch (err) {
    console.error('Analysis error:', err);
    showError(`Connection error: ${err.message}. Make sure the backend is running.`);
  }
}

// ── Step animation ────────────────────────────────────────────────────────────
let stepTimeouts = [];

function animateSteps() {
  // Clear any existing timeouts
  stepTimeouts.forEach(timeout => clearTimeout(timeout));
  stepTimeouts = [];
  
  const ids    = ['s1','s2','s3','s4','s5','s6'];
  const delays = [0, 5000, 14000, 25000, 38000, 55000];
  ids.forEach((id, i) => {
    const timeout = setTimeout(() => {
      if (i > 0) {
        const prev = document.getElementById(ids[i-1]);
        if (prev) { prev.className = 'done'; prev.querySelector('.step-icon').textContent = '✓'; }
      }
      const el = document.getElementById(id);
      if (el) el.className = 'active';
    }, delays[i]);
    stepTimeouts.push(timeout);
  });
}

function completeAllSteps() {
  // Immediately complete all steps
  stepTimeouts.forEach(timeout => clearTimeout(timeout));
  stepTimeouts = [];
  
  const ids = ['s1','s2','s3','s4','s5','s6'];
  ids.forEach((id, i) => {
    const el = document.getElementById(id);
    if (el) {
      el.className = 'done';
      el.querySelector('.step-icon').textContent = '✓';
    }
  });
}

// ── Render results ────────────────────────────────────────────────────────────
function showResults({ videoUrl, verdict, score, technique, coaching, metrics, elapsed }) {
  console.log('showResults called with videoUrl:', videoUrl);
  showSection('results');

  const [good, total] = (score || '0/5').split('/').map(Number);
  const pct = total ? good / total : 0;

  // Animated score ring with gradient
  const ring = document.getElementById('scoreRingFill');
  if (ring) {
    ring.style.stroke = pct >= 0.8 ? 'var(--green)' : pct >= 0.6 ? 'var(--blue)' : 'var(--red)';
    setTimeout(() => { ring.style.strokeDashoffset = 264 - pct * 264; }, 100);
  }
  
  // Animated score count-up (0 to final value over 1.5s)
  const scoreBigEl = document.getElementById('scoreBig');
  animateValue(scoreBigEl, 0, good, 1500);
  document.getElementById('scoreDenom').textContent = `/ ${total}`;

  const verdictMap = {
    'ELITE':      ['Elite Level 🏆', "Your technique matches Olympic-level athletes. Keep it up."],
    'GOOD':       ['Good Form ✓',    "Solid technique with a few areas to sharpen. You're on the right track."],
    'NEEDS WORK': ['Needs Work',     "Several areas need attention. The fixes below will make a real difference."],
  };
  const [vLabel, vDesc] = verdictMap[verdict] || ['Unknown', ''];
  document.getElementById('scoreVerdict').textContent = vLabel;
  document.getElementById('scoreDesc').textContent    = vDesc;

  const chip = document.getElementById('verdictChip');
  chip.textContent = verdict;
  chip.className = 'verdict-chip ' + (verdict === 'ELITE' ? 'v-ELITE' : verdict === 'GOOD' ? 'v-GOOD' : 'v-NEEDS-WORK');

  document.getElementById('mTech').textContent  = cap(technique);
  document.getElementById('mTime').textContent  = elapsed;
  document.getElementById('mConf').textContent  = 'High';
  document.getElementById('mScore').textContent = score;
  document.getElementById('mTech2').textContent = cap(technique);
  document.getElementById('mTime2').textContent = elapsed;

  const vid = document.getElementById('resultVideo');
  console.log('Video element found:', vid);
  if (videoUrl) {
    console.log('Setting video src to:', videoUrl);
    vid.src = videoUrl; 
    vid.style.display = 'block';
    console.log('Video src set, display:', vid.style.display);
    console.log('Video element src attribute:', vid.src);
    
    // Add error handler
    vid.onerror = (e) => {
      console.error('Video error:', e);
      console.error('Video error code:', vid.error?.code);
      console.error('Video error message:', vid.error?.message);
      
      // Show user-friendly message
      const videoCard = vid.closest('.video-card');
      if (videoCard && vid.error?.code === 4) {
        const errorMsg = document.createElement('div');
        errorMsg.style.cssText = `
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          background: var(--card);
          border: 1px solid var(--border);
          border-radius: 12px;
          padding: 24px;
          text-align: center;
          max-width: 400px;
        `;
        errorMsg.innerHTML = `
          <div style="font-size: 48px; margin-bottom: 16px;">🎬</div>
          <div style="font-family: 'Barlow Condensed', sans-serif; font-size: 24px; font-weight: 700; margin-bottom: 12px;">
            Video Ready!
          </div>
          <div style="color: var(--muted); font-size: 14px; line-height: 1.6; margin-bottom: 20px;">
            Your annotated video has been generated. Due to codec compatibility, please download it to watch.
          </div>
          <a href="${videoUrl}" download="sportsai-analysis.mp4" style="
            display: inline-block;
            padding: 12px 24px;
            background: var(--red);
            color: white;
            border-radius: 10px;
            text-decoration: none;
            font-family: 'Barlow Condensed', sans-serif;
            font-size: 18px;
            font-weight: 700;
          ">
            📥 Download Video
          </a>
        `;
        videoCard.style.position = 'relative';
        videoCard.appendChild(errorMsg);
        vid.style.opacity = '0.3';
      }
    };
    
    // Add loadeddata handler
    vid.onloadeddata = () => {
      console.log('Video loaded successfully, duration:', vid.duration);
    };
    
    // Try to load the video
    vid.load();
    console.log('Video load() called');
  } else {
    console.warn('No videoUrl provided');
    vid.style.display = 'none';
  }

  const col = document.getElementById('coachingCol');
  col.innerHTML = '';

  // Metrics — clean dot list
  if (Object.keys(metrics).length) {
    const mc = el('div', 'metrics-card');
    mc.innerHTML = '<div class="card-title">Metrics breakdown</div>';
    Object.entries(metrics).forEach(([name, val]) => {
      const isGood = val.status === 'GOOD';
      const row = el('div', 'metric-item');
      row.innerHTML = `
        <div class="metric-dot ${isGood ? 'dot-good' : 'dot-bad'}"></div>
        <div class="metric-name">${name.replace(/_/g,' ')}</div>
        <span class="metric-tag ${isGood ? 'tag-good' : 'tag-bad'}">${isGood ? 'Good' : 'Needs work'}</span>`;
      mc.appendChild(row);
    });
    col.appendChild(mc);
  }

  if (coaching.headline) {
    const hc = el('div', 'headline-card');
    hc.textContent = coaching.headline;
    col.appendChild(hc);
  }

  (coaching.fixes || []).slice(0, 3).forEach((fix, i) => {
    const fc = el('div', 'fix-card');
    fc.innerHTML = `
      <div class="fix-header">
        <div class="fix-num">${i+1}</div>
        <div class="fix-title">${(fix.metric||'').replace(/_/g,' ')}</div>
      </div>
      ${fix.feel_cue ? `<div class="fix-feel"><div class="fix-feel-label">FEEL</div><p>${fix.feel_cue}</p></div>` : ''}
      ${fix.drill ? `<div class="fix-drill-label">DRILL</div><div class="fix-drill-name">${fix.drill}</div><div class="fix-drill-rx">${fix.prescription||''}</div>` : ''}`;
    col.appendChild(fc);
  });

  if (coaching.next_session_focus) {
    const foc = el('div', 'focus-card');
    foc.innerHTML = `<div class="focus-label">NEXT SESSION FOCUS</div><p>${coaching.next_session_focus}</p>`;
    col.appendChild(foc);
  }
}


function showMatchResults(data, elapsed) {
  showSection('results');
  const summary = data.summary || {};
  document.getElementById('scoreBig').textContent   = summary.players_analysed || '?';
  document.getElementById('scoreDenom').textContent = 'players';
  document.getElementById('scoreVerdict').textContent = 'Match Analysis';
  document.getElementById('scoreDesc').textContent  =
    `${summary.total_techniques || 0} techniques detected across ${summary.players_analysed || 0} players in ${data.duration_sec}s`;

  const ring = document.getElementById('scoreRingFill');
  if (ring) { ring.style.stroke = 'var(--blue)'; setTimeout(() => { ring.style.strokeDashoffset = 100; }, 100); }

  const chip = document.getElementById('verdictChip');
  chip.textContent = 'MATCH MODE'; chip.className = 'verdict-chip v-GOOD';

  document.getElementById('mTech').textContent  = 'Full Match';
  document.getElementById('mScore').textContent = `${summary.players_analysed || 0} players`;
  document.getElementById('mTime').textContent  = elapsed;
  document.getElementById('mConf').textContent  = 'Multi-player';
  document.getElementById('mTech2').textContent = 'Match';
  document.getElementById('mTime2').textContent = elapsed;

  // Handle Shot Map / Video Toggling
  const vid = document.getElementById('resultVideo');
  const mapImg = document.getElementById('shotMapImage');
  const mapBtn = document.getElementById('btnShowMap');
  const vidBtn = document.getElementById('btnShowVideo');

  if (data.shot_map_url) {
    mapImg.src = data.shot_map_url;
    document.getElementById('btnShowMap').style.display = 'inline-block';
    document.getElementById('btnShowVideo').style.display = 'inline-block';
    setView('map'); // Default to map for match results
  } else {
    vid.style.display = 'block';
    document.getElementById('shotMapContainer').style.display = 'none';
    document.getElementById('btnShowMap').style.display = 'none';
    document.getElementById('btnShowVideo').style.display = 'none';
  }

  const col = document.getElementById('coachingCol');
  col.innerHTML = '';

  // Per-player cards
  const players = data.players || {};
  if (Object.keys(players).length === 0) {
    const empty = el('div', 'headline-card');
    empty.textContent = 'No players with enough technique data found. Try a longer video with more action.';
    col.appendChild(empty);
    return;
  }

  Object.entries(players).forEach(([pid, pdata]) => {
    const card = el('div', 'fix-card');
    const segs = pdata.segments || [];
    const techniques = pdata.techniques_detected || [];
    card.innerHTML = `
      <div class="fix-header">
        <div class="fix-num">${pid}</div>
        <div class="fix-title">Player ${pid} — ${techniques.join(', ') || 'No techniques'}</div>
      </div>`;
    segs.slice(0, 2).forEach(seg => {
      if (seg.analysis) {
        const coaching = seg.analysis.coaching || {};
        card.innerHTML += `
          <div style="margin-top:10px">
            <div class="fix-drill-label">${seg.technique.toUpperCase()} · ${seg.analysis.verdict}</div>
            ${coaching.headline ? `<div class="fix-drill-name">${coaching.headline}</div>` : ''}
            ${(coaching.fixes||[]).slice(0,1).map(f => `
              <div class="fix-feel"><div class="fix-feel-label">FEEL</div><p>${f.feel_cue||''}</p></div>
            `).join('')}
          </div>`;
      }
    });
    col.appendChild(card);
  });

  // Technique counts
  if (summary.technique_counts && Object.keys(summary.technique_counts).length) {
    const tc = el('div', 'metrics-card');
    tc.innerHTML = '<div class="card-title">Techniques detected</div>';
    Object.entries(summary.technique_counts).forEach(([tech, count]) => {
      const row = el('div', 'metric-item');
      row.innerHTML = `<div class="metric-dot dot-good"></div><div class="metric-name">${tech}</div><span class="metric-tag tag-good">${count}x</span>`;
      tc.appendChild(row);
    });
    col.appendChild(tc);
  }
}


// ── Helpers ───────────────────────────────────────────────────────────────────
function el(tag, cls) {
  const e = document.createElement(tag);
  e.className = cls;
  return e;
}

function cap(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : ''; }

// Animate number count-up
function animateValue(el, start, end, duration) {
  if (!el) return;
  const range = end - start;
  const startTime = performance.now();
  
  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    // Easing function: ease-out cubic
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = Math.round(start + range * eased);
    el.textContent = current;
    
    if (progress < 1) {
      requestAnimationFrame(update);
    }
  }
  
  requestAnimationFrame(update);
}

function showError(msg) {
  showSection('upload');
  document.getElementById('errorBox').classList.add('show');
  document.getElementById('errorMsg').textContent = msg;
}

function showSection(name) {
  document.getElementById('uploadSection').style.display   = name === 'upload'   ? '' : 'none';
  document.getElementById('progressSection').className     = name === 'progress' ? 'show' : '';
  document.getElementById('resultsSection').className      = name === 'results'  ? 'show' : '';
}

function resetAll() {
  resetUpload();
  showSection('upload');
  document.getElementById('resultVideo').src = '';
  document.getElementById('coachingCol').innerHTML = '';
  document.querySelectorAll('.steps li').forEach((li, i) => {
    li.className = i === 0 ? 'active' : '';
    li.querySelector('.step-icon').textContent = i + 1;
  });
}
