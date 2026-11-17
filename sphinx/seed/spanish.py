from .dsl import *

SUBJECT = {"slug": "espanol", "name": "Español y comprensión lectora", "icon": "📖", "position": 3, "color": "blue",
           "description": "Lee con atención, entiende lo que dicen los textos y también lo que sugieren.",
           "competencies": [
               ("idea-principal", "Identificar la idea principal", "Distinguir la idea principal de los detalles."),
               ("inferencia", "Inferir información no explícita", "Sacar conclusiones apoyadas en pistas del texto."),
               ("vocabulario-contexto", "Deducir el significado por contexto", "Usar el contexto para entender palabras nuevas.")]}

C1, C2, C3 = "idea-principal", "inferencia", "vocabulario-contexto"

ABEJAS = "Las abejas son esenciales para la agricultura. Al visitar flores para alimentarse de néctar, transportan polen de una planta a otra y permiten que se formen frutos y semillas. Sin ellas, muchos cultivos producirían menos."

DIAGNOSTIC = [
    mcq("Lee el texto:\n\n" + ABEJAS + "\n\n¿Cuál es la idea principal?", ["Las abejas se alimentan de néctar.", "Las abejas son importantes para que las plantas den frutos y semillas.", "Las abejas viven en panales.", "Los cultivos son muy grandes."], 1,
        "La idea principal es lo más importante que dice el texto: sin abejas habría menos frutos y semillas. Alimentarse de néctar es solo un detalle.", C1, 1, scene="🐝🌼"),
    tf("Un detalle es una información que apoya o ejemplifica la idea principal.", True, "Los detalles explican, ejemplifican o prueban la idea principal.", C1, 1),
    mcq("Dani abrió la ventana, tomó un suéter y se lo puso. ¿Qué se puede inferir?", ["Que tenía calor.", "Que sintió frío.", "Que quería salir corriendo.", "Que estaba dormido."], 1,
        "Ponerse un suéter es una pista de que sintió frío; la ventana abierta pudo causarlo.", C2, 2, scene="🧥"),
    tf("Una inferencia debe apoyarse en pistas del texto y no solo en lo que imaginamos.", True, "Inferir es sacar una conclusión usando pistas del texto y lo que ya sabemos.", C2, 1, scene="🕵️"),
    mcq("«La escasez de lluvia preocupó a los agricultores porque casi no había agua para los cultivos.» ¿Qué significa «escasez»?", ["Mucha cantidad", "Poca cantidad o falta de algo", "Un tipo de lluvia", "Un cultivo"], 1,
        "El contexto («casi no había agua») indica que escasez significa que hay poco o falta algo.", C3, 2, scene="🌾"),
    mcq("«El agua del río es tan cristalina que se ven los peces del fondo.» ¿Qué significa «cristalina»?", ["Sucia", "Helada", "Muy clara y transparente", "Muy profunda"], 2,
        "Si se ven los peces del fondo, el agua es transparente.", C3, 3, scene="🐟"),
]

COURSE = {
    "slug": "leer-con-proposito", "title": "Leer con propósito: comprensión lectora",
    "description": "Aprende a encontrar la idea principal, a leer entre líneas y a descubrir el significado de palabras nuevas usando el contexto, con juegos y dibujos.",
    "objectives": ["Distinguir la idea principal de los detalles de un texto.", "Hacer inferencias apoyadas en pistas del texto.", "Deducir el significado de una palabra a partir del contexto."],
    "level": "basico", "difficulty": 2, "pass_pct": 70, "max_attempts": 0, "competencies": [C1, C2, C3],
    "prerequisites": "Leer textos breves con soltura.",
    "resources": "Practica con una noticia corta o un artículo de tu interés: escribe en una línea su idea principal.",
    "units": [
        {"title": "Entender lo que dice el texto", "lessons": [
            {"title": "Idea principal y detalles", "est": 12,
             "summary": "La idea principal es lo más importante que comunica un párrafo; los detalles la explican o la apoyan.",
             "blocks": [
                 scene("🐝 🌼 🍎", "Las abejas llevan polen de flor en flor y así las plantas dan frutos."),
                 text("Lo más importante", "La **idea principal** es lo más importante que el autor quiere comunicar. Los **detalles** la explican, la ejemplifican o la prueban.\n\nUna buena pregunta para encontrarla es: *¿de qué trata el texto y qué dice sobre eso?*"),
                 example("Encontrar la idea principal", "Lee: «Dormir entre 8 y 10 horas ayuda a los adolescentes a concentrarse y recordar lo que estudian. Además, el descanso fortalece las defensas del cuerpo. Por eso, dormir bien es tan importante como estudiar.» ¿Cuál es la idea principal?",
                         ["Pregunta de qué trata: del descanso.", "¿Qué dice sobre eso? Que es tan importante como estudiar.", "Concentrarse y fortalecer defensas son detalles que lo apoyan."], "Dormir bien es muy importante, tanto como estudiar."),
                 mistakes("Confundir el **tema** (de qué habla) con la **idea principal** (lo que dice sobre ese tema).", "Elegir un detalle llamativo o curioso como si fuera lo principal."),
                 summary("Idea principal = lo más importante del texto.", "Detalles = datos que la apoyan.", "Pregúntate: ¿qué dice el autor sobre el tema?")],
             "quiz": [
                 mcq("Lee: «" + ABEJAS + "» ¿Cuál es la idea principal?", ["Las abejas se alimentan de néctar.", "Las abejas son importantes para que las plantas den frutos y semillas.", "Las abejas viven en panales."], 1,
                     "Lo más importante: sin abejas habría menos frutos y semillas. Alimentarse de néctar es un detalle.", C1, 2, scene="🐝🌼"),
                 mcq("«Las abejas llevan polen de flor en flor y así las plantas dan frutos.» ¿Qué dibujo resume mejor este texto?", ["Abejas, flores y frutos", "Peces en el mar", "Autos en la ciudad"], 0,
                     "El dibujo debe mostrar lo principal: abejas, flores y frutos.", C1, 1, emojis=["🐝🌼🍎", "🐟🌊", "🚗🏙️"], layout="images"),
                 tf("Un detalle es una información que apoya o ejemplifica la idea principal.", True, "Los detalles sostienen la idea principal con datos, ejemplos o razones.", C1, 1),
                 match("Arrastra cada descripción a su nombre.", [["Lo más importante del texto", "Idea principal"], ["Un dato que apoya la idea", "Detalle"], ["De qué trata el texto", "Tema"]],
                       "La idea principal es lo más importante; el detalle la apoya; el tema es de qué habla el texto.", C1, 2),
                 order("Ordena las palabras para formar una oración.", ["Las", "abejas", "ayudan", "a", "polinizar", "flores"],
                       "La oración correcta es: «Las abejas ayudan a polinizar flores».", C1, 1, scene="🐝")]},
            {"title": "Leer entre líneas: inferir", "est": 12,
             "summary": "Inferir es sacar conclusiones usando pistas del texto y lo que ya sabemos.",
             "blocks": [
                 scene("🌧️ ☔ 😮‍💨", "Alguien llega empapado con un paraguas roto. El texto no dice que llovió, pero podemos inferirlo."),
                 text("Pistas + lo que sé", "Muchas veces los textos **no lo dicen todo**. Inferir es llegar a una conclusión combinando las **pistas del texto** con lo que ya sabes."),
                 example("Una escena con pistas", "«Marta llegó empapada y dejó un paraguas roto junto a la puerta.» ¿Qué se puede inferir?",
                         ["Pista 1: llegó empapada.", "Pista 2: el paraguas está roto.", "Conocimiento previo: con lluvia fuerte o viento se mojan las personas y se rompen paraguas."], "Probablemente llovía mucho o hacía mucho viento."),
                 mistakes("Inventar una conclusión sin ninguna pista en el texto.", "Confundir lo que se infiere con lo que el texto dice literalmente."),
                 summary("Inferir = pistas del texto + conocimientos previos.", "Una buena inferencia siempre se puede justificar con el texto.")],
             "quiz": [
                 mcq("Sofía bostezaba y se frotaba los ojos mientras miraba el reloj. Probablemente…", ["Tenía sueño.", "Tenía hambre.", "Estaba muy enojada.", "Iba a viajar."], 0, "Bostezar y frotarse los ojos son pistas de sueño.", C2, 1, scene="🥱"),
                 mcq("«Marta llegó empapada y con el paraguas roto.» ¿Qué dibujo muestra lo que probablemente pasó?", ["Llovió con mucho viento", "Hizo mucho sol", "Nevó en la playa"], 0,
                     "Empapada y paraguas roto son pistas de lluvia fuerte o viento.", C2, 1, emojis=["🌧️💨", "☀️😎", "❄️🏖️"], layout="images"),
                 mcq("Luis salió al patio y vio el suelo mojado y a los vecinos con los paraguas cerrados. ¿Qué se puede inferir?", ["Que va a llover pronto.", "Que acababa de llover.", "Que habrá un incendio.", "Que hay una fiesta."], 1, "Suelo mojado y paraguas ya cerrados indican que la lluvia terminó hace poco.", C2, 2, scene="☔"),
                 tf("Una inferencia debe poder justificarse con pistas del texto.", True, "Si no hay pistas, solo es una suposición.", C2, 1),
                 order("Ordena los pasos para hacer una inferencia.", ["Lee el texto y busca pistas", "Piensa qué sabes del tema", "Une las pistas con lo que sabes", "Escribe tu inferencia y justifícala"],
                       "Primero se buscan pistas, luego se usa lo que ya sabemos y al final se justifica la conclusión.", C2, 2, scene="🔎")]}]},
        {"title": "Las palabras nuevas", "lessons": [
            {"title": "Significado por contexto", "est": 12,
             "summary": "El contexto (las palabras y frases cercanas) ofrece pistas para entender una palabra que no conocemos.",
             "blocks": [
                 scene("🔍 📖 💡", "Si no conoces una palabra, las frases de alrededor te dan pistas para descubrirla."),
                 text("Las pistas de alrededor", "Cuando encuentres una palabra nueva, **no te detengas**: lee la frase completa y las cercanas. Pueden dar una **definición**, un **ejemplo**, un **sinónimo** o un **contraste**."),
                 example("Palabra desconocida", "«El agua del río es tan cristalina que se ven los peces del fondo.» ¿Qué significa «cristalina»?",
                         ["Lee la frase: se ven los peces del fondo.", "Eso solo pasa si el agua es transparente.", "Prueba el significado y comprueba que la frase tenga sentido."], "Cristalina significa clara y transparente."),
                 mistakes("Elegir un significado solo porque se parece a una palabra conocida.", "No comprobar si el significado elegido encaja en la frase."),
                 cards(("Pista de definición", "El texto explica la palabra directamente."), ("Pista de ejemplo", "Se presentan ejemplos de lo que significa."), ("Pista de contraste", "Se opone a otra idea, lo que ayuda a deducir su sentido."))],
             "quiz": [
                 mcq("«Fue un gesto altruista: ayudó a todos sin pedir nada a cambio.» ¿Qué significa «altruista»?", ["Que piensa solo en sí mismo", "Que ayuda a otros sin esperar recompensa", "Que es muy rápido", "Que no habla"], 1, "La frase lo explica: ayudó sin pedir nada a cambio.", C3, 2, scene="🤝"),
                 mcq("«El guepardo es veloz: recorre grandes distancias en pocos segundos.» ¿Qué dibujo representa la palabra «veloz»?", ["Un guepardo corriendo", "Una tortuga", "Una piedra"], 0,
                     "Recorrer grandes distancias en pocos segundos indica rapidez.", C3, 1, emojis=["🐆💨", "🐢", "🪨"], layout="images"),
                 tf("Las palabras cercanas a una palabra nueva pueden darnos pistas sobre su significado.", True, "Ese es justo el valor del contexto.", C3, 1),
                 match("Arrastra cada palabra a su significado.", [["altruista", "ayuda sin pedir nada"], ["locuaz", "muy hablador"], ["árido", "seco"], ["efímero", "dura poco"]],
                       "Cada palabra se puede deducir con pistas del contexto.", C3, 2),
                 order("Ordena las palabras para formar una oración.", ["Los", "peces", "nadan", "en", "el", "río"], "La oración correcta es: «Los peces nadan en el río».", C3, 1, scene="🐟")]}]}],
    "final": [
        mcq("Lee: «Las bicicletas no contaminan, mejoran la salud y ahorran dinero. Por eso, usarlas en la ciudad es una buena decisión.» ¿Cuál es la idea principal?", ["Las bicicletas ahorran dinero.", "Usar bicicleta en la ciudad es una buena decisión.", "Las bicicletas mejoran la salud.", "La ciudad tiene tráfico."], 1,
            "Las ventajas son detalles que apoyan la idea principal, que está en la última oración.", C1, 2, scene="🚲"),
        mcq("«Mateo llegó a casa con las rodillas raspadas y la bicicleta torcida.» ¿Qué se puede inferir?", ["Que se cayó de la bicicleta.", "Que ganó una carrera.", "Que vendió la bicicleta.", "Que estaba dormido."], 0,
            "Rodillas raspadas y bicicleta torcida son pistas de una caída.", C2, 2, scene="🚲💥"),
        mcq("«El desierto es un lugar árido: casi nunca llueve y hay muy poca vegetación.» ¿Qué significa «árido»?", ["Muy húmedo", "Seco, con poca agua", "Muy frío", "Lleno de ríos"], 1,
            "La frase explica que casi nunca llueve y casi no hay plantas: seco.", C3, 2, scene="🏜️"),
        short("Completa con una palabra: algo «transparente» deja pasar la luz, así que se puede ver a ____ de él.", ["traves", "través"], "Algo transparente permite ver a través de él.", C3, 2),
        match("Arrastra cada palabra a su significado.", [["cristalino", "transparente"], ["escaso", "poco abundante"], ["veloz", "rápido"], ["enorme", "muy grande"]],
              "Son sinónimos o definiciones cercanas.", C3, 2),
        order("Ordena las palabras para formar una oración.", ["Usar", "bicicleta", "cuida", "el", "ambiente"], "La oración correcta es: «Usar bicicleta cuida el ambiente».", C1, 2, scene="🌎")],
}
