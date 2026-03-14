# Reverso — Valores Cerrados (14/03/2026)

## Hoja
- Formato: Oficio 215.9 x 355.6 mm
- Margen superior (Y inicio): **5mm**
- Margen izquierdo: 7.1mm, derecho: 4.7mm, inferior: 1.0mm

## Anclas de referencia (posiciones Y verificadas del PDF generado)

```
Y=0mm     ┌─────────────────────────────────┐
Y=5mm     │  MARGEN SUPERIOR                │
          │                                 │
Y≈7mm     │  ┌── HEADER IMAGEN ──────────┐  │  ANCLA-R1
          │  └───────────────────────────┘  │
Y≈43mm    │                                 │
          │  ┌── CONGRESALES 30-49 ──────┐  │  ANCLA-R2
          │  │  (20 filas, sin header)   │  │
          │  └───────────────────────────┘  │
Y≈145mm   │                                 │
          │  Art. 53 - Estatuto SUTEBA      │  ANCLA-R3
          │  (2 columnas)                   │
Y≈159mm   │                                 │
          │  ── gap 5mm ──                  │
Y≈164mm   │  COMISIÓN REVISORA DE CUENTAS   │  ANCLA-R4
          │  ┌── tabla 4 filas ──────────┐  │
          │  └───────────────────────────┘  │
Y≈188mm   │                                 │
          │  ── gap 8mm ──                  │
Y=195.6mm │  ┌── TABLA FIRMAS ──────────┐  │  ANCLA-R5 *** INAMOVIBLE ***
          │  │  (23 filas + header)      │  │
          │  │  192mm centrada           │  │
          │  └───────────────────────────┘  │
Y≈338mm   │                                 │
Y=355.6mm └─────────────────────────────────┘
```

## Zona R1: Header imagen
- Y inicio: 5mm
- Imagen: header_avales3_trimmed.png (781x143px)
- Alto: imgW * (143/781) - 3mm ≈ 35.4mm
- Gap después: 2mm (drawHeaderImage)
- **SIN texto de avales** (solo imagen)

## Zona R2: Congresales 30-49
- Y inicio: ~43mm (después de header)
- **SIN header de tabla** (continúa del anverso)
- 20 filas de datos
- Fuente: Times 12pt
- Alto real fila: ~5.1mm (12pt + padding 0.1+0.1)
- Columnas: 47.6, 52.0, 52.0, 46.0 mm
- minCellHeight: 4.1mm (la fuente manda)

## Zona R3: Art. 53
- Y inicio: finalY de congresales (~145mm)
- Fuente: Times 10pt
- 2 columnas:
  - Izquierda: "Art. 53 - Estatuto SUTEBA" + bullet 1 + bullet 2
  - Derecha: bullet 3 ("Se elegirán...")
- Alto total: 14mm

## Zona R4: Comisión Revisora de Cuentas
- Gap antes: 5mm
- Título: Arial 11pt Bold, subrayado, centrado (4mm)
- Tabla: 4 filas (1 header + 3 datos)
- Fuente: Helvetica 11pt
- Columnas: 46.1, 50.3, 50.4, 50.4 mm
- minCellHeight: 4.1mm
- Fin de tabla: ~188.5mm

## Zona R5: Tabla de Firmas *** ANCLA INAMOVIBLE ***
- Gap antes: **8mm** desde Comisión Revisora
- **Y inicio medido del PDF completo: 195.6mm**
- Y inicio modo solo_firmas: **195.6mm** (mismo valor)
- **192mm de ancho, CENTRADA**
  - Margen izquierdo: 13.2mm
  - Margen derecho: 10.8mm
- 24 filas (1 header + 23 datos)
- Fuente: Helvetica 14pt
- Alto real fila: ~5.14mm (14pt + padding 0.1+0.1)
- minCellHeight: 4.1mm (la fuente de 14pt manda)
- Columnas: 8.0, 34.7, 83.1, 25.3, 40.9 mm (total 192mm)
- Headers: Nº, DOCUMENTO, APELLIDO/S Y NOMBRES, ESCUELA, FIRMA
- Fin de tabla: ~337.6mm
- **ESTA TABLA NO SE MUEVE. Si algo cambia arriba, se ajusta lo de arriba, NUNCA las firmas.**

## Modos de exportación

| Modo | Pág 1 | Pág 2 | Firmas Y |
|---|---|---|---|
| **completo** | anverso completo | reverso completo | 195.6mm |
| **sin_firmas** | anverso completo | reverso sin firmas | — |
| **solo_firmas** | en blanco | solo tabla firmas | 195.6mm |

### Verificación de alineación (14/03/2026)
- Completo:    Y = 195.6mm
- Solo firmas: Y = 194.6mm
- Diferencia:  **1.0mm** (aceptable, pendiente ajuste fino con impresión real)

## Regla de oro
> Si se necesita ganar espacio en el reverso, se achican congresales, art.53 o comisión.
> La tabla de firmas es INTOCABLE en posición y tamaño.
> Cualquier cambio requiere re-verificar alineación completo vs solo_firmas.
