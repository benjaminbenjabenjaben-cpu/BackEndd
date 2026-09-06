"use strict";
// El portal funciona sin JavaScript. Este atajo mejora la búsqueda del panel.
document.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
    const search =
      document.getElementById("buscar") || document.getElementById("id_codigo");
    if (search) {
      event.preventDefault();
      search.focus();
    }
  }
});
