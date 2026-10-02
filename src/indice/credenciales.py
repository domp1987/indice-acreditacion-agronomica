"""Oculta credenciales (usuario y contraseña) que aparezcan en el texto de las fuentes.

Algunos anexos traen el acceso a la plataforma Moodle ("Usuario: … Contraseña: …"). Nunca deben llegar a la base,
al tablero ni a la versión publicada: se reemplaza el valor y se conserva la etiqueta para que se entienda el texto.
"""
import re

CREDENCIAL = re.compile(r'(?i)\b(usuario|user(?:name)?|contrase(?:ñ|n)a|password|clave(?: de acceso)?)(\s*[:=]\s*)(\S+)')


def ocultar_credenciales(texto):
    if not texto: return texto
    return CREDENCIAL.sub(lambda m: f'{m.group(1)}{m.group(2)}[omitido]', texto)


def ocultar_en_tablas(tablas):
    return [dict(t, filas=[[ocultar_credenciales(c) if isinstance(c, str) else c for c in f] for f in t['filas']]) for t in tablas]
