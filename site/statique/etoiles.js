// Petites étoiles qui suivent la souris. Rien sur écran tactile ;
// rien non plus (et texte qui défile arrêté) si le visiteur a demandé moins d'animations.
(function () {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    document.querySelectorAll("marquee").forEach(m => m.stop && m.stop());
    return;
  }
  if (!window.matchMedia("(pointer: fine)").matches) return;
  const couleurs = ["#ffff00", "#ffffff", "#00ffff", "#ff88ff", "#ffaa00"];
  let dernier = 0;
  document.addEventListener("mousemove", e => {
    const t = performance.now();
    if (t - dernier < 45) return;
    dernier = t;
    const p = document.createElement("span");
    p.className = "paillette";
    p.textContent = Math.random() < 0.5 ? "★" : "✦";
    p.style.left = (e.pageX + 6) + "px";
    p.style.top = (e.pageY + 6) + "px";
    p.style.color = couleurs[Math.floor(Math.random() * couleurs.length)];
    document.body.appendChild(p);
    setTimeout(() => p.remove(), 900);
  });
})();
