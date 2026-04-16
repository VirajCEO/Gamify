// ══ THEME INIT ══════════════════════════════════════════════════════════════
const L_THEME = localStorage.getItem('theme');
if (L_THEME === 'light') document.documentElement.setAttribute('data-theme','light');

function toggleTheme(isLight){
  if(isLight){
    document.documentElement.setAttribute('data-theme','light');
    localStorage.setItem('theme','light');
  }else{
    document.documentElement.removeAttribute('data-theme');
    localStorage.setItem('theme','dark');
  }
}

// ══ AUDIO ═══════════════════════════════════════════════════════════════════
const AC=window.AudioContext||window.webkitAudioContext; let ac;
const ea=()=>{if(!ac)ac=new AC()};
const tone=(freqs,type='sine',vol=.12,dur=.3,gap=.08)=>{ea();const n=ac.currentTime;freqs.forEach((f,i)=>{const o=ac.createOscillator(),g=ac.createGain();o.type=type;o.frequency.value=f;g.gain.setValueAtTime(vol,n+i*gap);g.gain.exponentialRampToValueAtTime(.001,n+i*gap+dur);o.connect(g);g.connect(ac.destination);o.start(n+i*gap);o.stop(n+i*gap+dur)})};
const sndComplete=()=>tone([523,659,784,1047],'sine',.12,.28,.07);
const sndLevelUp=()=>tone([262,330,392,523,659,784],'triangle',.18,.45,.11);
const sndStatUp=()=>tone([392,523,659],'triangle',.1,.3,.1);
const sndAch=()=>tone([440,554,659],'triangle',.11,.35,.13);
const sndMegaComplete=()=>{tone([523,659,784,1047,1319,1568],'sine',.14,.32,.06);setTimeout(()=>tone([784,1047,1568],'triangle',.1,.4,.08),120)};
const sndFail=()=>tone([220,165,110],'sawtooth',.15,.45,.12);
const sndPenalty=()=>{ea();const n=ac.currentTime;[{f:180,t:'sawtooth',d:.6,v:.22},{f:90,t:'sawtooth',d:.8,v:.18},{f:60,t:'square',d:1.0,v:.12}].forEach(x=>{const o=ac.createOscillator(),g=ac.createGain();o.type=x.t;o.frequency.setValueAtTime(x.f,n);o.frequency.exponentialRampToValueAtTime(x.f*.4,n+x.d);g.gain.setValueAtTime(x.v,n);g.gain.exponentialRampToValueAtTime(.001,n+x.d);o.connect(g);g.connect(ac.destination);o.start(n);o.stop(n+x.d)})};
const sndStreakBreak=()=>{ea();const n=ac.currentTime;[0,.08,.16].forEach((dly,i)=>{const o=ac.createOscillator(),g=ac.createGain();o.type='triangle';o.frequency.setValueAtTime(660-i*220,n+dly);o.frequency.exponentialRampToValueAtTime(80,n+dly+.4);g.gain.setValueAtTime(.18,n+dly);g.gain.exponentialRampToValueAtTime(.001,n+dly+.4);o.connect(g);g.connect(ac.destination);o.start(n+dly);o.stop(n+dly+.4)})};
const sndHpHit=()=>tone([140,100,70],'square',.16,.18,.05);
const sndTick=()=>tone([880],'sine',.05,.08,0);
const sndCoin=()=>tone([1760,2093],'square',.07,.09,.04);
const sndSwoosh=()=>{ea();const n=ac.currentTime;const o=ac.createOscillator(),g=ac.createGain(),f=ac.createBiquadFilter();o.type='sawtooth';o.frequency.setValueAtTime(1200,n);o.frequency.exponentialRampToValueAtTime(200,n+.25);f.type='lowpass';f.frequency.value=1500;g.gain.setValueAtTime(.08,n);g.gain.exponentialRampToValueAtTime(.001,n+.25);o.connect(f);f.connect(g);g.connect(ac.destination);o.start(n);o.stop(n+.25)};
const sndChallenge=()=>{tone([659,784,988,1319],'triangle',.14,.32,.08);setTimeout(()=>tone([988,1319,1760],'sine',.1,.3,.09),200)};
const sndChime=()=>tone([1047,1319,1568,2093],'sine',.08,.3,.06);

// ══ CONFETTI ═════════════════════════════════════════════════════════════════
const COLS=['#9b8fff','#ff7070','#fbbf24','#4ade80','#f4b942','#7C6FFF','#ff85a1'];
const confetti=(n=22)=>{for(let i=0;i<n;i++){const e=document.createElement('div');e.className='cfetti';e.style.cssText=`left:${Math.random()*100}vw;top:-10px;background:${COLS[~~(Math.random()*COLS.length)]};border-radius:${Math.random()>.5?'50%':'3px'};width:${5+Math.random()*7}px;height:${5+Math.random()*7}px;animation-duration:${1+Math.random()*1.5}s;animation-delay:${Math.random()*.3}s`;document.body.appendChild(e);setTimeout(()=>e.remove(),3000)}};

// ══ TOASTS ════════════════════════════════════════════════════════════════════
const toast=(title,body,dur=3000)=>{const e=document.createElement('div');e.className='toast';e.innerHTML=`<div class="tt">${title}</div><div class="tb">${esc(body)}</div>`;document.body.appendChild(e);setTimeout(()=>{e.style.opacity='0';e.style.transition='opacity .3s';setTimeout(()=>e.remove(),300)},dur)};
const showXP=(xp,stat)=>{const C={INT:'var(--int)',DEX:'var(--dex)',CHA:'var(--cha)',VIT:'var(--vit)'};const e=document.createElement('div');e.className='xppop';e.innerHTML=`<div class="xa">+${xp} XP</div><div class="xs" style="color:${C[stat]||'var(--text)'}">${stat}</div>`;document.body.appendChild(e);setTimeout(()=>e.remove(),1300)};
const showLvl=(lv, newTitle, newUnlocks)=>{
  const t = newTitle||{};
  const tLine = t.name ? `<div style="font-size:1rem;color:var(--gold);font-weight:700;margin-top:6px">${t.icon||''} ${t.name}</div>` : '';
  const uLines = (newUnlocks||[]).map(u=>`<div style="font-size:.82rem;color:var(--accent);font-weight:600;margin-top:4px">\u2728 Unlocked: ${u.label}</div>`).join('');
  const e=document.createElement('div');e.className='lvl-overlay';
  e.innerHTML=`<div class="lvl-box"><div class="lt">LEVEL UP!</div><div class="ln">${lv}</div>${tLine}${uLines}<div class="ls" style="margin-top:8px">${newUnlocks?.length?'':'New powers unlocked'}</div></div>`;
  e.onclick=()=>e.remove();document.body.appendChild(e);sndLevelUp();confetti(55);starShower(25);
  setTimeout(()=>e.remove(),4200);
};
const showUnlock=(unlock)=>{
  const e=document.createElement('div');e.className='unlock-pop';
  e.innerHTML=`<div class="upt">New Unlock</div><div class="upico">\u2728</div><div class="uplbl">${esc(unlock.label)}</div><div class="updesc">${esc(unlock.desc)}</div>`;
  document.body.appendChild(e);sndChallenge();confetti(20);
  setTimeout(()=>e.remove(),2800);
};

const screenFlash=(bad=false)=>{const f=document.createElement('div');f.className=bad?'screen-flash-bad':'screen-flash-good';document.body.appendChild(f);setTimeout(()=>f.remove(),600)};
const screenShake=()=>{document.body.classList.add('screen-shake');setTimeout(()=>document.body.classList.remove('screen-shake'),550)};
const hpHit=()=>{const b=document.getElementById('hp-bar');if(b){b.parentElement.classList.add('hp-hit');setTimeout(()=>b.parentElement.classList.remove('hp-hit'),650)}};
const sparks=(x,y,color='var(--gold)',n=14)=>{for(let i=0;i<n;i++){const s=document.createElement('div');s.className='spark';const a=(Math.PI*2*i)/n+Math.random()*.4;const d=60+Math.random()*80;s.style.cssText=`left:${x}px;top:${y}px;color:${COLS[~~(Math.random()*COLS.length)]};--dx:${Math.cos(a)*d}px;--dy:${Math.sin(a)*d}px`;document.body.appendChild(s);setTimeout(()=>s.remove(),950)}};
const comboRing=()=>{const r=document.createElement('div');r.className='combo-ring';document.body.appendChild(r);setTimeout(()=>r.remove(),820)};
const streakBreakFx=(lost)=>{const e=document.createElement('div');e.className='streak-break';e.innerHTML=`&#128165; STREAK BROKEN &#128165;<div style="font-size:1.2rem;margin-top:10px;color:#ffaaaa">${lost} days lost</div>`;document.body.appendChild(e);setTimeout(()=>e.remove(),1800)};
const coinRain=(x,y,n=10)=>{for(let i=0;i<n;i++){const c=document.createElement('div');c.className='coin';const dx=(Math.random()-.5)*220;const dy=90+Math.random()*160;c.style.cssText=`left:${x}px;top:${y}px;--cx:${dx}px;--cy:${dy}px;animation-delay:${i*40}ms`;document.body.appendChild(c);setTimeout(()=>c.remove(),1400+i*40)}sndCoin()};
const starShower=(n=20)=>{const emojis=['\u2728','\u2B50','\ud83c\udf1f'];for(let i=0;i<n;i++){const s=document.createElement('div');s.className='star';s.textContent=emojis[i%emojis.length];s.style.cssText=`left:${Math.random()*100}vw;animation-delay:${Math.random()*.8}s;font-size:${14+Math.random()*14}px`;document.body.appendChild(s);setTimeout(()=>s.remove(),3000)}};
const showChallengeDone=(ch)=>{const e=document.createElement('div');e.className='chal-pop';e.innerHTML=`<div class="cpi">${ch.icon||'\ud83c\udfaf'}</div><div class="cpt">Challenge Complete</div><div class="cpd">${esc(ch.description)}</div><div class="cpr">+${ch.reward_xp} XP</div>`;document.body.appendChild(e);sndChallenge();confetti(30);starShower(14);setTimeout(()=>e.remove(),2300)};

// ══ ANIMATED COUNTER ═════════════════════════════════════════════════
const animateNum=(el,from,to,dur=700)=>{
  if(!el)return;from=Number(from)||0;to=Number(to)||0;
  const start=performance.now();
  const tick=(now)=>{
    const t=Math.min(1,(now-start)/dur);
    const e=1-Math.pow(1-t,3);
    const v=Math.round(from+(to-from)*e);
    el.textContent=v;
    if(t<1)requestAnimationFrame(tick);
    else{el.classList.add('tick');setTimeout(()=>el.classList.remove('tick'),260)}
  };
  requestAnimationFrame(tick);
};
const bumpBar=(id)=>{const b=document.getElementById(id);if(b){b.classList.remove('bar-bump');void b.offsetWidth;b.classList.add('bar-bump')}};

// ══ COMBO ═════════════════════════════════════════════════════════════
let comboN=0,comboTO=null;
const bumpCombo=()=>{
  comboN++;
  if(comboTO)clearTimeout(comboTO);
  if(comboN>=2){
    document.querySelectorAll('.combo-badge').forEach(x=>x.remove());
    const e=document.createElement('div');e.className='combo-badge'+(comboN>=5?' mega':'');
    const label=comboN>=10?'UNSTOPPABLE':comboN>=5?'ON FIRE':comboN>=3?'COMBO':'STREAK';
    e.innerHTML=`<span class="cx">${comboN}x</span><span>${label}</span>`;
    document.body.appendChild(e);
    const baseFreq=440+comboN*50;
    tone([baseFreq,baseFreq*1.25,baseFreq*1.5],'triangle',.11,.22,.05);
    setTimeout(()=>{e.style.transition='opacity .4s,transform .4s';e.style.opacity='0';e.style.transform='translateX(-50%) translateY(-20px) scale(.8)';setTimeout(()=>e.remove(),400)},1400);
  }
  comboTO=setTimeout(()=>{comboN=0},6000);
};

// ══ PERFECT DAY ═══════════════════════════════════════════════════════
const showPerfectDay=()=>{
  const today=new Date().toISOString().slice(0,10);
  if(localStorage.getItem('pd_shown')===today)return;
  localStorage.setItem('pd_shown',today);
  const e=document.createElement('div');e.className='pd-overlay';
  e.innerHTML=`<div class="pd-rays"></div><div class="pd-box">
    <div class="pdt">&#11088; Perfect Day &#11088;</div>
    <div class="pdn">ALL CLEAR</div>
    <div class="pds">Every quest conquered.<br/>Streak secured. Grind validated.</div>
    <div class="pdhint">Tap to continue</div>
  </div>`;
  e.onclick=()=>e.remove();document.body.appendChild(e);
  sndLevelUp();setTimeout(()=>sndAch(),400);
  confetti(120);
  let bursts=0;const iv=setInterval(()=>{confetti(40);bursts++;if(bursts>=4)clearInterval(iv)},500);
};

// ══ RIPPLE EFFECT ═════════════════════════════════════════════════════
document.addEventListener('click',(ev)=>{
  const t=ev.target.closest('.qcheck,.btn,.btab');
  if(!t||t.classList.contains('locked'))return;
  const r=t.getBoundingClientRect();
  const rip=document.createElement('span');rip.className='ripple';
  const size=Math.max(r.width,r.height);
  rip.style.cssText=`width:${size}px;height:${size}px;left:${ev.clientX-r.left-size/2}px;top:${ev.clientY-r.top-size/2}px`;
  const oldPos=getComputedStyle(t).position;
  if(oldPos==='static')t.style.position='relative';
  t.style.overflow='hidden';
  t.appendChild(rip);setTimeout(()=>rip.remove(),620);
},true);

const showPenalty=(p)=>{
  if(!p)return;
  sndPenalty();screenShake();hpHit();
  const e=document.createElement('div');e.className='pen-overlay';
  const streakRow=p.streak_lost>0?`<div class="pstat"><span class="pv">-${p.streak_lost}</span><span class="pl">STREAK LOST</span></div>`:'';
  e.innerHTML=`<div class="pen-cracks"></div><div class="pen-box">
    <div class="pt">&#9888; QUEST FAILED &#9888;</div>
    <div class="pn">-${p.hp_lost} HP</div>
    <div class="pd">You missed <b>${p.missed}</b> quest${p.missed>1?'s':''} from yesterday.<br/>The Game Master is not pleased.</div>
    <div>${streakRow}<div class="pstat"><span class="pv">${p.missed}</span><span class="pl">QUESTS FAILED</span></div></div>
    <div class="phint">Click to dismiss &middot; Redeem yourself today</div>
  </div>`;
  e.onclick=()=>e.remove();document.body.appendChild(e);
  if(p.streak_lost>0)setTimeout(()=>{sndStreakBreak();streakBreakFx(p.streak_lost)},600);
  setTimeout(()=>sndHpHit(),1200);
};

// ══ STATE ═════════════════════════════════════════════════════════════════════
let S={user:null,daily:[],tomorrow:[],weekly:[],monthly:[],ach:[],chal:[],canWk:false,canMo:false};
let selPersona='',sPersona='',activeTab='daily',taskTimers={};
const esc=s=>{const d=document.createElement('div');d.textContent=s||'';return d.innerHTML};
const PROFILE = (()=>{
  const path = location.pathname.replace(/^\//,'').split('/')[0]||'';
  return path.replace(/[^a-z0-9_]/gi,'').slice(0,32);
})();

const withProfile=(url)=>{
  if(!PROFILE)return url;
  const sep=url.includes('?')?'&':'?';
  return `${url}${sep}profile=${encodeURIComponent(PROFILE)}`;
};
let api=async(url,o={})=>{
  const r=await fetch(withProfile(url),{
    headers:{'Content-Type':'application/json'},
    ...o
  });
  return r.json();
};
const pad=n=>String(n).padStart(2,'0');

// ══ COUNTDOWNS ══════════════════════════════════════════════════════════════
let lastDate = new Date().toDateString();
const updateClocks=()=>{
  const now=new Date();
  // Daily: to 23:59:59
  const mid=new Date(now);mid.setHours(23,59,59,999);
  const ds=Math.max(0,Math.floor((mid-now)/1000));
  const dClk=document.getElementById('daily-clock');
  if(dClk){
    dClk.textContent=`${pad(~~(ds/3600))}:${pad(~~(ds%3600/60))}:${pad(ds%60)}`;
    dClk.className='timer-clock'+(ds<3600?' urgent':'');
  }
  // Weekly: to end of Sunday
  const dayOfWeek=now.getDay();// 0=Sun
  const daysToSun=dayOfWeek===0?0:(7-dayOfWeek);
  const sun=new Date(now);sun.setDate(now.getDate()+daysToSun);sun.setHours(23,59,59,999);
  const ws=Math.max(0,Math.floor((sun-now)/1000));
  const wd=~~(ws/86400),wh=~~(ws%86400/3600),wm=~~(ws%3600/60),wsc=ws%60;
  const wClk=document.getElementById('weekly-clock');
  if(wClk) wClk.textContent=wd>0?`${wd}d ${pad(wh)}:${pad(wm)}`:`${pad(wh)}:${pad(wm)}:${pad(wsc)}`;
  // Detect date change → reload
  const nd=now.toDateString();
  if(nd!==lastDate){lastDate=nd;loadAll();}
};
setInterval(updateClocks,1000);updateClocks();

// ══ TASK TIMERS ══════════════════════════════════════════════════════════════
const toggleTaskTimer=(id,mins)=>{
  if(taskTimers[id]){clearInterval(taskTimers[id].iv);const el=document.getElementById(`tmr-${id}`);if(el){el.classList.remove('run');el.textContent=`${taskTimers[id].rem}s`}delete taskTimers[id];return}
  let rem=mins*60;
  const el=document.getElementById(`tmr-${id}`);
  if(el){el.classList.add('run')}
  taskTimers[id]={rem,iv:setInterval(()=>{
    rem--;taskTimers[id].rem=rem;
    const e2=document.getElementById(`tmr-${id}`);
    if(e2)e2.textContent=`${pad(~~(rem/60))}:${pad(rem%60)}`;
    if(rem<=0){clearInterval(taskTimers[id].iv);delete taskTimers[id];const e2=document.getElementById(`tmr-${id}`);if(e2){e2.classList.remove('run');e2.textContent='Done!'}sndComplete();toast('Timer Done!',`Quest time's up!`)}
  },1000)};
  if(el)el.textContent=`${pad(~~(rem/60))}:${pad(rem%60)}`;
};

// ══ INIT ══════════════════════════════════════════════════════════════════════
function hideSplash(){const s=document.getElementById('app-splash');if(s){s.classList.add('hide');setTimeout(()=>s.remove(),500)}}
function setSplashNote(t){const n=document.getElementById('splash-note');if(n)n.textContent=t}
async function checkIdentity(){
  const saved = localStorage.getItem('gamify_slug');
  const path = location.pathname;
  
  if(path === "/"){
    if(saved === null){
      renderAuthScreen();
      return false;
    }
    if(saved !== ""){
      location.href = `/${saved}`;
      return false;
    }
    // if saved is "", we stay at root. return true to continue init
    return true;
  }
  
  if(PROFILE){
    localStorage.setItem('gamify_slug', PROFILE);
  }
  return true;
}

async function renderAuthScreen(){
  hideSplash();
  const screen = document.getElementById('auth-screen');
  screen.style.display = 'flex';
  
  try {
    const profiles = await fetch('/api/auth/profiles').then(r=>r.json());
    const list = document.getElementById('auth-profile-list');
    list.innerHTML = profiles.map(p => `
      <div class="auth-card" onclick="login('${p.slug}')">
        <div class="ac-photo">
          ${p.profile_photo ? `<img src="${p.profile_photo}">` : `<span>${(p.username||'?')[0].toUpperCase()}</span>`}
        </div>
        <div class="ac-name">${esc(p.username)}</div>
        <div class="ac-meta">
          ${p.level ? `<span class="ac-lv">Lv.${p.level}</span> ${esc(p.title||'')}` : '<span class="ac-lv">New Adventure</span>'}
        </div>
      </div>
    `).join('') || '<div class="auth-loading">No explorers found yet. Start the first journey!</div>';
  } catch(e) {
    console.error(e);
  }
}

async function login(slug){
  localStorage.setItem('gamify_slug', slug);
  location.href = slug === "" ? "/" : `/${slug}`;
}

async function loginNew(){
  const name = document.getElementById('auth-new-name').value.trim();
  if(!name) return toast('Wait!', 'Please enter a name for your journey');
  
  try {
    const r = await fetch('/api/auth/login', {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({username: name})
    }).then(r=>r.json());
    
    if(r.error) return toast('Error', r.error);
    login(r.slug);
  } catch(e) {
    toast('Error', 'Could not connect to server');
  }
}

function switchAccount(){
  localStorage.removeItem('gamify_slug');
  location.href = "/";
}

async function init(){
  try{
    setSplashNote('Identifying runner...');
    const ok = await checkIdentity();
    if(!ok) return;

    setSplashNote('Connecting...');
    S.user=await api('/api/user');
    if(!S.user.onboarded){
      document.getElementById('onboarding').style.display='flex';
      buildPersonaGrid('persona-grid');
      hideSplash();
    }else{
      setSplashNote('Loading your adventure...');
      document.getElementById('onboarding').style.display='none';
      document.getElementById('main-app').style.display='grid';
      await loadAll();
      hideSplash();
    }
  }catch(e){
    console.error('init failed',e);
    setSplashNote('Something went wrong. Retrying...');
    setTimeout(()=>location.reload(),2200);
  }
}

function buildPersonaGrid(gridId){
  const g=document.getElementById(gridId);g.innerHTML='';
  Object.entries(S.user.personas||{}).forEach(([k,p])=>{
    const c=document.createElement('div');c.className='persona-card';
    c.innerHTML=`<div class="p-icon">${p.icon}</div><div class="p-name">${p.name}</div><div class="p-desc">${p.desc}</div>`;
    c.onclick=()=>{g.querySelectorAll('.persona-card').forEach(x=>x.classList.remove('selected'));c.classList.add('selected');
      if(gridId==='persona-grid'){selPersona=k;document.getElementById('btn-nxt-persona').disabled=false}
      else{sPersona=k;document.querySelectorAll('.popt').forEach(x=>x.classList.remove('active'));c.classList.add('active')}};
    g.appendChild(c);
  });
}

const STEPS=['step-about','step-persona','step-goals'];
function toStep(i){
  STEPS.forEach((s,j)=>{
    document.getElementById(s).classList.toggle('active',j===i);
    document.getElementById(`dot${j}`)?.classList.toggle('active',j===i);
  });
}

async function completeOnboard(){
  await api('/api/onboard',{method:'POST',body:JSON.stringify({
    persona:selPersona,
    display_name:document.getElementById('onb-name').value.trim(),
    profession:document.getElementById('onb-profession').value.trim(),
    bio:document.getElementById('onb-bio').value.trim(),
    motivation:document.getElementById('onb-motivation').value.trim(),
    monthly_goal:document.getElementById('onb-monthly').value.trim(),
    weekly_goal:document.getElementById('onb-weekly').value.trim(),
  })});
  document.getElementById('onboarding').style.display='none';
  document.getElementById('main-app').style.display='grid';
  S.user=await api('/api/user');await loadAll();
}

async function loadAll(){
  const[u,t,a,ch,ms,bn,pt]=await Promise.all([
    api('/api/user'),api('/api/tasks'),api('/api/achievements'),
    api('/api/challenges'),api('/api/milestones'),api('/api/bounties'),api('/api/pet')
  ]);
  S.user=u;S.daily=t.daily||[];S.tomorrow=t.tomorrow||[];S.weekly=t.weekly||[];S.monthly=t.monthly||[];
  S.canWk=t.can_tick_weekly;S.canMo=t.can_tick_monthly;S.ach=a.achievements||[];S.chal=ch.challenges||[];
  S.bounties=bn.bounties||[];S.pet=pt.pet||null;S.petSpecies=pt.species||[];
  renderAll();
  rMilestones(ms.milestones||[]);
  rBounties();
  rPet();
  rTodayStats();
  checkDailyGift();
  if(u.penalty){setTimeout(()=>showPenalty(u.penalty),400)}
  else{setTimeout(()=>tryLoginReward(),800)}
}

// ══ RENDER ════════════════════════════════════════════════════════════════════
const STAT_C={INT:'var(--int)',DEX:'var(--dex)',CHA:'var(--cha)',VIT:'var(--vit)'};
const STAT_GLOW={INT:'var(--int-glow)',DEX:'var(--dex-glow)',CHA:'var(--cha-glow)',VIT:'var(--vit-glow)'};
const STAT_DESC={
  INT:'<b>Intelligence</b><br>Coding, research, analysis & deep thinking. Tasks that challenge and expand your mind.',
  DEX:'<b>Dexterity</b><br>Building, hands-on work & precision skills. Tasks that require physical execution.',
  CHA:'<b>Charisma</b><br>Communication, networking & social skills. Tasks that connect you to others.',
  VIT:'<b>Vitality</b><br>Exercise, sleep, nutrition & recovery. Restores Energy and builds physical resilience.',
};

function renderAll(){rProfile();rBars();rStats();rGoals();rDaily();rTomorrow();rWeekly();rMonthly();rAch();rChal();rCounts()}

function rChal(){
  const el=document.getElementById('chal-list');if(!el)return;
  const list=S.chal||[];
  if(!list.length){el.innerHTML=`<div class="empty" style="padding:16px;font-size:.8rem">No challenges yet.</div>`;return}
  el.innerHTML=list.map(c=>{
    const pct=Math.min(100,Math.round((c.progress/c.target_value)*100));
    const done=c.completed?'chal-done':'';
    return `<div class="chal-item ${done}" data-chid="${c.id}">
      <div class="chtop"><div class="chic">${c.icon||'\ud83c\udfaf'}</div><div class="chdesc">${esc(c.description)}</div><div class="chrew">+${c.reward_xp} XP</div></div>
      <div class="chbar"><div class="chfill" style="width:${pct}%"></div></div>
      <div class="chmeta"><span>${c.progress} / ${c.target_value}</span><span>${pct}%</span></div>
    </div>`;
  }).join('');
}

function rProfile(){
  const u=S.user;if(!u)return;
  const name=u.display_name||'Hero';
  document.getElementById('pname').textContent=name;
  document.getElementById('lv-pill').textContent='Lv.'+u.level;
  const p=(u.personas||{})[u.persona];
  document.getElementById('ptag').textContent=p?`${p.icon} ${p.name}`:'';
  // Title
  const ptEl=document.getElementById('ptitle');
  if(u.title)ptEl.innerHTML=`${u.title_icon||''} ${u.title}`;
  // Next unlock
  const nub=document.getElementById('next-unlock-bar');
  if(u.next_unlock){nub.style.display='flex';nub.innerHTML=`<span class="nulv">Lv.${u.next_unlock.level}</span><span class="nulbl">${u.next_unlock.label}</span><span style="color:var(--text3)">${u.next_unlock.desc}</span>`}
  else{nub.style.display='none'}
  // Avatar border for prestige
  const av=document.getElementById('avatar');
  if(u.level>=50)av.style.boxShadow='0 0 20px rgba(139,92,246,.6),0 0 40px rgba(139,92,246,.3)';
  else if(u.level>=40)av.style.boxShadow='0 0 14px rgba(245,158,11,.5)';
  else av.style.boxShadow='';
  if(u.profile_photo){av.innerHTML=`<img src="/static/uploads/${esc(u.profile_photo)}">`}
  else{av.innerHTML=`<span class="initials">${(name.split(' ').map(w=>w[0]).join('').toUpperCase().slice(0,2)||'?')}</span>`}
  // Gem count
  const gc=document.getElementById('gems-count');
  if(gc){const prev=Number(gc.textContent||0);const nxt=u.gems||0;if(prev!==nxt){animateNum(gc,prev,nxt);const pill=document.getElementById('gems-pill');if(pill && nxt>prev){pill.classList.remove('bump');void pill.offsetWidth;pill.classList.add('bump')}}else{gc.textContent=nxt}}
}

let _prevXP=null,_prevHP=null,_prevLv=null;
function rBars(){
  const u=S.user;if(!u)return;
  const xpN=u.xp_for_next||100,prev=u.level>1?Math.floor(100*Math.pow(u.level-1,1.5)):0;
  const xpP=Math.min(100,Math.max(0,((u.total_xp-prev)/(xpN-prev))*100));
  const xpBar=document.getElementById('xp-bar');
  xpBar.style.width=xpP+'%';
  const xpTxt=document.getElementById('xp-txt');
  xpTxt.innerHTML=`<span class="count-up" id="xp-num">${_prevXP??u.total_xp}</span> / ${xpN}`;
  if(_prevXP!==null && _prevXP!==u.total_xp){animateNum(document.getElementById('xp-num'),_prevXP,u.total_xp);bumpBar('xp-bar')}
  _prevXP=u.total_xp;

  const hP=u.max_hp?Math.round(u.hp/u.max_hp*100):100;
  const hb=document.getElementById('hp-bar');
  hb.style.width=hP+'%';
  hb.style.background=hP<25?'linear-gradient(90deg,var(--danger),#fca5a5)':hP<50?'linear-gradient(90deg,var(--gold),#fde68a)':'linear-gradient(90deg,var(--vit),#6ee7b7)';
  hb.style.boxShadow=hP<25?'0 0 14px rgba(255,85,85,.5)':hP<50?'0 0 12px rgba(244,185,66,.35)':'0 0 12px rgba(74,222,128,.35)';
  const hpTxt=document.getElementById('hp-txt');
  hpTxt.innerHTML=`<span class="count-up" id="hp-num">${_prevHP??u.hp}</span> / ${u.max_hp}`;
  if(_prevHP!==null && _prevHP!==u.hp)animateNum(document.getElementById('hp-num'),_prevHP,u.hp);
  _prevHP=u.hp;

  // Level pill bump on level-up
  const lvPill=document.getElementById('lv-pill');
  if(_prevLv!==null && _prevLv!==u.level){lvPill.classList.remove('bump');void lvPill.offsetWidth;lvPill.classList.add('bump')}
  _prevLv=u.level;

  const sw=document.getElementById('streak-wrap');
  if(u.streak>0){
    const atRisk=u.last_active && u.last_active!==new Date().toISOString().slice(0,10);
    sw.innerHTML=`<div class="streak-badge${atRisk?' atrisk':''}"><span class="flame">&#128293;</span><span class="sn">${u.streak}</span><span>Day Streak</span></div>`;
  } else sw.innerHTML='';

  // Daily progress ring
  const dDone=S.daily.filter(t=>t.status==='done').length;
  const dTot=S.daily.length;
  const wrap=document.getElementById('daily-ring-wrap');
  if(dTot>0){
    wrap.style.display='flex';
    const pct=dDone/dTot;
    const circ=2*Math.PI*21;
    const off=circ*(1-pct);
    document.getElementById('daily-ring-fg').setAttribute('stroke-dashoffset',off);
    document.getElementById('daily-ring-txt').textContent=`${dDone}/${dTot}`;
    const sub=document.getElementById('daily-ring-sub');
    wrap.classList.toggle('complete',dDone===dTot);
    sub.textContent=dDone===0?'Begin your quests':dDone===dTot?'Perfect day! 🎉':`${dTot-dDone} to conquer`;
  } else wrap.style.display='none';
}

function rStats(){
  const u=S.user;if(!u)return;
  document.getElementById('stats-list').innerHTML=['int','dex','cha','vit'].map(s=>{
    const S2=s.toUpperCase(),xp=u[s+'_xp']||0,cur=u[s+'_xp_current']||0,need=u[s+'_xp_needed']||1,lv=u[s+'_level']||1;
    const pct=Math.min(100,cur/need*100);
    return `<div class="stat-row">
      <div class="stat-top">
        <div class="stat-name-wrap">
          <span class="stat-name" style="color:${STAT_C[S2]}">${S2}</span>
          <span class="stat-lvl" style="background:${STAT_C[S2]}">Lv.${lv}</span>
          <div class="stat-tooltip">${STAT_DESC[S2]}</div>
        </div>
        <span class="stat-xp-val">${xp} XP &bull; ${cur}/${need}</span>
      </div>
      <div class="stat-bar"><div class="stat-fill" style="width:${pct}%;background:${STAT_C[S2]};box-shadow:0 0 8px ${STAT_GLOW[S2]}"></div></div>
    </div>`;
  }).join('');
}

function rGoals(){}

function rQI(t,canTick){
  const done=t.status==='done';
  const failed=t.status==='failed';
  const tmrState=taskTimers[t.id];
  const tmrTxt=tmrState?`${pad(~~(tmrState.rem/60))}:${pad(tmrState.rem%60)}` :`${t.timer_minutes||30}m`;
  const enDrain=t.energy_cost<0;
  return `<div class="qi ${done?'done':''} ${failed?'failed':''}" data-id="${t.id}">
    <div class="qcheck ${!canTick&&!done&&!failed?'locked':''}" ${canTick&&!done&&!failed?`onclick="completeTask(${t.id})"`:''}>${failed?'&#10007;':''}</div>
    <div class="qbody">
      <div class="qd">${esc(t.description)}</div>
      <div class="qmeta">
        <span class="qstat" style="background:${STAT_C[t.stat]};box-shadow:0 0 6px ${STAT_GLOW[t.stat]}">${t.stat}</span>
        <span class="qxp" style="color:var(--gold)">+${t.xp_value} XP</span>
        <span class="qen ${enDrain?'r':'d'}">${enDrain?'+':'−'}${Math.abs(t.energy_cost)} EN</span>
        ${!done?`<span class="qtmr ${tmrState?'run':''}" id="tmr-${t.id}" onclick="event.stopPropagation();toggleTaskTimer(${t.id},${t.timer_minutes||30})">&#9201; ${tmrTxt}</span>`:''}
      </div>
    </div>
  </div>`;
}

function rDaily(){
  const el=document.getElementById('qs-daily');
  if(!S.daily.length){el.innerHTML=`<div class="empty"><div class="eico">&#9876;&#65039;</div><p>No quests yet.<br>Generate or quick add!</p></div>`;return}
  const sorted=[...S.daily].sort((a,b)=>a.status==='pending'&&b.status==='done'?-1:1);
  el.innerHTML=`<div class="quest-list">${sorted.map(t=>rQI(t,true)).join('')}</div>`;
}

function rWeekly(){
  const el=document.getElementById('qs-weekly'),lock=document.getElementById('wk-lock');
  lock.innerHTML=S.canWk?'':`<div class="lock-notice">&#128274; Unlocks Saturday & Sunday</div>`;
  if(!S.weekly.length){el.innerHTML=`<div class="empty"><div class="eico">&#128203;</div><p>No weekly goals yet.<br>Generate or add your own!</p></div>`;return}
  const sorted=[...S.weekly].sort((a,b)=>a.status==='pending'&&b.status==='done'?-1:1);
  el.innerHTML=`<div class="quest-list">${sorted.map(t=>rQI(t,S.canWk)).join('')}</div>`;
}

function rMonthly(){
  const el=document.getElementById('qs-monthly'),lock=document.getElementById('mo-lock');
  lock.innerHTML=S.canMo?'':`<div class="lock-notice">&#128274; Unlocks last 2 days of the month</div>`;
  if(!S.monthly.length){el.innerHTML=`<div class="empty"><div class="eico">&#127775;</div><p>No monthly milestones.<br>Generate or add one!</p></div>`;return}
  const sorted=[...S.monthly].sort((a,b)=>a.status==='pending'&&b.status==='done'?-1:1);
  el.innerHTML=`<div class="quest-list">${sorted.map(t=>rQI(t,S.canMo)).join('')}</div>`;
}

function rTomorrow(){
  const el=document.getElementById('qs-tomorrow');
  if(!S.tomorrow.length){el.innerHTML=`<div class="empty"><div class="eico">&#128337;</div><p>No quests for tomorrow yet.</p></div>`;return}
  const sorted=[...S.tomorrow].sort((a,b)=>a.status==='pending'&&b.status==='done'?-1:1);
  el.innerHTML=`<div class="quest-list">${sorted.map(t=>rQI(t,true)).join('')}</div>`;
}

function rCounts(){
  document.getElementById('cnt-daily').textContent=S.daily.filter(t=>t.status==='pending').length;
  document.getElementById('cnt-tomorrow').textContent=S.tomorrow.filter(t=>t.status==='pending').length;
  document.getElementById('cnt-weekly').textContent=S.weekly.filter(t=>t.status==='pending').length;
  document.getElementById('cnt-monthly').textContent=S.monthly.filter(t=>t.status==='pending').length;
}

function rAch(){
  const el=document.getElementById('ach-list');
  if(!S.ach.length){el.innerHTML=`<div class="empty" style="padding:20px"><p>Complete quests to unlock achievements.</p></div>`;return}
  el.innerHTML=S.ach.map(a=>`<div class="ach-item"><div class="at-ico">${a.icon||'\ud83c\udfc6'}</div><div class="at-body"><div class="at">${esc(a.title)}</div><div class="ad">${esc(a.description)}</div></div></div>`).join('');
}

// ══ TAB ═══════════════════════════════════════════════════════════════════════
function switchTab(t){
  activeTab=t;sndSwoosh();
  ['daily','tomorrow','weekly','monthly'].forEach(x=>{
    document.getElementById('tab-'+x).classList.toggle('active',x===t);
    document.getElementById('sec-'+x).classList.toggle('active',x===t);
  });
}

function switchRightTab(t){
  ['challenges','bounties','milestones','achievements'].forEach(x=>{
    const tb=document.getElementById('rtab-'+x);const sc=document.getElementById('rsec-'+x);
    if(tb)tb.classList.toggle('active',x===t);
    if(sc)sc.classList.toggle('active',x===t);
  });
  if(t==='bounties')loadBounties();
}

// ══ GENERATE → SUGGEST (preview → user picks → add-batch) ═══════════════════
let _suggestions = [];
let _suggTarget = 'daily';
let _suggIntent = '';

async function genWith(url,btnId,txtId,spId,target,intent=''){
  const btn=document.getElementById(btnId),txt=document.getElementById(txtId),sp=document.getElementById(spId);
  const oldTxt=txt.textContent;
  btn.disabled=true;txt.textContent='...';sp.style.display='inline-block';
  try{
    const body = JSON.stringify({preview:true, intent: intent||''});
    const items = await api(url,{method:'POST', body});
    if(!Array.isArray(items))throw new Error('Non-array response');
    if(items.length===0){toast('No ideas','The Game Master came up empty. Try again.');return}
    _suggestions = items.map((q,i)=>({...q, task_type: target, picked:true, _k:i}));
    _suggTarget = target;
    _suggIntent = intent;
    openSuggestions();
  }catch(e){console.error('[genWith]',e);toast('Error','Quest generation failed.')}
  btn.disabled=false;txt.textContent=oldTxt;sp.style.display='none';
}

const genDaily=(useIntent=false)=>{
  const intent=useIntent?(document.getElementById('qa-intent').value.trim()):'';
  genWith('/api/tasks/generate', useIntent?'btn-gen-bd':'btn-gen-auto', useIntent?'gen-bd-txt':'gen-auto-txt', useIntent?'gen-bd-sp':'gen-auto-sp', 'daily', intent);
};
const genTomorrow=(useIntent=false)=>{
  const intent=useIntent?(document.getElementById('qa-tomorrow-intent').value.trim()):'';
  genWith('/api/tasks/generate-tomorrow', useIntent?'btn-gen-tm-bd':'btn-gen-tm-auto', useIntent?'gen-tm-txt':'gen-tma-txt', useIntent?'gen-tm-sp':'gen-tma-sp', 'tomorrow', intent);
};
const genWeekly=(useIntent=false)=>{
  const intent=useIntent?(document.getElementById('qa-weekly-intent').value.trim()):'';
  genWith('/api/tasks/generate-weekly', useIntent?'btn-gen-wk-bd':'btn-gen-wk-auto', useIntent?'gen-wn-txt':'gen-wa-txt', useIntent?'gen-wn-sp':'gen-wa-sp', 'weekly', intent);
};
const genMonthly=(useIntent=false)=>{
  const intent=useIntent?(document.getElementById('qa-monthly-intent').value.trim()):'';
  genWith('/api/tasks/generate-monthly', useIntent?'btn-gen-mo-bd':'btn-gen-mo-auto', useIntent?'gen-mn-txt':'gen-ma-txt', useIntent?'gen-mn-sp':'gen-ma-sp', 'monthly', intent);
};

// ── Suggestion modal ──────────────────────────────────────────────────
function openSuggestions(){
  const m=document.getElementById('sugg-modal');
  const titles={daily:'Daily Quests',tomorrow:"Tomorrow's Quests",weekly:'Weekly Goals',monthly:'Monthly Milestones'};
  const icons={daily:'&#9876;&#65039;',tomorrow:'&#127748;',weekly:'&#127919;',monthly:'&#11088;'};
  document.getElementById('sugg-title').textContent=titles[_suggTarget]||'Suggested Quests';
  document.getElementById('sugg-hdr-icon').innerHTML=icons[_suggTarget]||'&#10024;';
  document.getElementById('sugg-sub').textContent=_suggIntent?`Based on: "${_suggIntent}"`:'The Game Master proposes these quests';
  renderSuggestions();
  m.style.display='flex';
  sndAch();
}
function closeSuggestions(){document.getElementById('sugg-modal').style.display='none';_suggestions=[]}
function suggSelectAll(on){_suggestions.forEach(q=>q.picked=!!on);renderSuggestions()}
function toggleSugg(k){const q=_suggestions.find(x=>x._k===k);if(!q)return;q.picked=!q.picked;renderSuggestions()}

function renderSuggestions(){
  const list=document.getElementById('sugg-list');
  if(!_suggestions.length){list.innerHTML='<div class="sugg-empty"><div class="eico">&#128170;</div><p>No suggestions yet.</p></div>';return}
  list.innerHTML=_suggestions.map((q,i)=>{
    const glow=(STAT_GLOW[q.stat]||'var(--accent-glow)');
    return `
    <div class="sugg-item ${q.picked?'picked':''}" onclick="toggleSugg(${q._k})" style="animation-delay:${i*60}ms;--item-glow:${glow}">
      <div class="sugg-check"></div>
      <div class="sugg-body">
        <div class="sugg-desc">${esc(q.description)}</div>
        <div class="sugg-meta">
          <span class="sugg-chip stat" style="background:${STAT_C[q.stat]||'var(--accent)'}">${q.stat}</span>
          <span class="sugg-chip xp">+${q.xp_value} XP</span>
          ${q.timer_minutes?`<span class="sugg-chip tmr">&#9201; ${q.timer_minutes}m</span>`:''}
        </div>
      </div>
    </div>`;
  }).join('');
  const picked=_suggestions.filter(q=>q.picked);
  const n=picked.length;
  const totalXp=picked.reduce((s,q)=>s+(q.xp_value||0),0);
  const cnt=document.getElementById('sugg-count');
  cnt.textContent=`${n} of ${_suggestions.length} selected`;cnt.classList.toggle('has',n>0);
  const xpt=document.getElementById('sugg-xptotal');
  xpt.textContent=`+${totalXp} XP potential`;xpt.classList.toggle('show',n>0);
  const btn=document.getElementById('sugg-accept');btn.disabled=n===0;
  const txt=document.getElementById('sugg-accept-txt');
  if(txt&&!document.getElementById('sugg-accept-sp').style.display.includes('inline')){
    txt.textContent=n>0?`Add ${n} quest${n>1?'s':''}`:`Add quests`;
  }
}

async function acceptSelectedSuggestions(){
  const picked=_suggestions.filter(q=>q.picked);
  if(!picked.length)return;
  const btn=document.getElementById('sugg-accept'),txt=document.getElementById('sugg-accept-txt'),sp=document.getElementById('sugg-accept-sp');
  const oldTxt=txt.textContent;btn.disabled=true;txt.textContent='Adding...';sp.style.display='inline-block';
  try{
    const payload=picked.map(q=>({description:q.description,xp_value:q.xp_value,stat:q.stat,timer_minutes:q.timer_minutes,task_type:_suggTarget}));
    const created=await api('/api/tasks/add-batch',{method:'POST',body:JSON.stringify({quests:payload})});
    if(!Array.isArray(created))throw new Error('Bad response');
    const bucket = _suggTarget==='tomorrow'?'tomorrow':_suggTarget;
    S[bucket]=[...created,...S[bucket]];
    if(bucket==='daily')rDaily();else if(bucket==='tomorrow')rTomorrow();else if(bucket==='weekly')rWeekly();else rMonthly();
    rCounts();rBars();
    confetti(28);sndComplete();
    toast('Quests Accepted',`${created.length} added to the board`);
    closeSuggestions();
  }catch(e){console.error(e);toast('Error','Could not add quests.')}
  btn.disabled=false;txt.textContent=oldTxt;sp.style.display='none';
}

// Esc closes modal
document.addEventListener('keydown',(e)=>{if(e.key==='Escape'&&document.getElementById('sugg-modal').style.display==='flex')closeSuggestions()});

// ══ QUICK ADD ══════════════════════════════════════════════════════════════════
async function quickAdd(type){
  const inputId=`qa-${type}`;const input=document.getElementById(inputId);
  const btn=input.nextElementSibling;
  const desc=input.value.trim();if(!desc)return;
  input.disabled=true;
  if(btn){ btn.disabled=true; btn.innerHTML='<span class="spinner" style="width:12px;height:12px;border-width:2px;margin-right:4px;"></span>...'; }
  try{
    const t=await api('/api/tasks/add',{method:'POST',body:JSON.stringify({description:desc,task_type:type})});
    if(!t.error){
      if(type==='daily')S.daily.unshift(t);
      else if(type==='tomorrow')S.tomorrow.unshift(t);
      else if(type==='weekly')S.weekly.unshift(t);
      else S.monthly.unshift(t);
      if(type==='daily')rDaily();else if(type==='tomorrow')rTomorrow();else if(type==='weekly')rWeekly();else rMonthly();
      rCounts();input.value='';
    }
  }catch(e){console.error(e)}
  input.disabled=false;
  if(btn){ btn.disabled=false; btn.textContent='Add'; }
}

// ══ COMPLETE ════════════════════════════════════════════════════════════════════
async function completeTask(id){
  const el=document.querySelector(`[data-id="${id}"]`);
  if(el){el.classList.add('completing');setTimeout(()=>{el.classList.add('done');el.classList.remove('completing');const ch=el.querySelector('.qcheck');if(ch)ch.removeAttribute('onclick')},400)}
  try{
    const r=await api(`/api/tasks/${id}/complete`,{method:'POST'});
    if(r.error){toast('Cannot Complete',r.error);if(el){el.classList.remove('done','completing')};return}
    if(r.ok){
      const big=r.xp_gained>=300;
      if(big){sndMegaComplete();confetti(55);comboRing();screenFlash(false)}
      else{sndComplete();confetti(22)}
      showXP(r.xp_gained,r.stat);sndChime();
      if(el){const b=el.getBoundingClientRect();sparks(b.left+b.width/2,b.top+b.height/2,'var(--gold)',big?22:12);coinRain(b.left+b.width/2,b.top+b.height/2,big?14:6)}
      bumpCombo();
      if(r.streak && r.streak>0 && r.streak%7===0){setTimeout(()=>{toast('STREAK MILESTONE',`${r.streak}-day streak!`);confetti(80);sndAch()},300)}
      ['daily','tomorrow','weekly','monthly'].forEach(k=>{const t=S[k].find(x=>x.id===id);if(t)t.status='done'});
      // Perfect day check (all daily tasks complete)
      const dTasks=S.daily;
      if(dTasks.length>0 && dTasks.every(t=>t.status==='done')){
        setTimeout(()=>showPerfectDay(), r.leveled_up?2200:1400);
      }
      if(r.user)S.user=r.user;
      rBars();rStats();rCounts();
      // Re-render appropriate section
      if(S.daily.find(t=>t.id===id))rDaily();
      else if(S.tomorrow.find(t=>t.id===id))rTomorrow();
      else if(S.weekly.find(t=>t.id===id))rWeekly();
      else rMonthly();

      if(r.stat_level_ups?.length)r.stat_level_ups.forEach((s,i)=>setTimeout(()=>{sndStatUp();toast('Attribute Level Up!',`${s.stat} reached Lv.${s.new_level}`)},400+i*600));
      if(r.leveled_up){
        setTimeout(()=>showLvl(r.new_level, r.new_title, r.new_unlocks),700);
        if(r.new_unlocks?.length){r.new_unlocks.forEach((u,i)=>setTimeout(()=>showUnlock(u),4500+i*2000))}
      }
      // Refresh + animate challenges
      try{const chd=await api('/api/challenges');S.chal=chd.challenges||[];rChal()}catch(_){}
      if(r.completed_challenges?.length){
        r.completed_challenges.forEach((ch,i)=>setTimeout(()=>{
          showChallengeDone(ch);
          const elc=document.querySelector(`[data-chid="${ch.id}"]`);if(elc)elc.classList.add('chal-just');
        },900+i*1600));
      }
      // Loot drop
      if(r.loot_drop){
        const delay=r.completed_challenges?.length?(900+r.completed_challenges.length*1600+400):1500;
        setTimeout(()=>showLootDrop(r.loot_drop),delay);
      }
      if(r.new_achievements?.length){r.new_achievements.forEach((a,i)=>setTimeout(()=>{sndAch();toast('Achievement Unlocked!',`${a.icon||'\ud83c\udfc6'} ${a.title}`);starShower(10)},1200+i*700));const ad=await api('/api/achievements');S.ach=ad.achievements||[];rAch()}
      // Refresh milestones + today stats
      try{const ms=await api('/api/milestones');rMilestones(ms.milestones||[])}catch(_){}
      rTodayStats();
    }
  }catch(e){console.error(e)}
}

async function delTask(id,type){
  await api(`/api/tasks/${id}`,{method:'DELETE'});
  let removed = null;
  ['daily','tomorrow','weekly','monthly'].forEach(k=>{
     const l = S[k].length;
     S[k]=S[k].filter(t=>t.id!==id);
     if(S[k].length < l){ removed = k; }
  });
  if(removed==='daily')rDaily();
  else if(removed==='tomorrow')rTomorrow();
  else if(removed==='weekly')rWeekly();
  else if(removed==='monthly')rMonthly();
  rCounts();
}

// ══ HISTORY ══════════════════════════════════════════════════════════════════
let histLoaded=false;
async function openHistory(){
  if(!histLoaded){await loadHistory();histLoaded=true}
  document.getElementById('history').classList.add('open');
}
function closeHistory(){document.getElementById('history').classList.remove('open')}

// ══ LEADERBOARD ═══════════════════════════════════════════════════════════
function renderLbRows(list){
  const el=document.getElementById('lb-list');
  if(!list.length){el.innerHTML=`<div class="lb-empty"><div class="lei">\ud83c\udfc6</div><div>No players yet!<br>Complete quests to appear on the leaderboard.</div></div>`;return}
  el.innerHTML=list.map(p=>{
    const rankCls=p.rank===1?'lb-top1':p.rank===2?'lb-top2':p.rank===3?'lb-top3':'';
    const meCls=p.is_me?'lb-me':'';
    const medal=p.rank===1?'\ud83e\udd47':p.rank===2?'\ud83e\udd48':p.rank===3?'\ud83e\udd49':'';
    const avInner=p.profile_photo?`<img src="/static/uploads/${esc(p.profile_photo)}">`:(p.display_name||'?').charAt(0).toUpperCase();
    return `<div class="lb-row ${rankCls} ${meCls}">
      <div class="lb-rank ${rankCls?'':'lb-rank-default'}">${medal||p.rank}</div>
      <div class="lb-av">${avInner}</div>
      <div class="lb-info">
        <div class="lb-name">${esc(p.display_name||p.profile)} <span style="font-size:.65rem;color:var(--text2)">Lv.${p.level}</span></div>
        <div class="lb-title">${p.title_icon||''} ${esc(p.title||'Novice')}</div>
      </div>
      <div class="lb-stats">
        <span class="lb-xp">\u2728 ${(p.total_xp||0).toLocaleString()}</span>
        <span class="lb-streak-val">\ud83d\udd25 ${p.streak||0}</span>
        <span>\u2694\ufe0f ${p.quests_done||0}</span>
      </div>
    </div>`;
  }).join('');
}
async function openLeaderboard(){
  document.getElementById('leaderboard-drawer').classList.add('open');
  exitLbHistory(); // ensure we start on live view
  try{
    const d=await api('/api/leaderboard');
    renderLbRows(d.leaderboard||[]);
  }catch(e){console.error(e)}
}

// ── History view ──
let _lbHistOn=false;
async function toggleLbHistory(){
  if(_lbHistOn){exitLbHistory();return}
  _lbHistOn=true;
  const bar=document.getElementById('lb-hist-bar');if(bar)bar.style.display='flex';
  const title=document.getElementById('lb-title');if(title)title.innerHTML='\ud83d\udcdc Leaderboard History';
  const sel=document.getElementById('lb-hist-sel');
  const el=document.getElementById('lb-list');
  if(el)el.innerHTML=`<div class="empty" style="padding:30px;text-align:center">Loading history...</div>`;
  try{
    const d=await api('/api/leaderboard/history');
    const dates=d.dates||[];
    if(!dates.length){
      if(sel)sel.innerHTML='';
      if(el)el.innerHTML=`<div class="lb-empty"><div class="lei">\ud83d\udcc5</div><div>No snapshots yet.<br>Snapshots are taken daily when someone views the leaderboard.</div></div>`;
      return;
    }
    if(sel){sel.innerHTML=dates.map(dt=>`<option value="${dt}">${dt}</option>`).join('');sel.value=dates[0]}
    await loadLbSnapshot(dates[0]);
  }catch(e){console.error(e);if(el)el.innerHTML='<div class="empty" style="padding:30px;text-align:center">Unable to load history.</div>'}
}
function exitLbHistory(){
  _lbHistOn=false;
  const bar=document.getElementById('lb-hist-bar');if(bar)bar.style.display='none';
  const title=document.getElementById('lb-title');if(title)title.innerHTML='\ud83c\udfc6 Leaderboard';
}
async function loadLbSnapshot(dateStr){
  if(!dateStr)return;
  const el=document.getElementById('lb-list');
  if(el)el.innerHTML=`<div class="empty" style="padding:30px;text-align:center">Loading ${esc(dateStr)}...</div>`;
  try{
    const d=await api('/api/leaderboard/history?date='+encodeURIComponent(dateStr));
    renderLbRows(d.leaderboard||[]);
  }catch(e){console.error(e);if(el)el.innerHTML='<div class="empty" style="padding:30px;text-align:center">Snapshot unavailable.</div>'}
}
function closeLeaderboard(){document.getElementById('leaderboard-drawer').classList.remove('open');exitLbHistory()}

function histTab(t){
  ['daily','weekly','monthly'].forEach(x=>{
    document.getElementById('htab-'+x).classList.toggle('active',x===t);
    document.getElementById('hs-'+x).classList.toggle('active',x===t);
  });
}

async function loadHistory(){
  const h=await api('/api/history');
  // Daily
  const dl=document.getElementById('hlist-daily');
  if(!h.daily_days?.length){dl.innerHTML='<div class="empty"><div class="eico">&#128214;</div><p>No past daily history yet.</p></div>';return}
  dl.innerHTML=h.daily_days.map(day=>{
    const dateLabel=new Date(day.date+'T12:00:00').toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric'});
    const tasks=day.tasks.map(t=>`
      <div class="hd-task">
        <div class="hdt-status ${t.status==='done'?'done':'fail'}">${t.status==='done'?'✓':'✗'}</div>
        <div class="hdt-desc">${esc(t.description)}</div>
        <div class="hdt-meta">
          <span class="qstat" style="background:${STAT_C[t.stat]||'var(--accent)'}; font-size:.55rem;padding:1px 5px;border-radius:4px;color:#fff">${t.stat}</span>
          ${t.status==='done'?`<span style="font-size:.65rem;color:var(--gold)">+${t.xp_value} XP</span>`:`<span style="font-size:.65rem;color:var(--danger)">missed</span>`}
        </div>
      </div>`).join('');
    return `<div class="hist-day">
      <div class="hist-day-hdr" onclick="this.parentElement.classList.toggle('expanded')">
        <div class="hd-left"><div class="date">${dateLabel}</div><div class="stats">${day.completed}/${day.total} completed</div></div>
        <div class="hd-right">
          ${day.xp>0?`<span class="xp-chip">+${day.xp} XP</span>`:''}
          <span class="expand-arrow">&#9660;</span>
        </div>
      </div>
      <div class="hist-day-body">${tasks}</div>
    </div>`;
  }).join('');

  // Weekly
  const wl=document.getElementById('hlist-weekly');
  if(!h.weekly?.length){wl.innerHTML='<div class="empty"><div class="eico">&#128203;</div><p>No past weekly goals yet.</p></div>'}
  else wl.innerHTML=`<div class="quest-list" style="gap:8px">${h.weekly.map(t=>`<div class="qi" style="opacity:${t.status==='done'?1:.5}"><div class="qcheck ${t.status==='done'?'':'locked'}"></div><div class="qbody"><div class="qd">${esc(t.description)}</div><div class="qmeta"><span class="qstat" style="background:${STAT_C[t.stat]}">${t.stat}</span><span class="qxp" style="color:var(--gold)">+${t.xp_value} XP</span></div></div></div>`).join('')}</div>`;

  // Monthly
  const ml=document.getElementById('hlist-monthly');
  if(!h.monthly?.length){ml.innerHTML='<div class="empty"><div class="eico">&#127775;</div><p>No past monthly milestones yet.</p></div>'}
  else ml.innerHTML=`<div class="quest-list" style="gap:8px">${h.monthly.map(t=>`<div class="qi" style="opacity:${t.status==='done'?1:.5}"><div class="qcheck ${t.status==='done'?'':'locked'}"></div><div class="qbody"><div class="qd">${esc(t.description)}</div><div class="qmeta"><span class="qstat" style="background:${STAT_C[t.stat]}">${t.stat}</span><span class="qxp" style="color:var(--gold)">+${t.xp_value} XP</span></div></div></div>`).join('')}</div>`;
}

// ══ SETTINGS ════════════════════════════════════════════════════════════════
function openSettings(){
  const u=S.user;
  document.getElementById('s-name').value=u.display_name||'';
  document.getElementById('s-prof').value=u.profession||'';
  document.getElementById('s-bio').value=u.bio||'';
  document.getElementById('s-motiv').value=u.motivation||'';
  document.getElementById('s-monthly').value=u.monthly_goal||'';
  document.getElementById('s-weekly').value=u.weekly_goal||'';
  // photo
  const pp=document.getElementById('s-photo-prev'),rb=document.getElementById('s-rm-photo');
  if(u.profile_photo){pp.innerHTML=`<img src="/static/uploads/${esc(u.profile_photo)}"><input type="file" accept="image/*" onchange="uploadPhoto(this)">`;rb.style.display='inline-flex'}
  else{pp.innerHTML=`<span class="ph-hint">Add<br>Photo</span><input type="file" accept="image/*" onchange="uploadPhoto(this)">`;rb.style.display='none'}
  // persona opts
  const po=document.getElementById('s-persona-opts');
  po.innerHTML=Object.entries(S.user.personas||{}).map(([k,p])=>
    `<div class="popt ${k===u.persona?'active':''}" onclick="setSPersona(this,'${k}')">${p.icon} ${p.name}</div>`
  ).join('');
  sPersona=u.persona;
  
  const isLight = document.documentElement.getAttribute('data-theme') === 'light';
  document.getElementById('theme-cb').checked = isLight;
  
  document.getElementById('settings').style.display='flex';
}
function setSPersona(el,k){sPersona=k;document.querySelectorAll('.popt').forEach(x=>x.classList.remove('active'));el.classList.add('active')}
function closeSettings(){document.getElementById('settings').style.display='none'}
async function saveSettings(){
  const d={display_name:document.getElementById('s-name').value.trim(),profession:document.getElementById('s-prof').value.trim(),bio:document.getElementById('s-bio').value.trim(),motivation:document.getElementById('s-motiv').value.trim(),monthly_goal:document.getElementById('s-monthly').value.trim(),weekly_goal:document.getElementById('s-weekly').value.trim()};
  if(sPersona)d.persona=sPersona;
  await api('/api/user/update',{method:'POST',body:JSON.stringify(d)});
  S.user=await api('/api/user');renderAll();closeSettings();
}
async function uploadPhoto(input){
  if(!input.files?.[0])return;
  const fd=new FormData();fd.append('photo',input.files[0]);
  const r=await fetch(withProfile('/api/user/photo'),{method:'POST',body:fd});
  const d=await r.json();
  if(d.ok){S.user.profile_photo=d.filename;rProfile();const pp=document.getElementById('s-photo-prev');pp.innerHTML=`<img src="/static/uploads/${d.filename}"><input type="file" accept="image/*" onchange="uploadPhoto(this)">`;document.getElementById('s-rm-photo').style.display='inline-flex'}
}
async function removePhoto(){await api('/api/user/photo',{method:'DELETE'});S.user.profile_photo='';rProfile();const pp=document.getElementById('s-photo-prev');pp.innerHTML=`<span class="ph-hint">Add<br>Photo</span><input type="file" accept="image/*" onchange="uploadPhoto(this)">`;document.getElementById('s-rm-photo').style.display='none'}
async function resetAll(){if(!confirm('Reset ALL progress? This cannot be undone!'))return;await api('/api/reset',{method:'POST'});location.reload()}

// ══ BOOT ════════════════════════════════════════════════════════════════════
init();

// ══ SSE — Real-time multi-device sync ═══════════════════════════════════════
let _sseIgnoreUntil = 0; // ignore self-triggered syncs for 2s
const _origApi = api;
// Wrap api to set ignore window on mutations
const apiWithSync = async (url, o = {}) => {
  const r = await _origApi(url, o);
  if (o.method && o.method !== 'GET') _sseIgnoreUntil = Date.now() + 2000;
  return r;
};
// reassign api for all existing callers
api = apiWithSync;

let _rcAttempt = 0;
function connectSSE() {
  const es = new EventSource(withProfile('/api/events'));
  es.addEventListener('connected', () => {
    _rcAttempt = 0;
    document.getElementById('conn-badge').style.display = 'none';
    loadAll(); // Resync state immediately because we might have missed updates while offline
  });
  es.addEventListener('sync', (e) => {
    if (Date.now() < _sseIgnoreUntil) return; // skip own echo
    loadAll(); // silently refresh everything
  });
  es.addEventListener('reset', () => {
    location.reload();
  });
  es.onerror = () => {
    es.close();
    document.getElementById('conn-badge').style.display = 'flex';
    // Exponential backoff, up to 30 seconds
    _rcAttempt++;
    const delay = Math.min(30000, 2000 * Math.pow(1.5, _rcAttempt));
    setTimeout(connectSSE, delay); 
  };
}
// ══ LOGIN REWARDS ════════════════════════════════════════════════════════════
async function tryLoginReward(){
  const info=await api('/api/login-info');
  if(info.claimed_today)return;
  showLoginReward();
}

async function showLoginReward(){
  const info=await api('/api/login-info');
  const e=document.createElement('div');e.className='login-reward';e.id='lr-overlay';
  const cycle=info.cycle||[];
  const dots=cycle.map((d,i)=>{
    let cls='lr-dot';
    if(d.claimed)cls+=' claimed';
    if(d.day===((info.current_day||0)+1) && !info.claimed_today)cls+=' today';
    if(d.bonus==='jackpot')cls+=' jackpot';
    return `<div class="${cls}" style="animation:lrDotIn .35s cubic-bezier(.34,1.56,.64,1) ${.1+i*.06}s both">${d.day}</div>`;
  }).join('');
  const nextDay=info.claimed_today?(info.current_day||0):(info.current_day||0)+1;
  const nextReward=cycle.find(d=>d.day===nextDay)||cycle[0];
  e.innerHTML=`<div class="lr-box">
    <div class="lr-title">Daily Login Reward</div>
    <div class="lr-day">Day ${nextDay}</div>
    <div class="lr-desc">${nextReward?nextReward.desc:'Welcome back!'}</div>
    <div class="lr-xp">+${nextReward?nextReward.xp:50} XP</div>
    <div class="lr-cal">${dots}</div>
    <button class="lr-claim ${info.claimed_today?'lr-claimed':''}" id="lr-claim-btn" onclick="${info.claimed_today?'closeLR()':'claimLoginReward()'}">${info.claimed_today?'Already Claimed — Close':'Claim Reward!'}</button>
  </div>`;
  document.body.appendChild(e);
}

async function claimLoginReward(){
  const btn=document.getElementById('lr-claim-btn');if(btn){btn.disabled=true;btn.textContent='Claiming...'}
  const r=await api('/api/login-reward',{method:'POST'});
  if(r.already_claimed){closeLR();return}
  sndChallenge();confetti(40);starShower(18);
  if(r.bonus==='jackpot'){setTimeout(()=>{sndLevelUp();confetti(80);starShower(30)},300)}
  if(btn){btn.textContent=`+${r.reward_xp} XP Claimed!`;btn.className='lr-claim lr-claimed'}
  toast('Daily Reward!',`+${r.reward_xp} XP earned!`);
  const da=document.getElementById('da-login');if(da){da.classList.add('tb-claimed')}
  setTimeout(closeLR,1800);
  // Refresh user
  const u=await api('/api/user');S.user=u;rBars();rProfile();
}

function closeLR(){const e=document.getElementById('lr-overlay');if(e)e.remove()}

// ══ LOOT DROP ════════════════════════════════════════════════════════════════
const sndLoot=()=>{tone([440,554,659,880],'triangle',.12,.25,.07);setTimeout(()=>tone([880,1100,1320],'sine',.08,.3,.08),200)};
const sndLegendary=()=>{tone([262,330,392,523,659,784,1047],'triangle',.16,.35,.07);setTimeout(()=>{tone([523,659,784,1047,1319],'sine',.12,.4,.06)},250)};

function showLootDrop(loot){
  const e=document.createElement('div');e.className='loot-pop';
  const r=loot.rarity||'common';
  const isLeg=r==='legendary';const isEpic=r==='epic';
  if(isLeg)sndLegendary();else sndLoot();
  if(isLeg){confetti(60);starShower(25)}else if(isEpic){confetti(35);starShower(12)}else if(r==='rare')confetti(18);
  e.innerHTML=`<div class="loot-chest">\ud83c\udf81</div><div class="loot-card ${r}">
    <div class="loot-rarity ${r}">${r}</div>
    <div class="loot-ico">${loot.icon||'\ud83c\udf1f'}</div>
    <div class="loot-name">${esc(loot.name)}</div>
    <div class="loot-desc">${esc(loot.description)}</div>
    ${loot.bonus_xp?`<div class="loot-bonus">+${loot.bonus_xp} XP</div>`:''}
  </div>`;
  document.body.appendChild(e);
  setTimeout(()=>e.remove(),3200);
}

// ══ MILESTONES ═══════════════════════════════════════════════════════════════
function rMilestones(milestones){
  const el=document.getElementById('ms-list');if(!el)return;
  if(!milestones||!milestones.length){el.innerHTML=`<div class="empty" style="padding:12px;font-size:.8rem">Complete quests to see milestones!</div>`;return}
  el.innerHTML=milestones.map(m=>{
    const pct=Math.min(100,Math.round((m.current/m.target)*100));
    const left=m.target-m.current;
    return `<div class="ms-item">
      <div class="ms-top">
        <div class="ms-ico">${m.icon||'\u2b50'}</div>
        <div class="ms-info"><div class="ms-label">${esc(m.label)}</div><div class="ms-desc">${esc(m.desc)}</div></div>
        <div class="ms-close">${left} away</div>
      </div>
      <div class="ms-bar"><div class="ms-fill" style="width:${pct}%"></div></div>
      <div class="ms-meta"><span>${m.current} / ${m.target}</span><span>${pct}%</span></div>
    </div>`;
  }).join('');
}

// ══ TODAY STATS ══════════════════════════════════════════════════════════════
const QUOTES=[
  "The secret of getting ahead is getting started.",
  "Small daily improvements are the key to staggering long-term results.",
  "You don't have to be great to start, but you have to start to be great.",
  "Discipline is choosing between what you want now and what you want most.",
  "The only bad workout is the one that didn't happen.",
  "Level by level, day by day — that's how legends are made.",
  "Your future self is watching you right now through memories.",
  "Don't count the days. Make the days count.",
  "Consistency beats intensity. Show up every day.",
  "The grind you hate today is the glory you celebrate tomorrow.",
  "One quest at a time. One level at a time. You've got this.",
  "Progress, not perfection.",
  "Winners are just losers who tried one more time.",
  "The harder the battle, the sweeter the victory.",
  "Push yourself, because no one else is going to do it for you."
];
function dailyQuote(){const d=new Date();const idx=(d.getFullYear()*367+d.getMonth()*31+d.getDate())%QUOTES.length;return QUOTES[idx]}

async function rTodayStats(){
  try{
    const ts=await api('/api/today-stats');
    const eq=document.getElementById('ts-quests');if(eq)eq.textContent=ts.quests_done||0;
    const ex=document.getElementById('ts-xp');if(ex)ex.textContent=ts.xp_earned||0;
    const el=document.getElementById('ts-loot');if(el)el.textContent=ts.loot_found||0;
  }catch(_){}
  const qq=document.getElementById('ts-quote');if(qq)qq.textContent=`"${dailyQuote()}"`;
}

// ══ DAILY GIFT STATE ═════════════════════════════════════════════════════════
async function checkDailyGift(){
  try{
    const li=await api('/api/login-info');
    const dal=document.getElementById('da-login');
    if(li.claimed_today&&dal){dal.classList.add('tb-claimed')}
  }catch(_){}
}

// ══ PET WIDGET ═══════════════════════════════════════════════════════════════
const PET_STAGE_ICONS={egg:'\ud83e\udd5a',baby:'\ud83d\udc23',juvenile:'\ud83d\udc24',adult:'\ud83d\udc25',ancient:'\ud83d\udc09'};
function rPet(){
  const host=document.getElementById('pet-slot');if(!host)return;
  const p=S.pet;
  if(!p||!p.species){
    host.innerHTML=`<div class="pet-empty" onclick="openPetHatch()"><div class="pet-empty-ico">\ud83e\udd5a</div><div><div class="pet-empty-txt">Hatch a Companion</div><div class="pet-empty-sub">Tap to choose your pet</div></div></div>`;
    return;
  }
  const stage=p.stage||{};
  const spIcon=(S.petSpecies||[]).find(s=>(s.key||s.id)===p.species)?.icon||'\ud83d\udc3e';
  const stIcon=PET_STAGE_ICONS[p.stage_id||p.stage_key]||spIcon;
  const multPct=Math.round(((stage.xp_mult||1)-1)*100);
  host.innerHTML=`<div class="pet-card-active" onclick="openPetDetail()">
    <div class="pet-avatar">${stIcon}</div>
    <div class="pet-info">
      <div class="pet-name-row"><span class="pet-name">${esc(p.name||'Companion')}</span><span class="pet-stage-badge">${esc(stage.name||'')}</span></div>
      <div class="pet-lvl">Lv.${p.level||1}${multPct>0?` \u00b7 +${multPct}% XP`:''}</div>
      <div class="pet-meters">
        <div class="pet-meter happy"><span>\u2764\ufe0f</span><div class="pet-meter-bar"><div class="pet-meter-fill" style="width:${p.happiness||0}%"></div></div></div>
        <div class="pet-meter hunger"><span>\ud83c\udf57</span><div class="pet-meter-bar"><div class="pet-meter-fill" style="width:${p.hunger||0}%"></div></div></div>
      </div>
    </div>
  </div>`;
}

function openPetHatch(){
  const modal=document.getElementById('pet-hatch-modal');if(!modal)return;
  const grid=document.getElementById('pet-species-grid');
  const species=S.petSpecies||[];
  if(!species.length){toast('Loading...','Pet data not ready yet, try again in a moment.');return}
  grid.innerHTML=species.map(s=>{
    const k=s.key||s.id;
    return `<div class="pet-species-card" onclick="selectPetSpecies('${k}')" data-sp="${k}">
    <div class="pet-species-ico">${s.icon}</div>
    <div class="pet-species-name">${esc(s.name)}</div>
    <div class="pet-species-desc">${esc(s.desc||s.trait||s.description||'')}</div>
  </div>`;
  }).join('');
  _selSp=null;
  const btn=document.getElementById('pet-hatch-confirm');if(btn)btn.disabled=true;
  modal.style.display='flex';
}
function closePetHatch(){const m=document.getElementById('pet-hatch-modal');if(m)m.style.display='none'}
let _selSp=null;
function selectPetSpecies(id){
  _selSp=id;
  document.querySelectorAll('.pet-species-card').forEach(c=>c.classList.toggle('selected',c.dataset.sp===id));
  document.getElementById('pet-hatch-confirm').disabled=false;
}
async function hatchPet(){
  if(!_selSp)return;
  const nm=document.getElementById('pet-name-input').value.trim()||'Buddy';
  try{
    const r=await api('/api/pet/hatch',{method:'POST',body:JSON.stringify({species:_selSp,name:nm})});
    if(r.error){toast('Error',r.error);return}
    S.pet=r.pet;rPet();
    closePetHatch();
    sndAch?.();confetti?.(40);
    toast('Companion Hatched!',`${nm} has joined your journey!`);
  }catch(e){console.error(e)}
}
function openPetDetail(){
  const p=S.pet;if(!p)return;
  const spIcon=(S.petSpecies||[]).find(s=>(s.key||s.id)===p.species)?.icon||'\ud83d\udc3e';
  const stage=p.stage||{};
  const multPct=Math.round(((stage.xp_mult||1)-1)*100);
  toast(`${p.name||'Pet'} \u00b7 ${stage.name||''}`,`Lv.${p.level||1} ${spIcon} \u00b7 +${multPct}% XP bonus on quests.`);
}

// ══ BOUNTIES ═════════════════════════════════════════════════════════════════
async function loadBounties(){
  try{
    const d=await api('/api/bounties');
    S.bounties=d.bounties||[];
    rBounties();
  }catch(e){console.error(e)}
}
function rBounties(){
  const el=document.getElementById('bnt-list');if(!el)return;
  const list=S.bounties||[];
  if(!list.length){el.innerHTML=`<div class="empty" style="padding:16px;font-size:.8rem">New bounties arrive daily. Check back tomorrow!</div>`;return}
  el.innerHTML=list.map(b=>{
    const target=b.target_value||b.target||1;
    const prog=Math.min(b.progress||0,target);
    const pct=Math.min(100,Math.round((prog/target)*100));
    const done=b.completed?'completed':'';
    return `<div class="bnt-item ${done}">
      <div class="bnt-top"><div class="bnt-ico">${b.icon||'\ud83c\udfaf'}</div><div class="bnt-desc">${esc(b.description||b.label||'')}</div><div class="bnt-reward">\ud83d\udc8e ${b.reward_gems||0}</div></div>
      <div class="bnt-bar"><div class="bnt-fill" style="width:${pct}%"></div></div>
      <div class="bnt-meta"><span>${prog} / ${target}</span><span>${pct}%${b.completed?' \u2713':''}</span></div>
    </div>`;
  }).join('');
}

// ══ SHOP ═════════════════════════════════════════════════════════════════════
const SHOP_CAT_ICONS={powerup:'\u26a1',mystery:'\ud83c\udf81',pet:'\ud83d\udc3e',cosmetic:'\u2728'};
async function openShop(){
  const drawer=document.getElementById('shop-drawer');if(!drawer)return;
  drawer.classList.add('open');
  try{
    const d=await api('/api/shop');
    S.shopItems=d.items||[];
    const g=document.getElementById('shop-gems-count');if(g)g.textContent=(S.user?.gems)||0;
    const grid=document.getElementById('shop-grid');
    grid.innerHTML=S.shopItems.map(it=>{
      const cat=it.category||'powerup';
      const canAfford=(S.user?.gems||0)>=it.price;
      return `<div class="shop-item cat-${cat}">
        <div class="shop-icon">${it.icon||SHOP_CAT_ICONS[cat]||'\ud83d\udce6'}</div>
        <div class="shop-name">${esc(it.name)}</div>
        <div class="shop-desc">${esc(it.description||'')}</div>
        <button class="shop-buy" ${canAfford?'':'disabled'} onclick="buyItem('${it.key}')">\ud83d\udc8e ${it.price}</button>
      </div>`;
    }).join('');
  }catch(e){console.error(e)}
}
function closeShop(){document.getElementById('shop-drawer')?.classList.remove('open')}
async function buyItem(key){
  try{
    const r=await api('/api/shop/buy',{method:'POST',body:JSON.stringify({item_key:key})});
    if(r.error){toast('Cannot Buy',r.error);return}
    if(r.user)S.user=r.user;
    rProfile();
    const g=document.getElementById('shop-gems-count');if(g)g.textContent=S.user?.gems||0;
    if(r.mystery_reward){showMysteryReveal(r.mystery_reward)}
    else{sndChime?.();toast('Purchased!',`${r.item?.name||r.item_name||'Item'} added to inventory`)}
    // refresh shop affordability
    document.querySelectorAll('.shop-buy').forEach(b=>{
      const price=parseInt(b.textContent.replace(/[^\d]/g,''),10)||0;
      b.disabled=(S.user?.gems||0)<price;
    });
  }catch(e){console.error(e)}
}

// ══ INVENTORY ════════════════════════════════════════════════════════════════
async function openInventory(){
  const drawer=document.getElementById('inv-drawer');if(!drawer)return;
  drawer.classList.add('open');
  try{
    const d=await api('/api/inventory');
    const items=d.inventory||[];
    const boosts=d.active_boosts||{};
    const boostsEl=document.getElementById('inv-boosts');
    if(boostsEl){
      const bKeys=Object.keys(boosts);
      boostsEl.innerHTML=bKeys.length?bKeys.map(k=>{
        const b=boosts[k];
        let lbl='';
        if(b.expires_at){const mins=Math.max(0,Math.round((b.expires_at*1000-Date.now())/60000));lbl=`${mins}m left`}
        else if(b.charges){lbl=`${b.charges} use${b.charges>1?'s':''}`}
        return `<div class="inv-boost-chip">\u26a1 ${esc(k)} <span>\u00b7 ${lbl}</span></div>`;
      }).join(''):'<div style="color:var(--text3);font-size:.75rem">No active boosts</div>';
    }
    const grid=document.getElementById('inv-grid');
    if(!items.length){grid.innerHTML=`<div class="empty" style="padding:24px;font-size:.85rem;grid-column:1/-1">Your bag is empty. Visit the shop!</div>`;return}
    grid.innerHTML=items.map(it=>`<div class="inv-item">
      <div class="inv-icon">${it.icon||'\ud83d\udce6'}</div>
      <div class="inv-name">${esc(it.name)}</div>
      <div class="inv-qty">\u00d7${it.quantity}</div>
      <div class="inv-desc">${esc(it.description||'')}</div>
      <div class="inv-actions">
        <button class="inv-use" onclick="useItem('${it.item_key}')">Use</button>
        <button class="inv-gift" onclick="chooseGiftRecipient('${it.item_key}','${esc(it.name)}')">Gift</button>
      </div>
    </div>`).join('');
  }catch(e){console.error(e)}
}
function closeInventory(){document.getElementById('inv-drawer')?.classList.remove('open')}
async function useItem(key){
  try{
    const r=await api('/api/inventory/use',{method:'POST',body:JSON.stringify({item_key:key})});
    if(r.error){toast('Cannot Use',r.error);return}
    if(r.user)S.user=r.user;
    rProfile();rBars();rStats();
    if(r.mystery_reward){showMysteryReveal(r.mystery_reward)}
    else{sndChime?.();toast('Used!',r.message||'Item used')}
    openInventory(); // refresh
  }catch(e){console.error(e)}
}

// ══ MYSTERY BOX REVEAL ═══════════════════════════════════════════════════════
function showMysteryReveal(reward){
  const rarity=reward.rarity||'common';
  const overlay=document.createElement('div');
  overlay.className='mbox-overlay';
  overlay.innerHTML=`<div class="mbox-reveal mbox-${rarity}">
    <div class="mbox-shine"></div>
    <div class="mbox-rarity-label">${rarity.toUpperCase()}</div>
    <div class="mbox-icon">${reward.icon||'\ud83c\udf81'}</div>
    <div class="mbox-name">${esc(reward.name||'Reward')}</div>
    <div class="mbox-desc">${esc(reward.description||'')}</div>
    <button class="mbox-close" onclick="this.closest('.mbox-overlay').remove()">Claim</button>
  </div>`;
  document.body.appendChild(overlay);
  sndAch?.();confetti?.(rarity==='legendary'?80:rarity==='rare'?45:25);
  if(rarity==='legendary')starShower?.(16);
}

// ══ GEM POP / BOUNTY POP ═════════════════════════════════════════════════════
function showGemPop(amount){
  if(!amount)return;
  const el=document.createElement('div');
  el.className='gempop';
  el.innerHTML=`\ud83d\udc8e +${amount}`;
  const pill=document.getElementById('gems-pill');
  const r=pill?pill.getBoundingClientRect():{left:window.innerWidth-100,top:60,width:60};
  el.style.left=(r.left+r.width/2-20)+'px';
  el.style.top=(r.top+30)+'px';
  document.body.appendChild(el);
  setTimeout(()=>el.remove(),1800);
}
function showBountyComplete(b){
  const el=document.createElement('div');
  el.className='bnt-pop';
  el.innerHTML=`<div class="bnt-pop-ic">${b.icon||'\ud83c\udfaf'}</div><div class="bnt-pop-txt"><div>Bounty Complete!</div><div class="bnt-pop-sub">${esc(b.description||b.label||'')} \u00b7 \ud83d\udc8e +${b.reward_gems}</div></div>`;
  document.body.appendChild(el);
  sndAch?.();
  setTimeout(()=>el.remove(),3000);
}

// ══ WEEKLY REPORT ════════════════════════════════════════════════════════════
function simpleMarkdown(md){
  if(!md)return '';
  let h=esc(md);
  h=h.replace(/^###\s+(.+)$/gm,'<h3>$1</h3>');
  h=h.replace(/^##\s+(.+)$/gm,'<h2>$1</h2>');
  h=h.replace(/^#\s+(.+)$/gm,'<h1>$1</h1>');
  h=h.replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>');
  h=h.replace(/\*(.+?)\*/g,'<em>$1</em>');
  h=h.replace(/`([^`]+)`/g,'<code>$1</code>');
  h=h.replace(/^[-*]\s+(.+)$/gm,'<li>$1</li>');
  h=h.replace(/(<li>[\s\S]+?<\/li>)/g,m=>`<ul>${m}</ul>`);
  h=h.replace(/<\/ul>\s*<ul>/g,'');
  h=h.split(/\n\n+/).map(p=>/^<(h\d|ul|ol|blockquote|pre)/.test(p)?p:`<p>${p.replace(/\n/g,'<br>')}</p>`).join('');
  return h;
}
function renderWeeklyReport(d){
  const body=document.getElementById('wr-body');
  const meta=document.getElementById('wr-meta');
  const regen=document.getElementById('wr-regen-btn');
  if(meta)meta.textContent=d.week_start?`Week of ${d.week_start}`:'AI-generated weekly retrospective';
  if(d.available===false){
    if(regen)regen.style.display='none';
    body.innerHTML=`<div class="wr-unavailable">
      <div class="wr-unavail-ico">\ud83d\uddd3\ufe0f</div>
      <div class="wr-unavail-title">Available on the weekend</div>
      <div class="wr-unavail-desc">${esc(d.message||'Weekly reports are generated every Saturday and Sunday.')}</div>
      <div class="wr-unavail-badge">Next: Saturday</div>
    </div>`;
    return;
  }
  if(regen)regen.style.display='';
  body.innerHTML=simpleMarkdown(d.content||d.report||'No report available.');
}
async function openWeeklyReport(){
  const overlay=document.getElementById('wr-overlay');if(!overlay)return;
  overlay.style.display='flex';
  exitWrHistory();
  const body=document.getElementById('wr-body');
  body.innerHTML=`<div class="wr-loading"><div class="wr-spin"></div><div>Analyzing your week...</div></div>`;
  try{
    const d=await api('/api/weekly-report');
    renderWeeklyReport(d);
  }catch(e){
    body.innerHTML='<p>Unable to generate report. Please try again later.</p>';
  }
}
function closeWeeklyReport(){const m=document.getElementById('wr-overlay');if(m){m.style.display='none';exitWrHistory()}}

// ── Weekly report history ──
let _wrHistOn=false;
async function toggleWrHistory(){
  if(_wrHistOn){exitWrHistory();return}
  _wrHistOn=true;
  const bar=document.getElementById('wr-hist-bar');if(bar)bar.style.display='flex';
  const title=document.getElementById('wr-title');if(title)title.textContent='Report History';
  const regen=document.getElementById('wr-regen-btn');if(regen)regen.style.display='none';
  const body=document.getElementById('wr-body');
  const sel=document.getElementById('wr-hist-sel');
  if(body)body.innerHTML=`<div class="wr-loading"><div class="wr-spin"></div><div>Loading history...</div></div>`;
  try{
    const d=await api('/api/weekly-report/history');
    const weeks=d.weeks||[];
    if(!weeks.length){
      if(sel)sel.innerHTML='';
      if(body)body.innerHTML=`<div class="wr-unavailable">
        <div class="wr-unavail-ico">\ud83d\udcdc</div>
        <div class="wr-unavail-title">No past reports yet</div>
        <div class="wr-unavail-desc">Your weekly reports will show up here once you generate your first one on a Saturday or Sunday.</div>
      </div>`;
      return;
    }
    if(sel){sel.innerHTML=weeks.map(w=>`<option value="${w.week_start}">Week of ${w.week_start}</option>`).join('');sel.value=weeks[0].week_start}
    await loadWrWeek(weeks[0].week_start);
  }catch(e){console.error(e);if(body)body.innerHTML='<p>Unable to load history.</p>'}
}
function exitWrHistory(){
  _wrHistOn=false;
  const bar=document.getElementById('wr-hist-bar');if(bar)bar.style.display='none';
  const title=document.getElementById('wr-title');if(title)title.textContent='Weekly Report';
  const regen=document.getElementById('wr-regen-btn');if(regen)regen.style.display='';
}
async function loadWrWeek(week){
  if(!week)return;
  const body=document.getElementById('wr-body');
  if(body)body.innerHTML=`<div class="wr-loading"><div class="wr-spin"></div><div>Loading week of ${esc(week)}...</div></div>`;
  try{
    const d=await api('/api/weekly-report?week='+encodeURIComponent(week));
    renderWeeklyReport(d);
    // Keep the regen button hidden in history view (renderWeeklyReport may have re-shown it)
    const regen=document.getElementById('wr-regen-btn');if(regen)regen.style.display='none';
  }catch(e){if(body)body.innerHTML='<p>Snapshot unavailable.</p>'}
}
async function regenWeeklyReport(){
  const body=document.getElementById('wr-body');
  if(body)body.innerHTML=`<div class="wr-loading"><div class="wr-spin"></div><div>Regenerating...</div></div>`;
  try{
    const d=await api('/api/weekly-report?regen=1');
    renderWeeklyReport(d);
  }catch(e){if(body)body.innerHTML='<p>Unable to regenerate.</p>'}
}

// ══ GIFT FLOW ════════════════════════════════════════════════════════════════
let _giftItemKey=null,_giftItemName='';
function chooseGiftRecipient(itemKey,itemName){
  _giftItemKey=itemKey;_giftItemName=itemName;
  closeInventory();
  openLeaderboard();
  setTimeout(()=>{
    const list=document.getElementById('lb-list');
    if(list){
      const banner=document.createElement('div');
      banner.id='gift-mode-banner';
      banner.style.cssText='padding:10px 14px;margin-bottom:8px;background:linear-gradient(90deg,rgba(236,72,153,.2),rgba(139,92,246,.2));border:1px solid rgba(236,72,153,.4);border-radius:10px;font-size:.8rem;text-align:center';
      banner.innerHTML=`\ud83c\udf81 Choose recipient for <b>${esc(itemName)}</b> <span onclick="closeGiftPicker()" style="margin-left:8px;cursor:pointer;color:var(--text3)">\u00d7 cancel</span>`;
      list.insertBefore(banner,list.firstChild);
      list.querySelectorAll('.lb-row').forEach(row=>{
        if(row.classList.contains('lb-me'))return;
        const nameEl=row.querySelector('.lb-name');
        const profile=(nameEl?.textContent||'').trim().split(' ')[0];
        const btn=document.createElement('button');
        btn.className='lb-gift-btn';
        btn.textContent='\ud83c\udf81 Gift';
        btn.onclick=(ev)=>{ev.stopPropagation();pickGiftTarget(profile,nameEl?.textContent||profile)};
        row.appendChild(btn);
      });
    }
  },200);
}
function closeGiftPicker(){
  _giftItemId=null;_giftItemName='';
  document.getElementById('gift-mode-banner')?.remove();
  document.querySelectorAll('.lb-gift-btn').forEach(b=>b.remove());
}
async function pickGiftTarget(profile,displayName){
  if(!_giftItemKey)return;
  try{
    const r=await api('/api/gift/send',{method:'POST',body:JSON.stringify({to_profile:profile,item_key:_giftItemKey})});
    if(r.error){toast('Cannot Gift',r.error);return}
    sndChime?.();confetti?.(30);
    toast('Gift Sent!',`${_giftItemName} on its way to ${displayName}`);
    closeGiftPicker();
    closeLeaderboard();
  }catch(e){console.error(e)}
}

// ══ GIFT RECEIVING POLLER ════════════════════════════════════════════════════
async function checkGifts(){
  try{
    const d=await api('/api/gifts');
    const pending=(d.gifts||[]).filter(g=>!g.claimed);
    if(pending.length){
      for(const g of pending){
        await new Promise(res=>{
          const ov=document.createElement('div');
          ov.className='mbox-overlay';
          ov.innerHTML=`<div class="mbox-reveal mbox-rare">
            <div class="mbox-shine"></div>
            <div class="mbox-rarity-label">GIFT FROM ${esc((g.from_name||g.from_profile||'').toUpperCase())}</div>
            <div class="mbox-icon">${g.icon||'\ud83c\udf81'}</div>
            <div class="mbox-name">${esc(g.name||'Mystery Gift')}</div>
            <div class="mbox-desc">${esc(g.message||g.description||'A gift has arrived!')}</div>
            <button class="mbox-close">Accept</button>
          </div>`;
          document.body.appendChild(ov);
          sndAch?.();confetti?.(40);
          ov.querySelector('.mbox-close').onclick=async()=>{
            try{await api('/api/gifts/claim',{method:'POST',body:JSON.stringify({gift_id:g.id})})}catch(_){}
            ov.remove();res();
          };
        });
      }
      // refresh inventory state
      try{const u=await api('/api/user');S.user=u;rProfile()}catch(_){}
    }
  }catch(_){}
}

// ══ COMPLETE-TASK PATCH (gems, bounties, pet level-up) ═══════════════════════
const _origComplete = completeTask;
completeTask = async function(id){
  const el=document.querySelector(`[data-id="${id}"]`);
  if(el){el.classList.add('completing');setTimeout(()=>{el.classList.add('done');el.classList.remove('completing');const ch=el.querySelector('.qcheck');if(ch)ch.removeAttribute('onclick')},400)}
  try{
    const r=await api(`/api/tasks/${id}/complete`,{method:'POST'});
    if(r.error){toast('Cannot Complete',r.error);if(el){el.classList.remove('done','completing')};return}
    if(r.ok){
      const big=r.xp_gained>=300;
      if(big){sndMegaComplete();confetti(55);comboRing();screenFlash(false)}
      else{sndComplete();confetti(22)}
      showXP(r.xp_gained,r.stat);sndChime();
      if(el){const b=el.getBoundingClientRect();sparks(b.left+b.width/2,b.top+b.height/2,'var(--gold)',big?22:12);coinRain(b.left+b.width/2,b.top+b.height/2,big?14:6)}
      bumpCombo();
      if(r.gems_earned){showGemPop(r.gems_earned)}
      if(r.streak && r.streak>0 && r.streak%7===0){setTimeout(()=>{toast('STREAK MILESTONE',`${r.streak}-day streak!`);confetti(80);sndAch()},300)}
      ['daily','tomorrow','weekly','monthly'].forEach(k=>{const t=S[k].find(x=>x.id===id);if(t)t.status='done'});
      const dTasks=S.daily;
      if(dTasks.length>0 && dTasks.every(t=>t.status==='done')){setTimeout(()=>showPerfectDay(), r.leveled_up?2200:1400)}
      if(r.user)S.user=r.user;
      rBars();rStats();rCounts();rProfile();
      if(S.daily.find(t=>t.id===id))rDaily();
      else if(S.tomorrow.find(t=>t.id===id))rTomorrow();
      else if(S.weekly.find(t=>t.id===id))rWeekly();
      else rMonthly();
      if(r.stat_level_ups?.length)r.stat_level_ups.forEach((s,i)=>setTimeout(()=>{sndStatUp();toast('Attribute Level Up!',`${s.stat} reached Lv.${s.new_level}`)},400+i*600));
      if(r.leveled_up){setTimeout(()=>showLvl(r.new_level, r.new_title, r.new_unlocks),700);if(r.new_unlocks?.length){r.new_unlocks.forEach((u,i)=>setTimeout(()=>showUnlock(u),4500+i*2000))}}
      try{const chd=await api('/api/challenges');S.chal=chd.challenges||[];rChal()}catch(_){}
      if(r.completed_challenges?.length){r.completed_challenges.forEach((ch,i)=>setTimeout(()=>{showChallengeDone(ch);const elc=document.querySelector(`[data-chid="${ch.id}"]`);if(elc)elc.classList.add('chal-just')},900+i*1600))}
      if(r.loot_drop){const delay=r.completed_challenges?.length?(900+r.completed_challenges.length*1600+400):1500;setTimeout(()=>showLootDrop(r.loot_drop),delay)}
      if(r.new_achievements?.length){r.new_achievements.forEach((a,i)=>setTimeout(()=>{sndAch();toast('Achievement Unlocked!',`${a.icon||'\ud83c\udfc6'} ${a.title}`);starShower(10)},1200+i*700));const ad=await api('/api/achievements');S.ach=ad.achievements||[];rAch()}
      if(r.completed_bounties?.length){r.completed_bounties.forEach((b,i)=>setTimeout(()=>showBountyComplete(b),1600+i*1400));try{const bd=await api('/api/bounties');S.bounties=bd.bounties||[];rBounties()}catch(_){}}
      else{try{const bd=await api('/api/bounties');S.bounties=bd.bounties||[];rBounties()}catch(_){}}
      if(r.pet){S.pet=r.pet;rPet();if(r.pet_level_up){setTimeout(()=>{sndAch?.();toast('Companion Level Up!',`${r.pet.name||'Pet'} reached Lv.${r.pet.level}${r.pet_stage_up?` \u2014 evolved to ${r.pet.stage?.name}!`:''}`);if(r.pet_stage_up)confetti?.(60)},900)}}
      try{const ms=await api('/api/milestones');rMilestones(ms.milestones||[])}catch(_){}
      rTodayStats();
    }
  }catch(e){console.error(e)}
};

// Kick off gift check shortly after load, and every 5 minutes
setTimeout(checkGifts,2500);
setInterval(checkGifts,5*60*1000);

connectSSE();
