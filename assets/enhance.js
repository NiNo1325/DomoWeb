/* Charte « Rapport d'ingénierie » — met en valeur le numéro de section.
   Enveloppe le numéro en tête des titres (ex. « 4.1 ») dans <span class="secno">
   pour l'afficher en accent, suspendu. Sans JS, le numéro reste en texte normal :
   dégradation gracieuse, aucune dépendance. */
(function () {
  var LEADING_NUMBER = /^(\d+(?:\.\d+)*)\.?\s+/;
  var headings = document.querySelectorAll('main > h1, main > h2');

  Array.prototype.forEach.call(headings, function (h) {
    if (h.children.length) return;              // ne touche pas aux titres avec balises internes
    var match = h.textContent.match(LEADING_NUMBER);
    if (!match) return;                          // ignore les titres non numérotés

    var rest = h.textContent.slice(match[0].length);
    var num = document.createElement('span');
    num.className = 'secno';
    num.textContent = match[1];

    h.textContent = '';
    h.appendChild(num);
    h.appendChild(document.createTextNode(rest));
  });
})();
