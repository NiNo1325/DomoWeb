/* Zone de questions (Cusdis) — chargeur partagé par tous les articles.
   Remplacez APP_ID par l'App ID obtenu sur https://cusdis.com (Dashboard →
   votre projet). Tant que la valeur reste le repère « VOTRE_APP_ID », la
   zone affiche un message d'attente au lieu d'un widget en erreur. */
(function () {
  var APP_ID = "3f88c02e-30f2-4dae-b47c-7d0dc4640438"; // App ID Cusdis (projet NicoDomo)

  var el = document.getElementById("cusdis_thread");
  if (!el) return;

  var configured = APP_ID && APP_ID.indexOf("VOTRE_APP_ID") === -1;
  if (!configured) {
    el.innerHTML = '<p class="qa-pending">Zone de questions bientôt disponible.</p>';
    return;
  }

  el.setAttribute("data-host", "https://cusdis.com");
  el.setAttribute("data-app-id", APP_ID);

  var s = document.createElement("script");
  s.async = true;
  s.defer = true;
  s.src = "https://cusdis.com/js/cusdis.es.js";
  document.body.appendChild(s);
})();
