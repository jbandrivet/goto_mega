// Ciel étoilé du site : étoiles en pixels sur trois plans qui défilent lentement (parallaxe), scintillement,
// étoiles filantes de temps en temps. Immobile si le visiteur a demandé moins d'animations.
(function () {
  const ciel = document.getElementById("ciel");
  if (!ciel) return;
  const ctx = ciel.getContext("2d");
  const calme = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const couleurs = ["#ffffff", "#cfe8ff", "#ffe9c4", "#a8c8ff", "#ffd6f5"];
  const PX = 2;                    // une étoile = un carré de 2 × 2 pixels d'écran au moins
  let etoiles = [], filantes = [], w = 0, h = 0, t0 = performance.now();

  function semer() {
    w = ciel.width = Math.ceil(window.innerWidth / PX);
    h = ciel.height = Math.ceil(window.innerHeight / PX);
    const n = Math.min(900, Math.round(w * h / 260));
    etoiles = [];
    for (let i = 0; i < n; i++) {
      const plan = Math.random() < 0.6 ? 0 : Math.random() < 0.75 ? 1 : 2;      // loin, moyen, proche
      etoiles.push({
        x: Math.random() * w, y: Math.random() * h, plan,
        taille: plan === 2 && Math.random() < 0.3 ? 2 : 1,
        vitesse: [0.6, 1.4, 3.0][plan],                                     // dérive : pixels par dizaine de secondes
        couleur: couleurs[Math.floor(Math.random() * couleurs.length)],
        phase: Math.random() * Math.PI * 2, freq: 0.5 + Math.random() * 2.5,
        eclat: [0.45, 0.7, 1][plan],
      });
    }
  }

  function filante() {
    filantes.push({ x: Math.random() * w * 0.8, y: Math.random() * h * 0.4, vx: 1.6 + Math.random() * 1.2,
                    vy: 0.7 + Math.random() * 0.6, vie: 1 });
  }

  function dessiner(t) {
    const s = (t - t0) / 1000;
    ctx.clearRect(0, 0, w, h);
    for (const e of etoiles) {
      const x = calme ? e.x : (e.x + s * e.vitesse * 0.1) % w;
      const a = calme ? e.eclat : e.eclat * (0.65 + 0.35 * Math.sin(e.phase + s * e.freq));
      ctx.globalAlpha = a;
      ctx.fillStyle = e.couleur;
      ctx.fillRect(Math.floor(x), Math.floor(e.y), e.taille, e.taille);
      if (e.taille === 2 && a > 0.85) {                                      // petite croix des plus brillantes
        ctx.globalAlpha = a * 0.35;
        ctx.fillRect(Math.floor(x) - 1, Math.floor(e.y), 4, 2);
        ctx.fillRect(Math.floor(x), Math.floor(e.y) - 1, 2, 4);
      }
    }
    if (!calme) {
      if (Math.random() < 0.004) filante();
      filantes = filantes.filter(f => f.vie > 0);
      for (const f of filantes) {
        for (let k = 0; k < 14; k++) {
          ctx.globalAlpha = f.vie * (1 - k / 14);
          ctx.fillStyle = k < 2 ? "#ffffff" : "#9fe8ff";
          ctx.fillRect(Math.floor(f.x - f.vx * k), Math.floor(f.y - f.vy * k), 1, 1);
        }
        f.x += f.vx; f.y += f.vy; f.vie -= 0.012;
      }
    }
    ctx.globalAlpha = 1;
    if (!calme) requestAnimationFrame(dessiner);
  }

  semer();
  window.addEventListener("resize", () => { semer(); if (calme) dessiner(performance.now()); });
  requestAnimationFrame(dessiner);
})();
