from .dsl import *

SUBJECT = {"slug": "ciencias-naturales", "name": "Ciencias naturales", "icon": "🔬", "position": 2, "color": "green",
           "description": "Entiende los fenómenos naturales que ocurren a tu alrededor.",
           "competencies": [
               ("materia-estados", "Reconocer los estados de la materia", "Distinguir sólidos, líquidos y gases por sus propiedades."),
               ("cambios-estado", "Explicar los cambios de estado", "Nombrar y explicar los cambios de estado del agua."),
               ("ciclo-agua", "Describir el ciclo del agua", "Explicar cómo circula el agua en la naturaleza.")]}

C1, C2, C3 = "materia-estados", "cambios-estado", "ciclo-agua"

DIAGNOSTIC = [
    mcq("¿En qué estado de la materia se encuentra el aire que respiramos?", ["Sólido", "Líquido", "Gaseoso", "Plasma congelado"], 2, "El aire es una mezcla de gases: ocupa todo el espacio disponible y no tiene forma fija.", C1, 1),
    tf("El hielo es agua en estado sólido.", True, "El hielo es el estado sólido del agua: mantiene su forma y su volumen.", C1, 1),
    mcq("Cuando un charco de agua desaparece bajo el sol, ¿qué cambio de estado ocurrió principalmente?", ["Solidificación", "Evaporación", "Fusión", "Condensación"], 1, "El agua líquida pasa a vapor por evaporación: el calor del Sol mueve más rápido sus partículas.", C2, 2),
    short("¿Cómo se llama el cambio de estado de un sólido a un líquido? (una palabra)", ["fusion", "fusión"], "Fusión: el sólido recibe calor y se derrite, como el hielo que pasa a agua.", C2, 2),
    mcq("En el ciclo del agua, las nubes se forman principalmente por…", ["Fusión", "Condensación", "Solidificación", "Sublimación"], 1, "El vapor de agua se enfría en el aire y se condensa en gotitas muy pequeñas que forman las nubes.", C3, 2),
    tf("El agua de ríos y mares puede evaporarse y volver a caer como lluvia.", True, "Eso es el ciclo del agua: evaporación, condensación y precipitación.", C3, 1),
]

COURSE = {
    "slug": "el-agua-y-sus-cambios", "title": "El agua y sus cambios",
    "description": "Descubre los estados de la materia, cómo cambia el agua de un estado a otro y cómo circula por nuestro planeta.",
    "objectives": ["Distinguir sólidos, líquidos y gases por sus propiedades.", "Nombrar y explicar los cambios de estado del agua.", "Describir las etapas del ciclo del agua."],
    "level": "basico", "difficulty": 1, "pass_pct": 70, "max_attempts": 0, "competencies": [C1, C2, C3],
    "prerequisites": "Ninguno.",
    "resources": "Observa en casa: deja un vaso de agua al sol, otro en el congelador y mira qué ocurre después de unas horas.",
    "units": [
        {"title": "La materia y sus estados", "lessons": [
            {"title": "Sólidos, líquidos y gases", "est": 10,
             "summary": "La materia se presenta como sólido, líquido o gas según cómo están organizadas y se mueven sus partículas.",
             "blocks": [
                 text("Tres estados", "Todo lo que ocupa espacio y tiene masa es **materia**. En la vida diaria la encontramos sobre todo en tres estados:\n\n- **Sólido**: tiene forma y volumen propios (una piedra, el hielo).\n- **Líquido**: tiene volumen propio, pero toma la forma del recipiente (el agua, el jugo).\n- **Gas**: no tiene forma ni volumen propios; se expande y ocupa todo el recipiente (el aire)."),
                 example("El agua en tres estados", "Explica en qué estado está el agua en un cubo de hielo, en un vaso y en el vapor invisible del aire.",
                         ["El cubo de hielo conserva su forma: sólido.", "El agua del vaso toma la forma del vaso: líquido.", "El vapor de agua se mezcla con el aire y se expande: gas."], "Hielo = sólido, agua = líquido, vapor de agua = gas."),
                 mistakes("Creer que la “nube” blanca que sale de una olla es vapor de agua. El vapor de agua es invisible; lo que vemos son gotitas diminutas de agua líquida.",
                          "Pensar que los gases no son materia solo porque no los vemos: el aire ocupa espacio y tiene masa."),
                 cards(("Sólido", "Forma y volumen propios."), ("Líquido", "Volumen propio y forma del recipiente."), ("Gas", "Se expande y ocupa todo el recipiente.")),
                 summary("Los tres estados más comunes son sólido, líquido y gas.", "Se distinguen por su forma y su volumen.")],
             "quiz": [
                 mcq("¿Qué estado tiene forma y volumen definidos?", ["Gas", "Líquido", "Sólido", "Ninguno"], 2, "El sólido conserva su forma y su volumen.", C1, 1),
                 tf("Un gas conserva siempre el mismo volumen sin importar el recipiente en que esté.", False, "Un gas se expande y ocupa todo el espacio del recipiente.", C1, 1),
                 mcq("Una bebida toma la forma del vaso, pero su cantidad no cambia. ¿En qué estado está?", ["Sólido", "Líquido", "Gas", "No es materia"], 1, "Los líquidos tienen volumen propio pero se adaptan a la forma del recipiente.", C1, 2)]},
            {"title": "Cambios de estado", "est": 15,
             "summary": "El agua cambia de estado cuando gana o pierde calor: fusión, solidificación, evaporación y condensación.",
             "blocks": [
                 text("Ganar o perder calor", "Cuando una sustancia **gana calor**, sus partículas se mueven más rápido; cuando lo **pierde**, se mueven más despacio. Por eso puede cambiar de estado.\n\nEn el agua, a nivel del mar: se **congela** a 0 °C y **hierve** a 100 °C."),
                 text("Los nombres de los cambios", "- **Fusión**: de sólido a líquido (el hielo se derrite).\n- **Solidificación**: de líquido a sólido (el agua se congela).\n- **Evaporación**: de líquido a gas (el agua se convierte en vapor).\n- **Condensación**: de gas a líquido (el vapor forma gotitas en un vidrio frío)."),
                 example("¿Qué cambio ocurre?", "Un espejo del baño se empaña después de una ducha caliente. ¿Qué cambio de estado ocurrió?",
                         ["El aire tiene vapor de agua (gas).", "El espejo está más frío y enfría ese vapor.", "El vapor pasa a gotitas líquidas."], "Condensación."),
                 mistakes("Confundir fusión con solidificación: son cambios contrarios.", "Pensar que el agua solo hierve a 100 °C en cualquier lugar: ese valor es a nivel del mar."),
                 cards(("Fusión", "Sólido → líquido (se gana calor)."), ("Solidificación", "Líquido → sólido (se pierde calor)."), ("Evaporación", "Líquido → gas (se gana calor)."), ("Condensación", "Gas → líquido (se pierde calor)."))],
             "quiz": [
                 mcq("¿Cómo se llama el paso de líquido a gas?", ["Fusión", "Condensación", "Evaporación", "Solidificación"], 2, "La evaporación es el cambio de líquido a gas.", C2, 1),
                 short("Escribe el nombre del cambio de líquido a sólido (una palabra).", ["solidificacion", "solidificación", "congelacion", "congelación"], "Es la solidificación (también se le llama congelación en el caso del agua).", C2, 1),
                 num("A nivel del mar, ¿a cuántos grados Celsius hierve el agua pura? Escribe solo el número.", 100, "A nivel del mar el agua pura hierve a 100 °C.", C2, 1)]}]},
        {"title": "El agua en movimiento", "lessons": [
            {"title": "El ciclo del agua", "est": 15,
             "summary": "El Sol impulsa el ciclo del agua: evaporación, condensación, precipitación y regreso del agua a ríos, mares y suelo.",
             "blocks": [
                 text("Un recorrido sin fin", "El agua de la Tierra no se acaba: **circula** en un ciclo.\n\n1. **Evaporación**: el calor del Sol convierte agua de mares, ríos y lagos en vapor.\n2. **Condensación**: el vapor sube, se enfría y forma gotitas: las nubes.\n3. **Precipitación**: las gotas crecen y caen como lluvia, nieve o granizo.\n4. **Escurrimiento e infiltración**: el agua corre hacia ríos y mares o entra al suelo."),
                 example("Seguir una gota", "Describe el recorrido de una gota de agua que sale de un lago.",
                         ["El Sol la evapora y sube como vapor.", "En lo alto se enfría y forma parte de una nube.", "Cae como lluvia sobre una montaña y escurre al río."], "Lago → vapor → nube → lluvia → río."),
                 mistakes("Pensar que la lluvia “se acaba” el agua: el agua se transforma y vuelve a circular."),
                 summary("La energía del Sol impulsa el ciclo.", "Etapas: evaporación, condensación, precipitación y escurrimiento/infiltración.")],
             "quiz": [
                 mcq("¿Qué fuente de energía impulsa el ciclo del agua?", ["El viento", "El Sol", "La Luna", "Los volcanes"], 1, "El calor del Sol evapora el agua y mantiene el ciclo en movimiento.", C3, 1),
                 tf("En la condensación, el vapor de agua se enfría y forma gotitas de agua líquida.", True, "Así se forman las nubes.", C3, 1),
                 mcq("La lluvia, la nieve y el granizo reciben el nombre de…", ["Evaporación", "Infiltración", "Precipitación", "Fusión"], 2, "Todas son formas de precipitación.", C3, 1)]}]}],
    "final": [
        mcq("Sacas un hielo del congelador y se derrite sobre la mesa. ¿Qué cambio de estado ocurre?", ["Fusión", "Evaporación", "Condensación", "Solidificación"], 0, "El hielo gana calor y pasa de sólido a líquido: fusión.", C2, 1),
        tf("Cuando el agua de mar se evapora, la sal también se convierte en vapor.", False, "La sal no se evapora con el agua: se queda en el mar.", C3, 2),
        short("Escribe cómo se llama el proceso en el que el agua cae del cielo como lluvia, nieve o granizo (una palabra).", ["precipitacion", "precipitación"], "Se llama precipitación.", C3, 1),
        match("Relaciona cada estado con su característica.", [["Sólido", "Forma y volumen propios"], ["Líquido", "Volumen propio y forma del recipiente"], ["Gas", "Se expande y ocupa todo el recipiente"]],
              "Lo que distingue a cada estado es la forma en que se comportan sus partículas.", C1, 2),
        num("¿A cuántos grados Celsius se congela el agua pura a nivel del mar? Escribe solo el número.", 0, "El agua se congela (y el hielo se derrite) a 0 °C.", C2, 1)],
}
