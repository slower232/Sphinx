# Sphinx

Plataforma educativa **gratuita** para jóvenes con barreras de acceso a la escuela. Complementa (no reemplaza) a la escuela y a los docentes.
Contribuye al ODS 4 (educación de calidad). Idioma inicial: español.

**Estado: primera versión funcional ejecutable localmente. No está desplegada en internet** (ver "Pendiente").

## 1. Decisión de arquitectura

| Opción | Pros | Contras |
|---|---|---|
| A. **Flask + SQLite + plantillas Jinja (elegida)** | Una sola pieza que entender, sin paso de compilación, páginas ligeras para teléfonos modestos, costo casi cero, el HTML funciona incluso sin JavaScript | SQLite escribe de a una conexión (basta para miles de usuarios; después se migra) |
| B. React + FastAPI + PostgreSQL | Muy escalable, SPA fluida | Dos proyectos, build, más JavaScript pesado, base de datos que hay que alojar |
| C. Django completo | Admin y auth incluidos | Más "magia" que aprender; el admin genérico no sirve para editar lecciones/preguntas |

Se eligió A por mantenibilidad para quien está aprendiendo, costo y rendimiento. Se separan **blueprints** (rutas), **services** (lógica de negocio) y **migrations/SQL** (persistencia). Cambiar de SQLite a PostgreSQL implica tocar solo `sphinx/db.py` y el SQL (ver `db.py`: todas las consultas pasan por `q1/qa/ex/tx`).

## 2. Requisitos e instalación

- Python 3.10+ (probado con 3.12). Dependencias: Flask, reportlab (PDF). `gunicorn` solo para producción.

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # ajusta valores; nunca subas .env
python manage.py seed                                   # carga 3 cursos de DEMOSTRACIÓN
python manage.py create-admin --alias tu_alias          # pide contraseña (≥12 caracteres)
python run.py                                           # http://127.0.0.1:5000
```

Las migraciones (`sphinx/migrations/*.sql`) se aplican solas al iniciar y quedan registradas en `schema_migrations`.
`python manage.py reset-db --yes` **BORRA** la base de datos local.

### Pruebas
```bash
python -m unittest discover -s tests -t .
```
Resultado de la última ejecución: **41 pruebas, todas OK**. Cubren: calificación, cursos/borradores/filtros, evaluaciones (puntaje no manipulable, idempotencia, intentos), cuentas, permisos, aislamiento entre estudiantes, adopción de progreso, recuperación de contraseña, certificados + PDF + verificación, administración (crear/publicar), tutor (con proveedor simulado), cabeceras de seguridad y claves de traducción.
**No hay** pruebas de navegador (E2E) ni medición automática de accesibilidad: ver "Pendiente".

## 3. Estructura

```
run.py  manage.py  requirements.txt  .env.example
sphinx/
  __init__.py          fábrica de la app, manejo de errores
  config.py db.py      configuración y SQLite (transacciones, migraciones)
  security.py          sesión, CSRF, permisos, límite de intentos, cabeceras (CSP)
  i18n.py  locales/es.json   textos de interfaz centralizados
  richtext.py          texto enriquecido seguro (todo se escapa)
  blueprints/          public, auth, learn, student, api (tutor), admin
  services/            owner, grading, assessments, progress, gamification,
                       recommend, certificates, accounts, tutor, blocks
  seed/                contenido de demostración (math, science, spanish) + loader
  migrations/001_initial.sql
  templates/  static/
tests/
```

## 4. Modelo de datos (resumen)
`subjects → competencies`, `courses (status, version, pass_pct, max_attempts) → units → lessons → content_blocks (JSON validado)`.
`questions` (+ `answer_options`) se reutilizan en `assessments` (`diagnostic` por materia, `formative` por lección, `final` por curso) vía `assessment_questions`.
Progreso: `attempts`/`responses`, `lesson_progress`, `enrollments`, `learner_goals`, `xp_events`, `user_achievements`. Cada fila de progreso pertenece a **una cuenta (`user_id`) o a una sesión anónima (`anon_id`), nunca a ambas** (CHECK) y las unicidades evitan duplicados. `certificates`, `audit_log`, `login_attempts`, `password_resets`, `tutor_usage` (solo marcas de tiempo), `settings`.
Eliminar una cuenta borra por cascada todo lo suyo. Los cursos se archivan en lugar de borrarse (solo se borran borradores).
Diferencias con la lista de entidades del prompt: competencia dominada y recomendaciones se **calculan** al vuelo (no hay tablas `CompetencyProgress`/`Recommendation`); `CourseVersion` se reduce a un número `version` que sube al publicar; no existe `TutorConversation` a propósito (no se guardan conversaciones).

## 5. Reglas de negocio documentadas
- **Invitado**: sesión anónima en cookie firmada; el progreso se guarda en servidor y se borra tras `ANON_RETENTION_DAYS` (30) sin actividad. Al registrarse o ingresar puede **adoptar** su progreso (casilla explícita); se fusiona sin duplicar y la sesión anónima desaparece.
- **Calificación**: siempre en el servidor. Tipos: opción múltiple, verdadero/falso, numérica (acepta fracciones y decimales), respuesta corta (sin mayúsculas ni acentos), relacionar (crédito parcial). Las preguntas enviadas al navegador no incluyen respuestas correctas; reenviar un intento no duplica nada.
- **Lección completada**: si tiene comprobación con preguntas, se aprueba con ≥ `formative_pass_pct` (60 por defecto); si no, se marca manualmente.
- **Curso completado / certificado**: todas las lecciones completadas **y** evaluación final ≥ `pass_pct` del curso; requiere cuenta. El servidor lo comprueba al emitir.
- **XP** (una vez por logro verificado, ajustable en admin): lección 10, comprobación aprobada 20, diagnóstico 15 (por materia), curso 100, repaso 5 (una vez al día). Repetir no suma. Nivel *n* empieza en 40·(n−1)² XP. Insignias: primer paso, explorador, constancia (5 lecciones), precisión (≥90%), curso completado. Sin rankings; la racha es opcional y ocultable.
- **Dominio de competencia**: con el intento enviado más reciente de cada evaluación: ≥75% dominada, 50–74% en desarrollo, <50% por reforzar; con menos de 2 preguntas, "sin datos suficientes". Es una estimación, no una etiqueta.
- **Recomendaciones (reglas, en este orden)**: (1) lección que refuerza cada competencia "por reforzar"; (2) cursos empezados; (3) para cada materia elegida en Objetivos, un curso sin empezar (más difícil si el resultado en la materia ≥80%, más fácil si no); (4) sin datos: curso introductorio. Cada una explica su motivo. No hay bloqueos de contenido.
- **Reto de repaso**: hasta 5 preguntas cuya respuesta más reciente fue incorrecta.

## 6. Seguridad y privacidad (lo implementado)
Contraseñas con hash (werkzeug); sesión firmada, HttpOnly, SameSite=Lax, `Secure` en producción; sesión nueva al ingresar; CSRF en todo POST; límite de intentos de acceso (5 por 15 min por usuario+IP, 30 por IP); mensajes de error genéricos (sin trazas); validación en servidor; consultas parametrizadas; autoescape de Jinja + texto enriquecido restringido (sin HTML arbitrario); CSP estricta (sin scripts ni estilos en línea, sin recursos remotos); `X-Frame-Options`, `nosniff`; límite de tamaño de solicitud; redirecciones solo internas; cuentas desactivadas pierden acceso de inmediato; roles solo asignables por `manage.py create-admin`; bitácora de acciones administrativas; el panel admin no muestra correos ni progreso individual.
Privacidad: solo alias, correo opcional y progreso; sin telemetría ni anuncios; descarga (JSON) y eliminación de cuenta; el tutor no guarda mensajes. **Los textos de privacidad y consentimiento son un borrador técnico: deben ser revisados por una persona experta en la normativa aplicable (p. ej. México; datos de menores) antes de publicar.** Lista de verificación de dependencias: ejecutar `pip list --outdated` y una herramienta como `pip-audit` periódicamente (no incluida).

## 7. Tutor de IA (opcional)
Usa la API de mensajes de Anthropic **desde el servidor**. Configura en `.env`: `ANTHROPIC_API_KEY`, `TUTOR_MODEL` (por defecto `claude-haiku-5-5`), `TUTOR_DAILY_LIMIT`, `TUTOR_MINUTE_LIMIT`. Sin clave, se muestra como no disponible (no se simula nada). Instrucciones de sistema apropiadas para menores (pistas antes de respuestas, sin datos personales, derivar a adultos de confianza ante riesgos), el contexto de la lección se lee de la base de datos y se trata como dato, límites por minuto y por día, tiempo de espera de 20 s, manejo de cuota agotada.
**Probado solo con un proveedor simulado**: en el entorno de desarrollo no hubo acceso a internet, así que la llamada real a la API no se ha verificado. Prueba con tu clave antes de depender de ella. Ningún filtro de IA es perfecto; el prompt reduce pero no elimina el riesgo de contenido inapropiado. **Costo**: se paga por uso de la API del proveedor; el límite diario por estudiante acota el gasto (revisa precios vigentes en la consola del proveedor).

## 8. Guía rápida de contenido (admin)
1. *Materias y competencias* → crea materia/competencias (y un diagnóstico si quieres).
2. *Preguntas* → crea preguntas (opción múltiple, V/F, numérica, corta, relacionar) con explicación.
3. *Cursos → Nuevo curso* → completa metadatos; agrega unidades y lecciones; en cada lección agrega bloques (texto, ejemplo resuelto, consejo, errores frecuentes, resumen, tarjetas).
4. En *Evaluaciones* (o desde la lección/curso) elige las preguntas de la comprobación de cada lección y de la evaluación final.
5. *Vista previa* y *Publicar*: el sistema se niega si faltan lecciones, contenido, preguntas finales o competencias.
**Agregar otro idioma**: copia `sphinx/locales/es.json` a `en.json`, traduce valores y establece la cookie `lang=en` (no hay selector de idioma en la interfaz todavía); si falta una clave se usa español. El contenido educativo guarda su idioma (`language`) pero la interfaz solo filtra por español por ahora.

## 9. Despliegue (guía, no realizado)
1. Elige un alojamiento Python con disco persistente (o migra a PostgreSQL). Los planes gratuitos suelen tener límites, suspensión por inactividad o discos efímeros: **verifica antes de confiar datos reales**; nada garantiza disponibilidad permanente.
2. Variables: `SPHINX_ENV=production`, `SECRET_KEY` (aleatoria), `DATABASE_PATH` (ruta persistente), `TRUST_PROXY=1` si hay proxy, `PUBLIC_BASE_URL=https://tu-dominio`, SMTP (si quieres recuperar contraseñas) y, opcional, tutor.
3. `pip install -r requirements.txt && python manage.py seed && python manage.py create-admin --alias ...`
4. Ejecutar: `gunicorn -w 2 -b 0.0.0.0:8000 run:app` detrás de HTTPS (el proveedor o un proxy).
5. Copias de seguridad: copia periódica de `sphinx.db` (usa `sqlite3 sphinx.db ".backup copia.db"`). Programa `python manage.py purge-anon` (cron) si quieres limpiar invitados además del limpiado al arrancar.
**Costos posibles**: alojamiento, correo transaccional (SMTP), dominio, y uso de la API de IA. Lo básico (cursos) no depende de ningún servicio de pago.

## 10. Criterios de aceptación: estado real
| # | Criterio | Estado |
|---|---|---|
| 1 | Instalar y ejecutar localmente | ✅ (probado en el entorno de desarrollo) |
| 2 | Base de datos conserva datos | ✅ SQLite + migraciones |
| 3 | Explorar sin registrarse | ✅ |
| 4 | Objetivos y diagnóstico | ✅ |
| 5 | Cursos reales de las 3 materias | ✅ **uno por materia** (3 lecciones cada uno): colección pequeña, de demostración |
| 6 | Lecciones con actividades y retroalimentación | ✅ |
| 7 | Resultados y recomendaciones | ✅ |
| 8 | Cuentas guardan y recuperan progreso | ✅ |
| 9 | Permisos validados en el servidor | ✅ (con pruebas) |
| 10 | Admin crea, edita y publica desde la interfaz | ✅ |
| 11 | Estadísticas con datos reales | ✅ agregadas |
| 12 | Gamificación por acciones verificables | ✅ |
| 13 | Certificados respetan requisitos | ✅ PDF real y verificación |
| 14 | Tutor real y falla de forma segura | ⚠️ falla de forma segura (probado); integración real **sin verificar** (sin internet en el desarrollo) |
| 15 | Responsive y accesibilidad principal | ⚠️ implementado según buenas prácticas; **sin pruebas en dispositivos reales ni con lectores de pantalla** |
| 16 | Pruebas ejecutadas y documentadas | ✅ 41 OK (sin E2E de navegador) |
| 17 | Instrucciones de producción | ✅ guía; **no desplegado** |
| 18 | Limitaciones documentadas | ✅ abajo |

## 11. Pendiente / limitaciones conocidas
- Contenido: solo 3 cursos (9 lecciones) de demostración; sin imágenes ni diagramas; sin alineación curricular oficial verificada.
- Accesibilidad: sin auditoría WCAG formal, sin medición de contraste en el tema oscuro, sin pruebas con NVDA/VoiceOver; el audio es solo la voz del navegador (si existe).
- Sin pruebas E2E en navegador; JavaScript (tarjetas, tutor, menú, lector) sin pruebas automáticas.
- Correo (SMTP) sin probar contra un servidor real; sin SMTP la recuperación de contraseña no funciona en producción (en desarrollo el enlace se imprime en la consola).
- Admin: no hay duplicar cursos, ni reordenar arrastrando (hay botones ↑↓), ni revocar certificados desde la interfaz, ni reiniciar contraseñas de otros usuarios desde la interfaz (`manage.py reset-password`).
- Aviso de privacidad y consentimiento: borrador; revisión legal pendiente. No hay verificación de edad ni flujo de autorización parental más allá de una casilla.
- Búsqueda de cursos en memoria (suficiente para cientos de cursos; para más, usar FTS5).
- Una sola instancia de SQLite; para alta concurrencia migrar a PostgreSQL.
- Selector de idioma de interfaz no incluido (solo cookie `lang`).
