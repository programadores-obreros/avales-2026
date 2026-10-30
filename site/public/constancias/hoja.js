/* Formulario N°3 (CTA-T) — markup de la hoja + aplicación del diseño y de los datos.
   Lo usan index.html (impresión de todas las designaciones) y ajustar.html (Mesa de Registro).

   El "diseño" tiene el mismo formato que exporta "Copiar configuración":
   { tinta, letra, visibles, componentes:{ <pieza>: { posicion_mm | desplazamiento_mm, escala_pct, giro_grados } } }
   Las piezas con posición base (data-x/data-y) guardan posicion_mm absoluta; las piezas internas de
   un renglón guardan desplazamiento_mm. Las firmas de Lista 10 y de la Sub Delegada no forman parte
   de la hoja: se firman a mano en cada formulario. */
(function(){
  "use strict";

  var HTML = [
    '<div class="el franja" data-ck="franja" data-x="16" data-y="22"></div>',
    '<div class="el fecha" data-ck="fecha" data-x="23" data-y="28">ELECCIONES 3 DE NOVIEMBRE DE 2026</div>',
    '<div class="el numero" data-ck="numero" data-x="141" data-y="27">FORMULARIO N°3</div>',
    '<div class="el logo-ctat" data-ck="logoCtaT" data-x="25" data-y="37"><img src="assets/logo-cta-t-gris.png" alt="CTA"></div>',
    '<div class="el titulo" data-ck="titulo" data-x="16" data-y="88">DESIGNACION DE FISCAL de MESA</div>',
    '<div class="el renglon" data-ck="renglon1" data-x="22" data-y="114"><span class="pieza frag" data-ck="txtLocalidad">En la localidad de</span>',
    ' <span class="campo" style="width:62mm"><span class="pieza dato" data-ck="datoLocalidad" data-campo="localidad"></span></span><span class="pieza frag" data-ck="txtProvincia">provincia de</span>',
    ' <span class="campo" style="width:36mm"><span class="pieza dato" data-ck="datoProvincia" data-campo="provincia"></span></span><span class="pieza frag" data-ck="txtALos">a los</span></div>',
    '<div class="el renglon" data-ck="renglon2" data-x="22" data-y="127"><span class="pieza frag grande" data-ck="txtDia">3</span><span class="pieza frag" data-ck="txtMes">días del mes de noviembre</span><span class="pieza frag anio" data-ck="txtAnio">de <b>2026</b></span><span class="pieza frag" data-ck="txtDesigna">, se designa como</span>',
    ' <span class="campo" style="width:53mm"><span class="pieza dato" data-ck="datoRol" data-campo="rol"></span></span><span class="pieza frag" data-ck="txtDeLa">De la</span></div>',
    '<div class="el renglon" data-ck="renglon3" data-x="22" data-y="139"><span class="pieza frag" data-ck="txtMesa">mesa N°</span>',
    ' <span class="campo" style="width:16mm"><span class="pieza dato" data-ck="datoMesa" data-campo="mesa"></span></span><span class="pieza frag" data-ck="txtCro">al Cro./A</span>',
    ' <span class="campo" style="width:72mm"><span class="pieza dato" data-ck="datoNombre" data-campo="nombre"></span></span><span class="pieza frag" data-ck="txtDni">D.N.I.</span>',
    ' <span class="campo" style="width:28mm"><span class="pieza dato" data-ck="datoDni" data-campo="dni"></span></span></div>',
    '<div class="el firma" data-ck="firmaCappussi" data-x="74" data-y="200" style="width:60mm"><img data-firma="firma-cappussi" alt="Firma Cappussi"></div>',
    '<div class="el texto-firma" data-ck="aclaCappussi" data-x="70" data-y="215" style="width:70mm">Cappussi Luciana</div>',
    '<div class="el texto-firma" data-ck="cargoDelegada" data-x="70" data-y="220" style="width:70mm">Delegada Electoral CTA-T Pcia. de Bs. As.</div>',
    '<div class="el" data-ck="logoProv" data-x="80" data-y="230" style="width:50mm"><img src="assets/logo-cta-provincial.png" alt="CTA de los Trabajadores Provincia de Buenos Aires"></div>',
    '<div class="el firma" data-ck="firmaL6" data-x="140" data-y="186" style="width:48mm"><img data-firma="firma-apoderado-l6" alt="Firma apoderado Lista 6"></div>',
    '<div class="el linea-l6" data-ck="lineaL6" data-x="136" data-y="214"></div>',
    '<div class="el rotulo-l6" data-ck="rotuloL6" data-x="136" data-y="216">APODERADO DE LISTA 6</div>'
  ].join('\n');

  // Calibración hecha en la Mesa de Registro (30/10/2026). Es el diseño por defecto hasta que alguien
  // guarde otro desde "Ajustar diseño".
  var DISENO = {
    tinta:'negro',
    letra:{ fuente:'Reenie Beanie', size:20, color:'#1d3a8a', irreg:true },
    visibles:{ firmaCappussi:true, logoProv:true, firmaL6:true },
    componentes:{
      franja:{ posicion_mm:{ x:16, y:19.7 }, escala_pct:100, giro_grados:0 },
      fecha:{ posicion_mm:{ x:22.7, y:23.7 }, escala_pct:100, giro_grados:0 },
      numero:{ posicion_mm:{ x:136.4, y:25.7 }, escala_pct:100, giro_grados:0 },
      logoCtaT:{ posicion_mm:{ x:21.4, y:32.1 }, escala_pct:100, giro_grados:0 },
      renglon1:{ posicion_mm:{ x:23.6, y:113.7 }, escala_pct:100, giro_grados:0 },
      datoLocalidad:{ desplazamiento_mm:{ x:2.6, y:-1 }, escala_pct:126, giro_grados:0 },
      datoProvincia:{ desplazamiento_mm:{ x:0, y:0 }, escala_pct:126, giro_grados:0 },
      renglon2:{ posicion_mm:{ x:22, y:126.7 }, escala_pct:100, giro_grados:0 },
      renglon3:{ posicion_mm:{ x:22, y:139 }, escala_pct:98, giro_grados:0 },
      firmaCappussi:{ posicion_mm:{ x:68.1, y:190.1 }, escala_pct:87, giro_grados:0 },
      aclaCappussi:{ posicion_mm:{ x:63, y:203.4 }, escala_pct:100, giro_grados:0 },
      cargoDelegada:{ posicion_mm:{ x:66.7, y:210.1 }, escala_pct:100, giro_grados:0 },
      logoProv:{ posicion_mm:{ x:78.7, y:235.6 }, escala_pct:109, giro_grados:0 },
      firmaL6:{ posicion_mm:{ x:137.7, y:174.1 }, escala_pct:100, giro_grados:0 },
      lineaL6:{ posicion_mm:{ x:136, y:204.1 }, escala_pct:100, giro_grados:0 },
      rotuloL6:{ posicion_mm:{ x:136.7, y:212.4 }, escala_pct:100, giro_grados:0 }
    }
  };

  var CAMPOS_FIJOS = { localidad:'La Matanza', provincia:'Bs. As.', rol:'Fiscal Lista 6' };
  var FUENTES = ['Reenie Beanie','Shadows Into Light','Indie Flower','Covered By Your Grace','Caveat'];

  // pseudo-aleatorio estable: la misma letra en la misma posición siempre se tuerce igual
  function rnd(seed){ var x = Math.sin(seed * 12.9898) * 43758.5453; return x - Math.floor(x); }

  // diseño (formato export) → deltas {dx,dy,scale,rot} por pieza, usando la posición base del markup
  function deltas(root, diseno){
    var out = {}, comp = (diseno && diseno.componentes) || {};
    root.querySelectorAll('.el, .pieza').forEach(function(el){
      var k = el.dataset.ck, c = comp[k], d = { dx:0, dy:0, scale:100, rot:0 };
      if(c){
        if(c.posicion_mm && el.dataset.x){ d.dx = c.posicion_mm.x - el.dataset.x; d.dy = c.posicion_mm.y - el.dataset.y; }
        else if(c.desplazamiento_mm){ d.dx = c.desplazamiento_mm.x; d.dy = c.desplazamiento_mm.y; }
        d.scale = c.escala_pct; d.rot = c.giro_grados;
      }
      out[k] = d;
    });
    return out;
  }

  function aplicarPieza(el, d, visibles){
    if(el.dataset.x){ el.style.left = el.dataset.x + 'mm'; el.style.top = el.dataset.y + 'mm'; }
    el.style.transform = 'translate(' + d.dx + 'mm,' + d.dy + 'mm) rotate(' + d.rot + 'deg) scale(' + (d.scale/100) + ')';
    if(visibles && el.dataset.ck in visibles) el.classList.toggle('oculto', !visibles[el.dataset.ck]);
  }

  function aplicarTinta(root, tinta){
    root.querySelectorAll('[data-firma]').forEach(function(img){ img.src = 'assets/' + img.dataset.firma + '-' + (tinta || 'negro') + '.png'; });
  }

  function aplicarCampos(root, campos, letra){
    var L = letra || DISENO.letra;
    root.querySelectorAll('[data-campo]').forEach(function(s, fi){
      var txt = (campos && campos[s.dataset.campo]) || '';
      var mano = L.fuente !== 'imprenta';
      s.classList.toggle('manuscrita', mano);
      s.style.fontFamily = mano ? "'" + L.fuente + "', cursive" : '';
      s.style.fontSize = mano ? L.size + 'pt' : '';
      s.style.color = L.color;
      if(!mano || !L.irreg){ s.textContent = txt; return; }
      s.textContent = '';
      Array.from(txt).forEach(function(c, i){
        var sp = document.createElement('span'); sp.className = 'ch'; sp.textContent = c;
        var a = rnd(fi * 97 + i * 7 + c.charCodeAt(0)), b = rnd(fi * 31 + i * 13 + 5);
        sp.style.transform = 'translateY(' + ((a - .5) * .7).toFixed(2) + 'mm) rotate(' + ((b - .5) * 7).toFixed(1) + 'deg)';
        s.appendChild(sp);
      });
    });
  }

  // arma una hoja completa lista para imprimir
  function crear(diseno, campos){
    var d = diseno || DISENO;
    var hoja = document.createElement('div'); hoja.className = 'hoja'; hoja.innerHTML = HTML;
    var dl = deltas(hoja, d);
    hoja.querySelectorAll('.el, .pieza').forEach(function(el){ aplicarPieza(el, dl[el.dataset.ck], d.visibles); });
    aplicarTinta(hoja, d.tinta);
    aplicarCampos(hoja, campos, d.letra);
    return hoja;
  }

  window.Hoja = { HTML:HTML, DISENO:DISENO, CAMPOS_FIJOS:CAMPOS_FIJOS, FUENTES:FUENTES,
    deltas:deltas, aplicarPieza:aplicarPieza, aplicarTinta:aplicarTinta, aplicarCampos:aplicarCampos, crear:crear };
})();
