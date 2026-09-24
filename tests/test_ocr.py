"""Filtro del texto de OCR: solo se guarda lo que aporta algo que no está en el texto del PDF."""
from indice.ocr import texto_nuevo


def test_guarda_texto_que_solo_esta_en_la_imagen():
    pdf = 'Característica 11.\nDesarrollo profesoral\nCircuitos'
    ocr = ['Característica 11.', 'Desarrollo profesoral', 'CIRCUITO DE', 'FORMACIÓN', 'Circuitos']
    assert texto_nuevo(ocr, pdf) == 'CIRCUITO DE\nFORMACIÓN'


def test_descarta_encabezados_institucionales_y_ruido():
    ocr = ['Universidad de', 'CUNDINAMARCA', 'www.ucundinamarca.edu.co • Vigilada MinEducación', 'OS I D40', 'azo •', '12,5 %  3.4']
    assert texto_nuevo(ocr, '') == ''


def test_ignora_tildes_y_mayusculas_al_comparar():
    assert texto_nuevo(['EVALUACIÓN DE PROFESORES'], 'Evaluacion de profesores') == ''
