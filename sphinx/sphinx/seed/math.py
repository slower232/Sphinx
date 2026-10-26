from .dsl import *

SUBJECT = {"slug": "matematicas", "name": "Matemáticas", "icon": "➗", "position": 1, "color": "red",
           "description": "Números, operaciones y razonamiento para resolver problemas de la vida diaria.",
           "competencies": [
               ("fracciones-concepto", "Comprender y representar fracciones", "Interpretar qué significan numerador y denominador."),
               ("fracciones-equivalentes", "Comparar y simplificar fracciones", "Usar fracciones equivalentes para comparar y simplificar."),
               ("fracciones-operaciones", "Sumar y restar fracciones", "Operar con fracciones de igual y distinto denominador.")]}

C1, C2, C3 = "fracciones-concepto", "fracciones-equivalentes", "fracciones-operaciones"

DIAGNOSTIC = [
    mcq("Un círculo se divide en 4 partes iguales y se sombrean 3. ¿Qué fracción está sombreada?", ["3/4", "4/3", "1/4", "3/7"], 0,
        "El denominador (4) cuenta las partes iguales del total y el numerador (3) las partes sombreadas: 3/4.", C1, 1),
    tf("En la fracción 7/10, el denominador es 7.", False,
       "El denominador es el número de abajo: 10. El 7 es el numerador.", C1, 1),
    num("Completa la fracción equivalente: 1/2 = ?/10. ¿Qué número va en lugar de ?", 5,
        "Multiplicamos arriba y abajo por 5: 1×5 = 5 y 2×5 = 10.", C2, 2),
    mcq("¿Cuál fracción es mayor: 2/3 o 3/4?", ["2/3", "3/4", "Son iguales", "No se puede saber"], 1,
        "Con denominador común 12: 2/3 = 8/12 y 3/4 = 9/12. Como 9/12 > 8/12, 3/4 es mayor.", C2, 2),
    num("Calcula 2/9 + 5/9. Escribe el resultado como fracción (por ejemplo 3/4).", "7/9",
        "Con el mismo denominador se suman los numeradores: 2 + 5 = 7, y el denominador se queda en 9.", C3, 3),
    mcq("Calcula 1/2 + 1/3.", ["2/5", "5/6", "1/5", "2/6"], 1,
        "Denominador común 6: 3/6 + 2/6 = 5/6. Sumar numeradores con numeradores y denominadores con denominadores (2/5) es un error frecuente.", C3, 3),
]

COURSE = {
    "slug": "fracciones-desde-cero", "title": "Fracciones desde cero",
    "description": "Aprende qué son las fracciones, cómo compararlas y simplificarlas y cómo sumarlas y restarlas, con ejemplos de la vida diaria.",
    "objectives": ["Explicar qué representan el numerador y el denominador de una fracción.",
                   "Encontrar fracciones equivalentes y simplificar una fracción.",
                   "Sumar y restar fracciones con igual y distinto denominador."],
    "level": "basico", "difficulty": 1, "pass_pct": 70, "max_attempts": 0, "competencies": [C1, C2, C3],
    "prerequisites": "Saber multiplicar y dividir con números naturales.",
    "resources": "Practica con objetos reales: divide una hoja o una tortilla en partes iguales y nombra cada parte como fracción.",
    "units": [
        {"title": "Entender las fracciones", "lessons": [
            {"title": "¿Qué es una fracción?", "est": 10,
             "summary": "Una fracción representa partes iguales de un todo: el denominador dice en cuántas se dividió y el numerador cuántas se toman.",
             "blocks": [
                 text("La idea", "Una **fracción** representa una o varias partes de un todo que se dividió en partes **iguales**.\n\nSe escribe con dos números: el **numerador** (arriba) dice cuántas partes tomamos y el **denominador** (abajo) dice en cuántas partes iguales se dividió el todo.\n\nSi una pizza se corta en 8 rebanadas iguales y comes 3, comiste 3/8 de la pizza."),
                 example("Leer una fracción", "Una barra de chocolate tiene 10 cuadritos iguales. Te regalan 4. ¿Qué fracción de la barra recibes?",
                         ["El total de partes iguales es 10: ese es el denominador.", "Las partes que tomas son 4: ese es el numerador.", "Escribimos numerador sobre denominador."], "4/10 de la barra."),
                 mistakes("Pensar que 1/8 es mayor que 1/4 porque 8 es mayor que 4. Mientras más partes se hacen, cada parte es más pequeña.",
                          "Olvidar que las partes deben ser iguales: si una pizza se corta en trozos desiguales, no se puede hablar de octavos."),
                 cards(("Numerador", "El número de arriba: cuántas partes se toman."), ("Denominador", "El número de abajo: en cuántas partes iguales se dividió el todo."),
                       ("Fracción propia", "Aquella cuyo numerador es menor que el denominador, como 3/5.")),
                 summary("El denominador cuenta las partes iguales del total.", "El numerador cuenta las partes que tomamos.", "A mayor denominador (con el mismo numerador), cada parte es más pequeña.")],
             "quiz": [
                 mcq("En la fracción 5/9, ¿qué indica el 9?", ["Cuántas partes se toman", "En cuántas partes iguales se dividió el todo", "El resultado de una resta", "El tamaño de cada parte en centímetros"], 1,
                     "El denominador indica en cuántas partes iguales se dividió el todo.", C1, 1),
                 tf("Si una pizza se corta en 6 partes iguales y comes 2, comiste 2/6 de la pizza.", True,
                    "Se tomaron 2 de 6 partes iguales: 2/6.", C1, 1),
                 mcq("¿Cuál de estas fracciones es mayor?", ["1/8", "1/4", "Son iguales", "No se puede comparar"], 1,
                     "Con el mismo numerador, la fracción con menor denominador es mayor: 1/4 son partes más grandes que 1/8.", C1, 2)]},
            {"title": "Fracciones equivalentes y simplificación", "est": 15,
             "summary": "Dos fracciones son equivalentes si representan la misma cantidad; se obtienen multiplicando o dividiendo numerador y denominador por el mismo número.",
             "blocks": [
                 text("Misma cantidad, distinta escritura", "Las fracciones **equivalentes** representan la misma cantidad. Por ejemplo, 1/2, 2/4 y 4/8 son la misma mitad.\n\nPara obtenerlas, **multiplica o divide** el numerador y el denominador **por el mismo número** (distinto de cero).\n\nSimplificar es dividir arriba y abajo entre un divisor común hasta que ya no se pueda más."),
                 example("Simplificar 12/18", "Simplifica la fracción 12/18.",
                         ["Busca un número que divida a 12 y a 18. Sirve el 6.", "12 ÷ 6 = 2 y 18 ÷ 6 = 3.", "2/3 ya no se puede simplificar."], "12/18 = 2/3"),
                 tip("Para comparar dos fracciones con distinto denominador, conviértelas a fracciones equivalentes con el mismo denominador y compara los numeradores."),
                 mistakes("Sumar el mismo número arriba y abajo: 1/2 y 2/3 NO son equivalentes. Hay que multiplicar o dividir, no sumar.",
                          "Dejar una fracción a medias: 6/12 se puede dividir entre 6 para llegar a 1/2."),
                 summary("Equivalentes: multiplicar o dividir arriba y abajo por el mismo número.", "Simplificar: dividir entre divisores comunes.", "Para comparar, usa un denominador común.")],
             "quiz": [
                 num("Completa: 3/4 = ?/12. ¿Qué número va en lugar de ?", 9, "12 ÷ 4 = 3, así que se multiplica por 3: 3×3 = 9.", C2, 1),
                 mcq("¿Cuál es la fracción 12/18 simplificada al máximo?", ["6/9", "2/3", "4/6", "1/2"], 1, "Dividiendo entre 6 se obtiene 2/3. 6/9 y 4/6 son equivalentes pero aún se pueden simplificar.", C2, 2),
                 short("Escribe la fracción 10/15 simplificada al máximo (con el formato a/b).", ["2/3"], "Dividimos entre 5: 10 ÷ 5 = 2 y 15 ÷ 5 = 3.", C2, 2)]}]},
        {"title": "Operar con fracciones", "lessons": [
            {"title": "Sumar y restar fracciones", "est": 15,
             "summary": "Con igual denominador se suman o restan los numeradores; con distinto denominador primero se buscan fracciones equivalentes con denominador común.",
             "blocks": [
                 text("Igual denominador", "Si las fracciones tienen el **mismo denominador**, suma o resta los numeradores y conserva el denominador.\n\nPor ejemplo: 3/8 + 2/8 = 5/8. Son 3 octavos y 2 octavos, en total 5 octavos."),
                 text("Distinto denominador", "Si los denominadores son distintos, primero convierte las fracciones a otras **equivalentes con el mismo denominador** y luego opera.\n\nUna forma fácil es usar un múltiplo común de ambos denominadores."),
                 example("Sumar 1/3 + 1/6", "Calcula 1/3 + 1/6.",
                         ["El denominador común puede ser 6, porque 6 es múltiplo de 3.", "1/3 = 2/6.", "2/6 + 1/6 = 3/6.", "Simplificamos 3/6 dividiendo entre 3."], "1/3 + 1/6 = 1/2"),
                 mistakes("Sumar también los denominadores: 1/2 + 1/3 no es 2/5. El resultado correcto es 5/6.",
                          "Olvidar simplificar el resultado final cuando se puede."),
                 summary("Igual denominador: opera los numeradores y conserva el denominador.", "Distinto denominador: busca equivalentes con denominador común.", "Al final, simplifica.")],
             "quiz": [
                 num("Calcula 3/7 + 2/7. Escribe el resultado como fracción.", "5/7", "Mismo denominador: 3 + 2 = 5, y el denominador sigue siendo 7.", C3, 1),
                 mcq("Calcula 1/2 + 1/4.", ["2/6", "3/4", "1/6", "2/4"], 1, "1/2 = 2/4, y 2/4 + 1/4 = 3/4.", C3, 2),
                 tf("1/3 + 1/4 = 2/7.", False, "No se suman los denominadores. Con denominador 12: 4/12 + 3/12 = 7/12.", C3, 2)]}]}],
    "final": [
        num("Calcula 5/6 − 1/6. Escribe el resultado como fracción.", "2/3", "5/6 − 1/6 = 4/6, y simplificando 4/6 = 2/3 (el sistema acepta cualquier fracción equivalente).", C3, 1),
        mcq("¿Cuál de estas fracciones es equivalente a 2/5?", ["4/10", "3/6", "2/10", "5/2"], 0, "Multiplicando arriba y abajo por 2: 2/5 = 4/10.", C2, 1),
        short("Simplifica la fracción 8/12 al máximo (con el formato a/b).", ["2/3"], "Se divide entre 4: 8 ÷ 4 = 2 y 12 ÷ 4 = 3.", C2, 2),
        mcq("Ana comió 1/4 de una pizza y Luis comió 2/4. ¿Qué fracción de la pizza comieron entre los dos?", ["3/8", "3/4", "2/4", "1/2"], 1, "Mismo denominador: 1 + 2 = 3, así que comieron 3/4.", C3, 2),
        match("Relaciona cada fracción con una fracción equivalente.", [["1/2", "2/4"], ["1/3", "2/6"], ["3/4", "6/8"], ["2/5", "4/10"]],
              "En cada caso se multiplicó numerador y denominador por 2.", C2, 2)],
}
