# Set de preguntas doradas

Checklist manual de evaluación para el MVP (sin RAGAS todavía — ver roadmap en el README). 20 preguntas reales probadas contra el stack completo corriendo en Docker (Ollama `qwen2.5:3b-instruct` + `nomic-embed-text`, Chroma, umbral de relevancia 0.40), cubriendo las 4 áreas de la KB, casos límite diseñados a propósito, el guardrail anti-alucinación y la memoria de conversación.

Resultado: **16/20 correctas**, 3 con fallas reales de generación (documentadas abajo, no en retrieval), 1 respuesta correcta pero poco útil.

## Envíos

| # | Pregunta | Resultado |
|---|---|---|
| 1 | ¿Cuánto tarda en llegar mi pedido? | ⚠️ **Falla** — ver "Hallazgo 1" abajo |
| 2 | ¿Tienen envío express? | ✅ Correcta, cita "Costos de envío" |
| 3 | ¿Envían a otros países? | ✅ Correcta ("No, no realizamos envíos internacionales") |
| — | Hacen envíos a todo el país | ✅ Correcta tras el fix de overlap — ver "Hallazgo 2" |

## Devoluciones y garantía

| # | Pregunta | Resultado |
|---|---|---|
| 4 | ¿Puedo devolver algo que no me gustó? | ✅ Correcta, menciona plazo de 15 días y excepción por defecto |
| 5 | ¿Puedo devolver un producto que compré en oferta? | ✅ Correcta, aclara reembolso por valor pagado con descuento |
| 6 | Mi producto llegó defectuoso, ¿qué hago? | ✅ Correcta, menciona garantía de 3 meses |
| 7 | ¿Cuánto tardan en devolverme el dinero? | ✅ Correcta, distingue tarjeta (5-10 días) vs. transferencia (3-5 días) |

## Pagos

| # | Pregunta | Resultado |
|---|---|---|
| 8 | ¿Qué métodos de pago aceptan? | ⚠️ **Falla** — ver "Hallazgo 3" abajo |
| 9 | ¿Puedo pagar contra entrega? | ✅ Correcta, con monto y ciudades correctas |
| 10 | Me cobraron dos veces, ¿qué hago? | ⚠️ **Falla** (mismo patrón que #8) — ver "Hallazgo 3" |
| — | ¿Puedo pagar en cuotas? | ⚠️ **Falla reproducible** — ver "Hallazgo 4" |

## Seguimiento de pedido

| # | Pregunta | Resultado |
|---|---|---|
| 11 | ¿Cómo sé en qué estado va mi pedido? | ✅ Correcta |
| 12 | Mi pedido llegó incompleto, ¿qué hago? | 🟡 Responde con la política de "no ha llegado" en vez de "llegó incompleto/dañado" — caso límite diseñado a propósito, retrieval no distingue perfecto entre ambas secciones |
| 13 | Ya pasó la fecha de entrega y no me ha llegado nada | 🟡 Correcta pero vaga (remite a otra sección sin dar el detalle) |
| 14 | ¿Puedo cambiar la dirección de entrega? | ✅ Correcta |
| 15 | ¿Puedo cancelar mi pedido? | ✅ Correcta |

## Guardrail (fuera de dominio — no debe inventar)

| # | Pregunta | Resultado |
|---|---|---|
| 16 | ¿Cuál es la capital de Francia? | ✅ Responde el fallback fijo, no alucina |
| 17 | ¿Quién ganó el mundial de fútbol en 2022? | ✅ Responde el fallback fijo |
| 18 | Recomiéndame una receta de pasta | ✅ Responde el fallback fijo |

## Memoria de conversación

| # | Caso | Resultado |
|---|---|---|
| 19 | "¿cuánto cuesta el envío estándar?" → "¿y el envío express?" (mismo chat) | ✅ Resuelve el seguimiento usando el turno anterior |
| 20 | Reiniciar el contenedor a mitad de conversación | ✅ El historial persiste (SQLite en volumen, no en memoria del proceso) |

---

## Hallazgos documentados

Cuatro problemas reales se encontraron probando conversaciones de verdad (Telegram y el widget web), no preguntas inventadas en frío. Se documentan con evidencia en vez de solo reportar "funciona bien":

### Hallazgo 1 — Un embedding puede fallar por completo con una pregunta natural

La sección "Tiempos de entrega" responde exactamente la pregunta #1, pero con la frase literal del título ("tiempo de entrega") el retrieval la encuentra en el puesto #2 (distancia 0.3162). Con la pregunta tal como la haría un cliente real ("¿Cuánto tarda en llegar mi pedido?"), la misma sección cae al puesto **#19 de 23** (distancia 0.4739) — muy por fuera de cualquier top-k razonable. Es una limitación del modelo de embeddings (`nomic-embed-text`) con paráfrasis en español, no un bug de nuestro código. Ver "Limitaciones conocidas" en el README.

### Hallazgo 2 — Overlap de chunking que invertía negaciones (ya corregido)

La primera versión del chunking agregaba el último párrafo de la sección anterior como "overlap". Acotarlo a 25 palabras (para evitar que dominara el embedding siguiente) terminó cortando justo la palabra "No" de una negación real: "**No** tiene costo adicional" se volvía "tiene costo adicional", invirtiendo una política real de pago contra entrega y contaminando el chunk de "Pagos en cuotas". Se corrigió quitando el overlap por completo — cada chunk es ahora exactamente su propia sección.

### Hallazgo 3 — "Lost in the middle": el modelo no usa información que sí tiene

Con la pregunta #8 ("¿Qué métodos de pago aceptan?"), el chunk correcto ("Métodos de pago aceptados") **sí llega al prompt del LLM** — confirmado imprimiendo el prompt exacto enviado — como el 4° de 5 bloques de contexto. Aun así, el modelo (`qwen2.5:3b-instruct`) respondió "el contexto no especifica los métodos de pago" en 5 de 5 intentos repetidos. Es el fenómeno de *lost in the middle* bien documentado en la literatura de LLMs: con varios chunks sobre un tema similar ("Seguridad de los pagos", "Problemas con el pago") rodeando al correcto, un modelo de 3B parámetros pierde la información aunque esté presente. La pregunta #10 (cobro duplicado) mostró el mismo patrón. **No es un problema de retrieval** — el retrieval fue verificado determinista y correcto en los 5 intentos.

### Hallazgo 4 — Alucinación por combinación de datos de dos secciones distintas

Con "¿puedo pagar en cuotas?", el modelo inventó de forma reproducible (3/3 intentos) una condición que no existe: que el pago en cuotas "depende del monto del pedido o de que la ciudad esté en la lista". Esa condición sí existe en la KB, pero para "Pago contra entrega" — una sección completamente distinta, que ni siquiera estaba en el contexto recuperado para esta pregunta. El modelo combinó un patrón ("monto/ciudad = restricción de pago") visto en otra parte del entrenamiento o de la conversación con el tema correcto, generando una regla de negocio falsa pero plausible.

**Conclusión de los 4 hallazgos:** con el pipeline de retrieval ya validado como determinista y correcto (confirmado imprimiendo prompts exactos y repitiendo pruebas), el cuello de botella actual es la capacidad del modelo de 3B parámetros, no la ingeniería de RAG. Justifica los ítems de roadmap: modelo más grande (`qwen2.5:7b-instruct` / `llama3.1:8b-instruct` si hay más RAM), reranking, y evaluación sistemática con RAGAS en vez de descubrir estos casos por accidente.
