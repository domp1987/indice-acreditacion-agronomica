import sqlite3, json, re, os
DB='indice_acreditacion.sqlite'
if os.path.exists(DB): os.remove(DB)
con=sqlite3.connect(DB); cur=con.cursor()
cur.executescript(open('schema.sql').read())

# ---------- Marcos ----------
cur.executemany("INSERT INTO marco(id,codigo,nombre,version,descripcion) VALUES (?,?,?,?,?)",[
 (1,'CNA','Consejo Nacional de Acreditación - programas','Acuerdo 02 de 2020','12 factores y 48 características'),
 (2,'ABET-EAC','ABET Engineering Accreditation Commission','Criterios 2026-2027','8 criterios generales de pregrado; textos parafraseados, verificar contra el documento oficial'),
 (3,'REA-IA','Resultados de aprendizaje del programa','Documento maestro 2019','5 REA de Ingeniería Agronómica'),
])
def add_node(marco,codigo,nombre,tipo,padre=None,orden=None,desc=None):
    pid=None
    if padre: pid=cur.execute("SELECT id FROM nodo WHERE marco_id=? AND codigo=?",(marco,padre)).fetchone()[0]
    cur.execute("INSERT INTO nodo(marco_id,codigo,nombre,descripcion,tipo,padre_id,orden) VALUES (?,?,?,?,?,?,?)",(marco,codigo,nombre,desc,tipo,pid,orden))
    return cur.lastrowid
def nid(marco,codigo): return cur.execute("SELECT id FROM nodo WHERE marco_id=? AND codigo=?",(marco,codigo)).fetchone()[0]

# ---------- CNA ----------
factores={1:'Proyecto educativo del programa e identidad institucional',2:'Estudiantes',3:'Profesores',4:'Egresados',
5:'Aspectos académicos y resultados de aprendizaje',6:'Permanencia y graduación',7:'Interacción con el entorno nacional e internacional',
8:'Aportes de la investigación, la innovación, el desarrollo tecnológico y la creación',9:'Bienestar de la comunidad académica del programa',
10:'Medios educativos y ambientes de aprendizaje',11:'Organización, administración y financiación del programa académico',12:'Recursos físicos y tecnológicos'}
car={1:(1,'Proyecto educativo del programa'),2:(1,'Relevancia académica y pertinencia social del programa'),
3:(2,'Participación en actividades de formación integral'),4:(2,'Orientación y seguimiento a estudiantes'),5:(2,'Capacidad de trabajo autónomo'),
6:(2,'Reglamento estudiantil y política académica'),7:(2,'Estímulos y apoyos para estudiantes'),
8:(3,'Selección, vinculación y permanencia'),9:(3,'Estatuto profesoral'),10:(3,'Número, dedicación, nivel de formación y experiencia'),
11:(3,'Desarrollo profesoral'),12:(3,'Estímulos a la trayectoria profesoral'),13:(3,'Producción, pertinencia, utilización e impacto de material docente'),
14:(3,'Remuneración por méritos'),15:(3,'Evaluación de profesores'),16:(4,'Seguimiento a graduados'),17:(4,'Impacto de los graduados en el medio social y académico'),
18:(5,'Integralidad de los aspectos curriculares'),19:(5,'Flexibilidad de los aspectos curriculares'),20:(5,'Interdisciplinariedad'),
21:(5,'Estrategias pedagógicas'),22:(5,'Sistema de evaluación de estudiantes'),23:(5,'Resultados de aprendizaje'),24:(5,'Competencias'),
25:(5,'Evaluación y autorregulación del programa'),26:(5,'Vinculación e interacción social'),
27:(6,'Políticas, estrategias y estructura para la permanencia y la graduación'),28:(6,'Caracterización de estudiantes y sistema de alertas tempranas'),
29:(6,'Ajustes a los aspectos curriculares'),30:(6,'Mecanismos de selección'),
31:(7,'Inserción del programa en contextos académicos nacionales e internacionales'),32:(7,'Relaciones externas de profesores y estudiantes'),
33:(7,'Habilidades comunicativas en una segunda lengua'),34:(8,'Formación para la investigación, el desarrollo tecnológico, la innovación y la creación'),
35:(8,'Compromiso con la investigación, el desarrollo tecnológico, la innovación y la creación'),36:(9,'Programas y servicios'),37:(9,'Participación y seguimiento'),
38:(10,'Estrategias y recursos de apoyo a profesores'),39:(10,'Estrategias y recursos de apoyo a estudiantes'),40:(10,'Recursos bibliográficos y de información'),
41:(11,'Organización y administración'),42:(11,'Dirección y gestión'),43:(11,'Sistemas de comunicación e información'),44:(11,'Estudiantes y capacidad institucional'),
45:(11,'Financiación del programa'),46:(11,'Aseguramiento de la alta calidad y mejora continua'),
47:(12,'Recursos de infraestructura física y tecnológica'),48:(12,'Recursos informáticos y de comunicación')}
for f,n in factores.items(): add_node(1,f'F{f:02d}',n,'factor',orden=f*100)
for c,(f,n) in car.items(): add_node(1,f'C{c:02d}',n,'caracteristica',padre=f'F{f:02d}',orden=f*100+c)

# ---------- ABET EAC (parafraseado) ----------
o=0
def A(codigo,nombre,tipo,padre=None,desc=None):
    global o; o+=1; add_node(2,codigo,nombre,tipo,padre,o,desc)
A('C1','Estudiantes','criterio',desc='Evaluación y seguimiento del desempeño, consejería, políticas de admisión, transferencia y homologación, verificación de requisitos de grado.')
A('C2','Objetivos educacionales del programa (PEOs)','criterio',desc='Objetivos publicados, coherentes con la misión y las necesidades de los grupos de interés, con proceso documentado de revisión periódica.')
A('C3','Resultados de los estudiantes (Student Outcomes)','criterio',desc='Resultados 1 a 7 más los que defina el programa, con proceso documentado de revisión.')
for i,(n,d) in enumerate([
 ('Resolver problemas complejos de ingeniería','Identificar, formular y resolver problemas complejos aplicando principios de ingeniería, ciencia y matemáticas.'),
 ('Diseño de ingeniería','Aplicar diseño de ingeniería para producir soluciones a necesidades específicas considerando salud, seguridad, bienestar y factores globales, culturales, sociales, ambientales y económicos.'),
 ('Comunicación efectiva','Comunicarse efectivamente con públicos diversos.'),
 ('Ética y responsabilidad profesional','Reconocer responsabilidades éticas y profesionales y emitir juicios informados considerando impactos globales, económicos, ambientales y sociales.'),
 ('Trabajo en equipo','Funcionar eficazmente en equipos que colaboran, lideran, fijan metas, planifican y cumplen objetivos.'),
 ('Experimentación y análisis de datos','Diseñar y conducir experimentación, analizar e interpretar datos y usar juicio ingenieril para concluir.'),
 ('Aprendizaje autónomo','Adquirir y aplicar nuevo conocimiento según se necesite, con estrategias de aprendizaje apropiadas.')],1):
    A(f'SO{i}',n,'outcome','C3',d)
A('C4','Mejora continua','criterio',desc='Procesos documentados y aplicados de evaluación y valoración del logro de los Student Outcomes, cuyos resultados se usan para mejorar el programa.')
A('C5','Currículo','criterio',desc='Contenido adecuado en cada área, coherente con PEOs y Student Outcomes.')
A('C5a','Matemáticas y ciencias básicas (mínimo 30 créditos semestrales)','subcriterio','C5')
A('C5b','Temas de ingeniería (mínimo 45 créditos semestrales)','subcriterio','C5',desc='Ciencias de la ingeniería y diseño de ingeniería, con uso de herramientas modernas.')
A('C5c','Componente de educación amplia','subcriterio','C5')
A('C5d','Experiencia de diseño mayor (culminante)','subcriterio','C5',desc='Proyecto de diseño que integra conocimientos previos, con estándares y restricciones múltiples, obligatorio para todos.')
A('C6','Profesores','criterio',desc='Número suficiente, competencias para cubrir todas las áreas, continuidad y estabilidad, autoridad sobre el programa.')
A('C7','Instalaciones','criterio',desc='Aulas, laboratorios y equipos adecuados para el logro de los Student Outcomes, incluida la seguridad.')
A('C8','Apoyo institucional','criterio')
for k,n in [('a','Calidad y continuidad del programa'),('b','Atraer, retener y desarrollar profesores'),('c','Infraestructura y equipos'),('d','Ambiente respetuoso')]:
    A(f'C8{k}',n,'subcriterio','C8')
A('PC','Criterios específicos del programa (por confirmar con ABET)','criterio')

# ---------- REA del programa ----------
rea=[('REA1','Aplicar coherentemente herramientas comunicativas en procesos de interacción social, con sentido crítico y transformador del entorno.'),
('REA2','Aplicar herramientas matemáticas que faciliten el análisis, diseño, seguimiento y evaluación de sistemas productivos e investigativos.'),
('REA3','Desempeñarse honestamente como persona con principios, valores, actitudes y comportamientos propios del profesional UCundinamarca.'),
('REA4','Identificar y analizar conceptos, funcionalidad y elementos biológicos de un sistema de producción agrícola y sus interacciones.'),
('REA5','Liderar ética y solidariamente procesos de transformación de las comunidades, con alternativas viables y respetuosas del ambiente y la multiculturalidad.')]
for i,(c,d) in enumerate(rea,1): add_node(3,c,c,'rea',orden=i,desc=d)

# ---------- Correspondencias ----------
cmap={1:[('C2','parcial'),('C5','apoyo')],2:[('C2','parcial')],3:[('SO5','apoyo'),('C1','apoyo')],4:[('C1','equivalente')],
5:[('SO7','parcial')],6:[('C1','equivalente')],7:[('C8','apoyo')],8:[('C6','parcial'),('C8b','apoyo')],9:[('C6','apoyo')],
10:[('C6','equivalente')],11:[('C8b','parcial'),('C6','apoyo')],12:[('C8b','apoyo')],13:[('C6','apoyo')],14:[('C8b','apoyo')],
15:[('C6','parcial')],16:[('C2','parcial')],17:[('C2','parcial')],18:[('C5','parcial')],19:[('C1','parcial')],20:[('SO5','apoyo')],
21:[('C5','apoyo')],22:[('C1','parcial'),('C4','apoyo')],23:[('C3','parcial'),('C4','parcial')],24:[('C3','apoyo')],25:[('C4','parcial')],
26:[('SO4','apoyo')],27:[('C1','equivalente')],28:[('C1','equivalente')],29:[('C5','apoyo'),('C4','apoyo')],30:[('C1','equivalente')],
31:[('SO4','apoyo')],32:[('C6','apoyo')],33:[('SO3','apoyo')],34:[('SO6','parcial')],35:[('C6','apoyo')],36:[('C8d','parcial'),('C1','apoyo')],
37:[('C1','apoyo')],38:[('C8b','apoyo')],39:[('C7','parcial')],40:[('C7','parcial')],41:[('C8','parcial')],42:[('C8a','parcial')],
43:[('C8','apoyo')],44:[('C8','parcial'),('C6','apoyo')],45:[('C8','equivalente')],46:[('C4','parcial')],47:[('C7','equivalente'),('C8c','parcial')],48:[('C7','parcial')]}
for c,lst in cmap.items():
    for dest,t in lst:
        cur.execute("INSERT INTO correspondencia(origen_id,destino_id,tipo) VALUES (?,?,?)",(nid(1,f'C{c:02d}'),nid(2,dest),t))
for r,dest,t,nota in [('REA1','SO3','equivalente',None),('REA2','SO1','parcial','Cubre herramientas matemáticas, no problemas complejos de ingeniería'),
 ('REA2','SO2','parcial','Menciona diseño pero sin proceso de diseño de ingeniería'),('REA3','SO4','parcial',None),('REA4','SO1','parcial','Conocimiento biológico, no resolución de problemas de ingeniería'),
 ('REA5','SO5','parcial',None),('REA5','SO4','apoyo',None)]:
    cur.execute("INSERT INTO correspondencia(origen_id,destino_id,tipo,nota) VALUES (?,?,?,?)",(nid(3,r),nid(2,dest),t,nota))

# ---------- Evidencias desde las diapositivas ----------
slides=json.load(open('slides.json'))
def titulo_de(s):
    lines=[l.strip() for l in s['texto'].split('\n') if l.strip()]
    skip=re.compile(r'^(Caracter[ií]stica|Fuente|FACTOR|Factor \d|Ingenier[ií]a$|Agron[oó]mica$|Acreditaci[oó]n de Alta|Sede Fusa|ALD Faca|Universidad de|CUNDINAMARCA)',re.I)
    name=(s['car_nombre'] or '').lower()
    for l in lines:
        if skip.search(l) or len(l)<14 or l.lower() in name or name.startswith(l.lower()): continue
        if re.fullmatch(r'[\d\s%.,$]+',l): continue
        return l[:110]
    return s['car_nombre'] or 'Diapositiva'
car_actual=None; ev_by_page={}
for s in slides:
    t=s['texto']; up=t.upper()
    if len(t)<120 and ('Acreditación de Alta Calidad' in t or re.search(r'FACTOR\s*\d+\s*$',t.split('\n')[0] if t else '')):
        continue
    if re.match(r'^\s*FACTOR\s*\d+\s*\n',t) and len(t)<200: continue
    if 'VALORACIÓN INTERPRETATIVA' in up or 'VALORACIÓN INTERPRETATIVA DE LA CALIDAD' in up or ('Valoración Interpretativa' in t):
        tipo='valoracion'; titulo=f'Valoración interpretativa del factor {s["factor"]}'
    elif 'LOGROS E' in up and 'IMPACTO' in up:
        tipo='logros'; titulo=f'Logros e impacto del factor {s["factor"]}'
    elif 'PLAN DE' in up and 'MEJORAMIENTO' in up and 'Avance' in t:
        tipo='plan_mejora'; titulo=f'Avance en el plan de mejoramiento, factor {s["factor"]}'
    else:
        tipo='diapositiva'; sub=titulo_de(s)
        good = sub and len(sub)>=18 and sub[0].isupper() and not sub.rstrip().endswith((',',' que',' de',' y')) and sub!=s['car_nombre']
        if s['car_nombre']:
            titulo = f"{s['car_nombre'].rstrip('.')}: {sub}" if good else s['car_nombre'].rstrip('.')
        else:
            titulo = sub if good else f"Factor {s['factor']}, diapositiva {s['pagina']}"
    sede='Programa'
    has_f='Fusagasug' in t; has_fa='Facatativ' in t
    code=f'F{s["factor"]:02d}-P{s["pagina"]:03d}'
    fuentes=re.findall(r'Fuente[.:]\s*([^\n]{3,80})',t)
    cur.execute("INSERT INTO evidencia(codigo,titulo,tipo,texto,fuente,archivo,pagina,sede) VALUES (?,?,?,?,?,?,?,?)",
        (code,titulo,tipo,t,fuentes[0].strip() if fuentes else None,s['archivo'],s['pagina'],sede))
    eid=cur.lastrowid; ev_by_page[(s['factor'],s['pagina'])]=eid
    # etiquetado CNA
    if s['car']:
        cur.execute("INSERT OR IGNORE INTO evidencia_nodo VALUES (?,?,?,?,?)",(eid,nid(1,f'C{s["car"]:02d}'),'principal','extraccion','validada'))
    else:
        cur.execute("INSERT OR IGNORE INTO evidencia_nodo VALUES (?,?,?,?,?)",(eid,nid(1,f'F{s["factor"]:02d}'),'principal','extraccion','validada'))
        if tipo=='plan_mejora':
            cur.execute("INSERT OR IGNORE INTO evidencia_nodo VALUES (?,?,?,?,?)",(eid,nid(2,'C4'),'apoyo','inferida','propuesta'))

# Reproyección: etiquetas CNA -> ABET vía correspondencia
rolmap={'equivalente':'principal','parcial':'parcial','apoyo':'apoyo'}
rows=cur.execute("""SELECT en.evidencia_id, c.destino_id, c.tipo FROM evidencia_nodo en
  JOIN correspondencia c ON c.origen_id=en.nodo_id JOIN nodo d ON d.id=c.destino_id
  WHERE d.marco_id=2""").fetchall()
for eid,dest,t in rows:
    cur.execute("INSERT OR IGNORE INTO evidencia_nodo VALUES (?,?,?,?,?)",(eid,dest,rolmap[t],'inferida','propuesta'))

# ---------- Normativa ----------
pat=re.compile(r'(Acuerdo|Resoluci[oó]n)\b([^\n]{0,60}?)(?:N[o°º]\.?\s*|N\.\s*)?(\d{3,6})\s+(?:del?\s+)?(?:\d{1,2}\s+de\s+[a-zA-Z]+\s+(?:de\s+)?)?(\d{4})',re.I)
excluir={('Acuerdo',88,2023),('Acuerdo',17,2024),('Resolución',2004,2013)}
for (f,p),eid in ev_by_page.items():
    t=re.sub(r'\s+',' ',[s for s in slides if s['factor']==f and s['pagina']==p][0]['texto'])
    for m in pat.finditer(t):
        tipo='Acuerdo' if m.group(1).lower().startswith('acu') else 'Resolución'
        num,anio=int(m.group(3)),int(m.group(4))
        if (tipo,num,anio) in excluir or anio<1990 or anio>2026: continue
        ctx=m.group(0)
        org='Consejo Superior' if re.search(r'Superior|C\.?\s?S\b|CSU|CS\b',ctx) else 'Consejo Académico' if re.search(r'Acad[eé]mico|C\.?\s?A\b',ctx) else 'Rectoría' if 'Rector' in ctx else None
        cur.execute("INSERT OR IGNORE INTO normativa(tipo,numero,anio,organo) VALUES (?,?,?,?)",(tipo,num,anio,org))
        if org: cur.execute("UPDATE normativa SET organo=COALESCE(organo,?) WHERE tipo=? AND numero=? AND anio=?",(org,tipo,num,anio))
        doc=cur.execute("SELECT id FROM normativa WHERE tipo=? AND numero=? AND anio=?",(tipo,num,anio)).fetchone()[0]
        cur.execute("INSERT OR IGNORE INTO normativa_mencion VALUES (?,?)",(doc,eid))
for tipo,num,anio,org,kw in [('Acuerdo',11,2019,'Consejo Superior','Acuerdo 011 Abril de 2019'),('Acuerdo',12,2024,None,'Acuerdo 012 de 9 Julio 2024'),('Acuerdo',17,2019,None,'Acuerdo 000017')]:
    cur.execute("INSERT OR IGNORE INTO normativa(tipo,numero,anio,organo) VALUES (?,?,?,?)",(tipo,num,anio,org))
    doc=cur.execute("SELECT id FROM normativa WHERE tipo=? AND numero=? AND anio=?",(tipo,num,anio)).fetchone()[0]
    for (f,p),eid in ev_by_page.items():
        if kw in [s for s in slides if s['factor']==f and s['pagina']==p][0]['texto']:
            cur.execute("INSERT OR IGNORE INTO normativa_mencion VALUES (?,?)",(doc,eid))

# ---------- Indicadores ----------
def ev(f,kw):
    for s in slides:
        if s['factor']==f and kw in s['texto']: return ev_by_page.get((f,s['pagina']))
def ind(codigo,nombre,unidad,nodos,desc=None):
    cur.execute("INSERT INTO indicador(codigo,nombre,unidad,descripcion) VALUES (?,?,?,?)",(codigo,nombre,unidad,desc)); i=cur.lastrowid
    for n,rol in nodos: cur.execute("INSERT INTO indicador_nodo VALUES (?,?,?)",(i,nid(*n),rol))
    return i
def med(i,serie,sede='Programa',evid=None,nota=None):
    for p,v in serie: cur.execute("INSERT INTO medicion(indicador_id,periodo,sede,valor,evidencia_id,nota) VALUES (?,?,?,?,?,?)",(i,p,sede,v,evid,nota))
sem=['2020-1','2020-2','2021-1','2021-2','2022-1','2022-2','2023-1','2023-2','2024-1','2024-2','2025-1','2025-2']
e=ev(6,'Tasa de \ndeserción')
i=ind('RET','Tasa de retención','%',[((1,'C27'),'principal'),((2,'C1'),'principal')]); med(i,zip(sem,[94.49,93.31,94.87,94.49,94.31,94.07,92.95,96.20,94.65,93.65]),evid=e)
i=ind('DES','Tasa de deserción','%',[((1,'C27'),'principal'),((2,'C1'),'principal')]); med(i,zip(sem,[5.51,6.69,5.13,5.51,5.69,5.93,7.05,3.80,5.35,6.35]),evid=e)
e=ev(6,'Relación de graduados')
i=ind('GRAD','Graduados por periodo','personas',[((1,'C16'),'principal'),((2,'C1'),'apoyo')])
med(i,zip(sem,[36,49,36,33,36,33,40,46,32,20,26,14]),'Fusagasugá',e); med(i,zip(sem,[29,24,25,13,32,21,19,40,36,30,38,25]),'Facatativá',e)
i=ind('GRAD_ACUM','Tasa de graduación acumulada (cohorte 2015-1)','%',[((1,'C27'),'principal'),((2,'C1'),'principal')])
e6=ev(6,'32,9% en S12'); e4=ev(4,'18,7% en S12')
med(i,[('S12',32.9),('S13',39.4),('S14',44.3)],evid=e6,nota='Factor 6')
med(i,[('S12',18.71),('S14',34.33)],evid=e4,nota='Factor 4')
i=ind('GRAD_ACUM_NBC','Graduación acumulada, media nacional NBC Agronomía','%',[((2,'C1'),'apoyo')])
med(i,[('S12',25.1),('S13',28.1),('S14',31.1)],evid=e6,nota='Factor 6'); med(i,[('S14',27.45)],evid=e4,nota='Factor 4')
ei=ev(6,'Inscritos')
for nm,cod,fz,fc in [('Inscritos','INSC',[90,45,76,96,106,89,92,117,132,104,122,96],[103,52,118,149,134,115,116,119,158,104,147,130]),
                     ('Admitidos','ADM',[56,42,40,41,41,40,44,41,49,41,43,43],[41,36,39,35,40,40,41,42,50,43,44,42]),
                     ('Matriculados primer curso','PRIM',[40,33,37,32,36,40,40,40,39,40,40,39],[38,32,34,33,36,40,40,39,39,39,40,40])]:
    i=ind(cod,nm,'personas',[((1,'C30'),'principal'),((2,'C1'),'apoyo')]); med(i,zip(sem,fz),'Fusagasugá',ei); med(i,zip(sem,fc),'Facatativá',ei)
e=ev(5,'alcance de los REA')
sem5=['2023-2','2024-1','2024-2','2025-1','2025-2']
vals={'REA1':[71,75,73,78,72],'REA2':[78,80,81,85,79],'REA3':[75,77,75,75,77],'REA4':[76,77,77,77,78],'REA5':[78,86,85,85,77]}
for r,v in vals.items():
    i=ind(f'ALC_{r}',f'Porcentaje de alcance de {r}','%',[((3,r),'principal'),((1,'C23'),'principal'),((2,'C4'),'apoyo')],'Medición agregada del programa; ABET pide evaluación directa por indicador de desempeño')
    med(i,zip(sem5,v),evid=e)
e=ev(5,'Desempeño Saber Pro')
for cod,nm,v in [('SP_PROG','Saber Pro puntaje global - programa',[143,142,144]),('SP_INST','Saber Pro puntaje global - institución',[145,147,145]),('SP_REF','Saber Pro puntaje global - grupo de referencia NBC',[143,144,145])]:
    i=ind(cod,nm,'puntos',[((1,'C24'),'principal'),((2,'C3'),'apoyo')]); med(i,zip(['2022','2023','2024'],v),evid=e)
e=ev(1,'Programa en Cifras')
i=ind('EST','Estudiantes matriculados','personas',[((1,'C44'),'principal'),((2,'C1'),'apoyo')]); med(i,[('2025-2',318)],'Fusagasugá',e); med(i,[('2025-2',289)],'Facatativá',e)
i=ind('GC','Gestores del conocimiento','personas',[((1,'C10'),'principal'),((2,'C6'),'principal')]); med(i,[('2025-2',30)],'Fusagasugá',e); med(i,[('2025-2',23)],'Facatativá',e)
e=ev(3,'Doctorado')
for cod,nm,v in [('GC_DOC','Gestores con doctorado',16),('GC_MAE','Gestores con maestría',65),('GC_ESP','Gestores con especialización',19)]:
    i=ind(cod,nm,'%',[((1,'C10'),'principal'),((2,'C6'),'principal')]); med(i,[('2025-2',v)],evid=e)
e=ev(11,'Capacidad del programa')
i=ind('GC_PLANTA','Gestores de planta','personas',[((1,'C44'),'principal'),((2,'C6'),'principal'),((2,'C8b'),'apoyo')],'ABET exige continuidad y estabilidad del cuerpo docente')
med(i,[('2025-2',1)],'Fusagasugá',e); med(i,[('2025-2',0)],'Facatativá',e)
i=ind('GC_OCAS','Gestores tiempo completo ocasional','personas',[((1,'C44'),'principal'),((2,'C6'),'principal')])
med(i,[('2025-2',26)],'Fusagasugá',e); med(i,[('2025-2',20)],'Facatativá',e)
e=ev(12,'Tipo de espacio')
i=ind('LABS','Laboratorios','espacios',[((1,'C47'),'principal'),((2,'C7'),'principal')]); med(i,[('2025',26)],'Fusagasugá',e); med(i,[('2025',9)],'Facatativá',e)
i=ind('AREA','Área de la sede','m²',[((1,'C47'),'principal'),((2,'C7'),'apoyo')]); med(i,[('2025',70400)],'Fusagasugá',e); med(i,[('2025',12400)],'Facatativá',e)
e=ev(11,'Ejecución Presupuestal')
i=ind('PPTO','Ejecución presupuestal del programa','COP',[((1,'C45'),'principal'),((2,'C8'),'principal')]); med(i,[('2025',6027854647)],evid=e)
e=ev(1,'80% de empleadores')
i=ind('EMPL','Graduados valorados por empleadores','%',[((1,'C17'),'principal'),((2,'C2'),'apoyo')]); med(i,[('2025',80)],evid=e)
# Valoraciones CNA por característica
val={1:5.0,2:4.1,3:4.0,4:4.0,5:4.0,6:4.5,7:4.0,8:4.5,9:3.7,10:4.5,11:4.3,12:4.5,13:4.2,14:4.5,15:4.5,16:4.0,17:4.7,18:4.7,19:4.8,20:5.0,21:4.7,22:4.0,23:4.3,24:5.0,
25:4.3,26:4.0,27:4.0,28:4.3,29:4.5,30:4.7,31:4.5,32:4.3,33:4.5,34:4.8,35:4.8,36:4.5,37:4.3,38:4.2,39:4.3,40:5.0,41:4.2,42:4.5,43:4.3,44:4.2,45:4.0,46:5.0,47:4.3,48:4.3}
i=ind('CNA_VAL','Valoración CNA de la característica (autoevaluación)','escala 0-5',[])
for c,v in val.items():
    cur.execute("INSERT INTO medicion(indicador_id,periodo,sede,valor,desagregacion) VALUES (?,?,?,?,?)",(i,'2025','Programa',v,f'C{c:02d}'))

# ---------- Plan de estudios ----------
cursos=[
# Campo de aprendizaje institucional (27)
*[(n,'Institucional',c,'educacion_general','alta',None) for n,c in [('Razonamiento argumentativo',2),('Ciencia, tecnología e innovación I',2),('Ciencia, tecnología e innovación II',2),('Ciencia, tecnología e innovación III',2),
 ('Comunicación y pensamiento crítico I',2),('Comunicación y pensamiento crítico II',2),('Emprendimiento e innovación I',2),('Emprendimiento e innovación II',2),('Ciudadanía siglo 21',1),
 ('Segunda lengua I',2),('Segunda lengua II',2),('Segunda lengua III',2),('Segunda lengua IV',2),('Cátedra Generación Siglo 21',2)]],
# Ciencias básicas (20)
('Matemática aplicada','Ciencias básicas',3,'matematicas','alta','Único curso de matemáticas; no se evidencia cálculo diferencial e integral'),
('Física','Ciencias básicas',2,'ciencias_basicas','alta','Intensidad baja para un programa de ingeniería'),
('Química','Ciencias básicas',3,'ciencias_basicas','alta',None),('Bioquímica','Ciencias básicas',3,'ciencias_basicas','alta',None),
('Ecología y recursos naturales','Ciencias básicas',3,'ciencias_basicas','media',None),('Morfología y taxonomía vegetal','Ciencias básicas',4,'ciencias_basicas','media',None),
('Topografía','Ciencias básicas',2,'ingenieria','media','Clasificado por el programa como ciencia básica'),
# Ciencias básicas de ingeniería (18)
('Agroclimatología','Ciencias básicas de ingeniería',2,'ingenieria','baja','Validar contenido: puede ser ciencia básica'),
('Geología y pedología','Ciencias básicas de ingeniería',2,'ciencias_basicas','media',None),
('Suelos','Ciencias básicas de ingeniería',3,'ingenieria','baja','Validar si incluye mecánica o física de suelos'),
('Modelos estadísticos aplicados','Ciencias básicas de ingeniería',4,'matematicas','alta',None),
('Biología celular y molecular','Ciencias básicas de ingeniería',4,'ciencias_basicas','alta',None),('Genética','Ciencias básicas de ingeniería',3,'ciencias_basicas','alta',None),
# Ingeniería aplicada (73)
('Introducción a las ciencias agrarias','Ingeniería aplicada',2,'otro','alta',None),
('Hidráulica, riegos y drenajes','Ingeniería aplicada',3,'ingenieria','alta',None),
('Maquinaria y mecanización agrícola','Ingeniería aplicada',2,'ingenieria','alta',None),
('Poscosecha','Ingeniería aplicada',2,'ingenieria','baja','Validar componente de ingeniería de procesos'),
*[(n,'Ingeniería aplicada',c,'otro','media','Ciencia agronómica aplicada') for n,c in [('Fitomejoramiento',3),('Manejo de la fertilidad agrícola',3),('Manejo de arvenses',3),('Microbiología agrícola',3),
 ('Fitopatología',3),('MIPE',4),('Producción de cultivos',4),('Fisiología vegetal',3),('Fisiología de cultivos y semillas',3),('Propagación vegetal',2),('Entomología agrícola',5),('Agroecología',3)]],
('Electiva I','Ingeniería aplicada',2,'por_definir','baja',None),('Electiva II','Ingeniería aplicada',2,'por_definir','baja',None),
('Profundización I','Ingeniería aplicada',5,'por_definir','baja','Líneas SPAS / EDRT'),('Profundización II','Ingeniería aplicada',5,'por_definir','baja','Líneas SPAS / EDRT'),
('Profundización III','Ingeniería aplicada',10,'por_definir','baja','Candidato natural a experiencia de diseño mayor (C5d)'),
('Opción de grado','Ingeniería aplicada',1,'otro','media','Hoy admite monografía, pasantía, especialización u obra artística'),
# Formación complementaria (12)
*[(n,'Formación complementaria',c,'educacion_general','media',None) for n,c in [('Sociología y desarrollo rural',2),('Economía y administración agrícola',2),('Mercadeo agrícola',3),('Extensión rural',3)]],
('Formulación y evaluación de proyectos','Formación complementaria',2,'educacion_general','baja','Podría aportar a diseño (SO2) según contenido')]
cur.executemany("INSERT INTO curso(nombre,componente_cma,creditos,categoria_abet,confianza,nota) VALUES (?,?,?,?,?,?)",cursos)

# ---------- Brechas iniciales ----------
br=[('C5b','Temas de ingeniería muy por debajo del mínimo','Siendo generosos suman 14 créditos frente a 45. La mayor parte de la ingeniería aplicada es ciencia agronómica.','alta','Incluir ciencias de la ingeniería (fluidos, termodinámica, estructuras, maquinaria) en la resignificación del CMA'),
('C5a','Matemáticas insuficientes','Solo 7 créditos de matemáticas (Matemática aplicada y Modelos estadísticos) y 2 de física.','alta','Agregar cálculo diferencial, integral y ecuaciones diferenciales; ampliar física'),
('C5d','No hay experiencia de diseño obligatoria para todos','La opción de grado admite monografía, pasantía, créditos de especialización u obra artística.','alta','Convertir Profundización III en proyecto de diseño integrador obligatorio'),
('C6','Baja estabilidad del cuerpo docente','1 gestor de planta de 53; la mayoría con contratos ocasionales de 4 u 11 meses.','alta','Plan de vinculación de planta ligado al programa'),
('C6','Pocas competencias docentes en ingeniería','El área de ciencias de la ingeniería tiene un magíster en TIG y un especialista en SIG.','alta','Vincular ingenieros agrícolas, civiles o mecánicos con posgrado'),
('C2','No existen objetivos educacionales (PEOs)','Hay misión, visión y perfiles, pero no objetivos a 3-5 años del egreso.','media','Redactar PEOs y validarlos con egresados y empleadores'),
('SO2','Diseño de ingeniería sin resultado de aprendizaje propio','Ningún REA cubre el proceso de diseño de ingeniería.','alta','Reformular REA alineados a los 7 Student Outcomes'),
('SO6','Experimentación sin resultado de aprendizaje propio','Solo evidencia indirecta (semilleros, competencia PC1 de Saber Pro).','media','Definir indicador de desempeño en cursos con laboratorio'),
('SO7','Aprendizaje autónomo sin resultado de aprendizaje propio','Existe la característica CNA de trabajo autónomo, pero no un REA medible.','media','Definir indicador de desempeño'),
('C4','Medición de REA agregada, no directa por indicador','El porcentaje de alcance de REA no equivale a evaluación directa con rúbricas y metas.','media','Rúbricas por indicador de desempeño, metas y actas de cierre del ciclo'),
('C7','Disparidad de infraestructura entre sedes','26 laboratorios en Fusagasugá frente a 9 en Facatativá; 70.400 m² frente a 12.400 m².','media','Demostrar logro equivalente de resultados en ambas sedes'),
('C1','Cifras inconsistentes de graduación acumulada','Factor 6 reporta 44,3% en S14 y Factor 4 reporta 34,3% para la misma medida.','media','Unificar fuente y cohorte de referencia'),
('C1','Falta procedimiento documentado de verificación de requisitos de grado','Existe el reglamento, pero no la auditoría estudiante por estudiante que pide ABET.','baja','Documentar el procedimiento de Admisiones y Registro'),
('PC','Criterios específicos del programa sin confirmar','Por el nombre, podrían aplicar los criterios de ingeniería agrícola.','alta','Consulta formal con ABET antes de la Readiness Review')]
for n,t,d,s,a in br: cur.execute("INSERT INTO brecha(nodo_id,titulo,descripcion,severidad,accion) VALUES (?,?,?,?,?)",(nid(2,n),t,d,s,a))
con.commit()
for q in ["SELECT COUNT(*) FROM evidencia","SELECT COUNT(*) FROM evidencia_nodo","SELECT COUNT(*) FROM normativa","SELECT COUNT(*) FROM medicion","SELECT SUM(creditos) FROM curso","SELECT * FROM v_creditos_abet","SELECT * FROM v_inconsistencias","SELECT codigo,principales,parciales,apoyo,brechas_abiertas FROM v_cobertura_abet"]:
    print(q, cur.execute(q).fetchall())
