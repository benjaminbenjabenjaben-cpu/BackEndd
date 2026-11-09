/* Gráficos de lectura: los datos se reciben del ORM mediante json_script. */
(() => {
  const NS = 'http://www.w3.org/2000/svg';
  const colores = ['#1476ff', '#22c78d', '#9562eb', '#f2c52b', '#56b6d8', '#fb8c56'];
  const leer = id => JSON.parse(document.getElementById(id).textContent);
  function elemento(svg, nombre, atributos, texto) {
    const nodo = document.createElementNS(NS, nombre);
    Object.entries(atributos).forEach(([clave, valor]) => nodo.setAttribute(clave, valor));
    if (texto !== undefined) nodo.textContent = texto;
    svg.appendChild(nodo);
    return nodo;
  }
  function texto(svg, x, y, valor, extras = {}) {
    return elemento(svg, 'text', {x, y, fill: '#52647d', 'font-size': 11, 'font-family': 'Arial, sans-serif', ...extras}, valor);
  }
  function vacio(svg, mensaje, ancho, alto) {
    texto(svg, ancho / 2, alto / 2, mensaje, {'text-anchor': 'middle', fill: '#7a8ba0'});
  }
  function ejes(svg, ancho, alto, maximo, margen) {
    for (let i = 0; i <= 4; i++) {
      const y = margen.arriba + (alto - margen.arriba - margen.abajo) * i / 4;
      elemento(svg, 'line', {x1: margen.izquierda, x2: ancho - margen.derecha, y1: y, y2: y, stroke: '#e7edf5', 'stroke-width': 1});
      texto(svg, margen.izquierda - 8, y + 4, Math.round(maximo * (4 - i) / 4), {'text-anchor': 'end'});
    }
  }
  function donut() {
    const svg = document.getElementById('grafico-estados');
    const datos = leer('datos-estados');
    const total = datos.reduce((suma, fila) => suma + fila.total, 0);
    const radio = 67, largo = 2 * Math.PI * radio;
    elemento(svg, 'circle', {cx: 95, cy: 95, r: radio, fill: 'none', stroke: '#eaf0f8', 'stroke-width': 29});
    let acumulado = 0;
    datos.forEach(fila => {
      if (!total || !fila.total) return;
      const segmento = elemento(svg, 'circle', {
        cx: 95, cy: 95, r: radio, fill: 'none', stroke: fila.color,
        'stroke-width': 29, 'stroke-dasharray': `${fila.total / total * largo} ${largo}`,
        'stroke-dashoffset': -acumulado / total * largo, transform: 'rotate(-90 95 95)'
      });
      elemento(segmento, 'title', {}, `${fila.nombre}: ${fila.total} (${Math.round(fila.total / total * 100)} %)`);
      acumulado += fila.total;
    });
    texto(svg, 95, 96, total, {'text-anchor': 'middle', fill: '#0e2140', 'font-size': 28, 'font-weight': 700});
    texto(svg, 95, 115, 'Viajes', {'text-anchor': 'middle', fill: '#0e2140', 'font-size': 12, 'font-weight': 600});
    svg.setAttribute('aria-label', `Total de viajes: ${total}. ${datos.map(fila => `${fila.nombre}: ${fila.total}`).join('. ')}`);
  }
  function barras() {
    const svg = document.getElementById('grafico-tipos');
    const datos = leer('datos-tipos');
    if (!datos.length || !datos.some(fila => fila.total)) return vacio(svg, 'No hay viajes en este período', 380, 220);
    const ancho = Math.max(380, datos.length * 72), alto = 220, margen = {arriba: 28, abajo: 44, izquierda: 34, derecha: 8};
    svg.setAttribute('viewBox', `0 0 ${ancho} ${alto}`);
    if (datos.length > 6) svg.style.minWidth = `${ancho}px`;
    const maximo = Math.max(4, Math.ceil(Math.max(...datos.map(fila => fila.total)) / 4) * 4);
    const espacio = (ancho - margen.izquierda - margen.derecha) / datos.length;
    const anchoBarra = Math.min(55, espacio * .64);
    ejes(svg, ancho, alto, maximo, margen);
    datos.forEach((fila, i) => {
      const altoBarra = fila.total / maximo * (alto - margen.arriba - margen.abajo);
      const x = margen.izquierda + espacio * i + (espacio - anchoBarra) / 2;
      const y = alto - margen.abajo - altoBarra;
      const barra = elemento(svg, 'rect', {x, y, width: anchoBarra, height: altoBarra, rx: 4, fill: colores[i % colores.length]});
      elemento(barra, 'title', {}, `${fila.nombre}: ${fila.total} viajes`);
      texto(svg, x + anchoBarra / 2, y - 8, fila.total, {'text-anchor': 'middle', fill: '#142744', 'font-size': 12, 'font-weight': 700});
      const nombre = fila.nombre.length > 13 ? fila.nombre.slice(0, 11) + '…' : fila.nombre;
      const etiqueta = texto(svg, x + anchoBarra / 2, alto - 19, nombre, {'text-anchor': 'middle', 'font-size': 10});
      elemento(etiqueta, 'title', {}, fila.nombre);
    });
    svg.setAttribute('aria-label', datos.map(fila => `${fila.nombre}: ${fila.total} viajes`).join('. '));
  }
  function linea() {
    const svg = document.getElementById('grafico-evolucion');
    const datos = leer('datos-evolucion');
    if (!datos.length) return vacio(svg, 'No hay viajes en este período', 460, 220);
    const ancho = 460, alto = 220, margen = {arriba: 28, abajo: 44, izquierda: 32, derecha: 12};
    const maximo = Math.max(4, Math.ceil(Math.max(...datos.map(fila => fila.total)) / 4) * 4);
    const fondo = alto - margen.abajo;
    ejes(svg, ancho, alto, maximo, margen);
    const puntos = datos.map((fila, i) => [
      margen.izquierda + (ancho - margen.izquierda - margen.derecha) * i / Math.max(1, datos.length - 1),
      fondo - fila.total / maximo * (alto - margen.arriba - margen.abajo)
    ]);
    const defs = elemento(svg, 'defs', {});
    const degradado = elemento(defs, 'linearGradient', {id: 'area-viajes', x1: 0, y1: 0, x2: 0, y2: 1});
    elemento(degradado, 'stop', {offset: '0%', 'stop-color': '#237bfa', 'stop-opacity': .23});
    elemento(degradado, 'stop', {offset: '100%', 'stop-color': '#237bfa', 'stop-opacity': .02});
    elemento(svg, 'polygon', {points: `${puntos[0][0]},${fondo} ${puntos.map(p => p.join(',')).join(' ')} ${puntos[puntos.length - 1][0]},${fondo}`, fill: 'url(#area-viajes)'});
    elemento(svg, 'polyline', {points: puntos.map(p => p.join(',')).join(' '), fill: 'none', stroke: '#1476ff', 'stroke-width': 2.4, 'stroke-linejoin': 'round'});
    const etiquetas = new Set([0, 1, 2, 3, 4, 5].map(i => Math.round(i * (datos.length - 1) / 5)));
    puntos.forEach(([x, y], i) => {
      if (datos.length <= 31 || etiquetas.has(i)) {
        const punto = elemento(svg, 'circle', {cx: x, cy: y, r: 2.8, fill: 'white', stroke: '#1476ff', 'stroke-width': 1.8});
        elemento(punto, 'title', {}, `${datos[i].label}: ${datos[i].total} viajes`);
      }
      if (etiquetas.has(i)) texto(svg, x, alto - 19, datos[i].label, {'text-anchor': i === 0 ? 'start' : i === datos.length - 1 ? 'end' : 'middle', 'font-size': 10});
    });
    svg.setAttribute('aria-label', datos.map(fila => `${fila.label}: ${fila.total} viajes`).join('. '));
  }
  donut();
  barras();
  linea();
})();
