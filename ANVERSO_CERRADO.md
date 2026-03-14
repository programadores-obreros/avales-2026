# Anverso — Valores Cerrados (14/03/2026)

## Hoja
- Formato: Oficio 215.9 x 355.6 mm
- Margen superior (Y inicio): **5mm**
- Margen izquierdo: 7.1mm, derecho: 4.7mm, inferior: 1.0mm

## Header
- Imagen: `header_avales3_trimmed.png` (781x143px)
- Alto renderizado: imgW * (143/781) - 3mm ≈ 35.4mm
- Gap después de imagen: 2mm (en drawHeaderImage)

## Texto de avales
- Separación header → texto: **5mm**
- Fuente: Helvetica 12pt
- Ancho texto: AW - 4mm (margen derecho extra)
- Justificado, nombre de lista en bold
- Interlineado: 5mm

## Tabla Consejo Ejecutivo
- Gap antes: 3mm (finalY + 3)
- 11 filas x 6 columnas
- Header: fontSize 9.6pt bold, centrado H+V, minCellHeight 4.1mm
  - Columnas ESCUELA en header: fontSize 8pt (via didParseCell)
- Datos: fontSize 9pt, centrado V, minCellHeight 4.1mm
- Columnas: Secretaría 29.0, Nombre 52.15, Escuela 17.5 (x2 lados)
- Secretarías: fontSize 8pt bold
- Escuela datos: fontSize 8pt
- cellPadding: top 0.1, right 1, bottom 0.1, left 1

## Título VOCALES
- Gap antes: 5mm (finalY + 5)
- Arial 11pt Bold, subrayado, centrado
- Alto del título: 4mm (drawSectionTitle retorna y+4)
- Gap después: 1mm

## Tabla Vocales
- 8 filas x 4 columnas (7 titulares + 8 suplentes)
- Header: fontSize 11pt Helvetica bold, minCellHeight 4.1mm
- Datos: fontSize 12pt Times, minCellHeight 4.1mm
- Alto real de fila: ~4.4mm (12pt texto + 0.2mm padding)
- Columnas: 47.2, 51.6, 51.5, 47.0 mm
- Fila 8 (index 7): celdas izquierdas (cols 0,1) sin bordes

## Título CONGRESALES A SUTEBA
- Gap antes: 5mm (finalY + 5)
- Arial 11pt Bold, subrayado, centrado
- Gap después: 1mm

## Tabla Congresales (1-29)
- 30 filas (1 header + 29 datos)
- Header: fontSize 11pt Helvetica bold, minCellHeight 4.1mm
- Datos: fontSize 12pt Times, minCellHeight 4.1mm
- Columnas: 47.6, 52.0, 52.0, 46.0 mm
- **ANVERSO TERMINA EN FILA 29**

## Escuela
- Formato truncado: "0-069-MS-0140" → "MS-0140" (función shortEsc)
- "JUBILADO/A" queda igual

## Defaults globales (getTableDefaults)
- theme: grid
- cellPadding: top 0.1, right 1, bottom 0.1, left 1
- lineColor: negro, lineWidth: 0.25mm
- font: helvetica
- Bordes: grid negro 0.25mm
- Sin fondo en headers (fillColor: false)
