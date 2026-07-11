/* Amélioration du menu déroulant natif <details.nav-dd> :
   fermeture au clic en dehors et à la touche Échap.
   Sans ce script, le menu s'ouvre/ferme quand même via le clic sur « Publications ». */
(function () {
  function closeAll(except) {
    document.querySelectorAll("details.nav-dd[open]").forEach(function (d) {
      if (d !== except) d.removeAttribute("open");
    });
  }
  document.addEventListener("click", function (e) {
    var open = e.target.closest ? e.target.closest("details.nav-dd[open]") : null;
    closeAll(open);
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeAll(null);
  });
})();
