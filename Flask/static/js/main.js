/* ── Password toggle ─────────────────────────────────────────────────────── */
document.querySelectorAll('.pw-toggle').forEach(btn => {
  btn.addEventListener('click', () => {
    const targetId = btn.dataset.target;
    const input = document.getElementById(targetId);
    if (!input) return;
    const isHidden = input.type === 'password';
    input.type = isHidden ? 'text' : 'password';
    btn.querySelector('svg').style.opacity = isHidden ? '1' : '0.5';
  });
});

/* ── Role card keyboard support ─────────────────────────────────────────── */
document.querySelectorAll('.role-card').forEach(card => {
  card.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      card.querySelector('input[type="radio"]').checked = true;
    }
  });
  card.setAttribute('tabindex', '0');
});

/* ── Flash auto-dismiss ──────────────────────────────────────────────────── */
document.querySelectorAll('.flash').forEach(flash => {
  setTimeout(() => {
    flash.style.transition = 'opacity .4s ease, transform .4s ease';
    flash.style.opacity    = '0';
    flash.style.transform  = 'translateX(12px)';
    setTimeout(() => flash.remove(), 400);
  }, 4500);
});

/* ── Form submit animation ───────────────────────────────────────────────── */
document.querySelectorAll('form.form').forEach(form => {
  form.addEventListener('submit', () => {
    const btn = form.querySelector('.btn--primary');
    if (!btn) return;
    btn.style.opacity = '0.7';
    btn.style.pointerEvents = 'none';
    btn.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="16" class="spin">
        <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4"/>
      </svg>
      Processing…
    `;
  });
});

/* ── Inject spin keyframe ────────────────────────────────────────────────── */
const style = document.createElement('style');
style.textContent = `.spin { animation: spin .7s linear infinite; } @keyframes spin { to { transform: rotate(360deg); } }`;
document.head.appendChild(style);