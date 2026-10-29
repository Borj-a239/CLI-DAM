# Diccionario de palabras clave del detector de `dam start`.
#
# EDÍTALO A TU GUST: añade/quita términos o cambia pesos.
# Cada entrada: tipo_de_plantilla -> lista de pistas.
# Cada pista es una cadena (peso 1.0) o un par ("cadena", peso).
# Las pistas se comparan SIN acentos y en minúsculas.
#
# Tipos válidos: cuestionario, html, css, sql, js, java, calc, base.
# (css se considera un extra de html; ambos activan la plantilla web).

KEYWORD_RULES = {
    "cuestionario": [
        "cuestionario",
        "cuestionari",
        "test de",
        "preguntas",
        "responde",
        "respon",
        "contestar",
        "verdadero o falso",
        "relaciona",
        ("?", 0.2),
        ("¿", 0.6),
    ],
    "html": [
        "html",
        ("página web", 1.5),
        ("pagina web", 1.5),
        ("web", 0.8),
        "index.html",
        "etiquetas",
        "hipervínculo",
        ("hipervinculo", 1.0),
        "encabezado",
        "cabecera",
        "nav",
        "footer",
        "header",
        "main",
        "pie de página",
    ],
    "css": [
        "css",
        "hoja de estilos",
        "estilos",
        "colores",
        "fondo",
        "margen",
        "padding",
        "selectores",
    ],
    "sql": [
        "sql",
        "select",
        "from",
        "where",
        "create table",
        "insert into",
        "inner join",
        "left join",
        "group by",
        "ordenar por",
        ("consulta", 0.6),
    ],
    "js": [
        "javascript",
        "js",
        ("función", 1.2),
        ("funcion", 1.2),
        "addeventlistener",
        "getElementById",
        "onclick",
        "script",
        "alert(",
        "variable",
    ],
    "java": [
        "java",
        "java-sdk",
        (".java", 0.5),
        "jdk",
        ("clase", 0.8),
        ("método", 0.8),
        ("metodo", 0.8),
        ("objeto", 0.8),
        ("atributo", 0.8),
        "herencia",
        "polimorfismo",
        "abstracta",
        ("interface", 0.6),
        "getter",
        "setter",
    ],
    "calc": [
        "hoja de cálculo",
        ("hoja de calculo", 1.2),
        "hoja electronica",
        ("excel", 0.6),
        "celda",
        "celdas",
        "fórmula",
        ("formula", 1.2),
        "suma()",
        "promedio",
        "media(",
        "columnas",
        ("tabla de datos", 0.8),
    ],
    "base": [
        "access",
        "base de datos",
        ("base de dades", 1.2),
        "database",
        ".accdb",
        ".odb",
        "tablas",
        "campo",
        "registros",
        "formulario",
        "consulta guardada",
        "primary key",
        "clave primaria",
        "relaciones",
    ],
}

# Orden de desempate cuando dos plantillas empatan a puntuación
# (la que aparece primero gana).
TYPE_PRIORITY = ["java", "sql", "base", "calc", "js", "html", "css", "cuestionario"]

# Extensiones reconocidas por el fallback regex \.(\w+) sobre el texto del PDF.
# Cualquier otra extensión vista en el PDF también se genera como fichero vacío.
KNOWN_CODE_EXTENSIONS = {
    "php", "py", "c", "h", "cpp", "hpp", "cs", "rb", "go", "rs", "kt", "swift",
    "sh", "bat", "ps1", "txt", "md", "xml", "json", "yml", "yaml", "ini",
    "html", "htm", "css", "js", "ts", "sql", "java", "ods", "odt", "odb",
    "docx", "xlsx", "csv", "html5",
}
