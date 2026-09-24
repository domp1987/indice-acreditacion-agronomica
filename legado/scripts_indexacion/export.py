import sqlite3, json, csv, os, zipfile
c=sqlite3.connect('indice_acreditacion.sqlite'); c.row_factory=sqlite3.Row
q=lambda s,*a:[dict(r) for r in c.execute(s,a)]
abet=q("""SELECT n.id,n.codigo,n.nombre,n.tipo,n.descripcion,p.codigo padre FROM nodo n LEFT JOIN nodo p ON p.id=n.padre_id WHERE n.marco_id=2 ORDER BY n.orden""")
for a in abet:
    a['ev']=q("""SELECT e.codigo,en.rol,en.origen FROM evidencia_nodo en JOIN evidencia e ON e.id=en.evidencia_id WHERE en.nodo_id=? AND en.estado<>'descartada' ORDER BY CASE en.rol WHEN 'principal' THEN 0 WHEN 'parcial' THEN 1 ELSE 2 END, e.codigo""",a['id'])
    a['fuentes']=q("""SELECT o.codigo,o.nombre,m.codigo marco,c.tipo,c.nota FROM correspondencia c JOIN nodo o ON o.id=c.origen_id JOIN marco m ON m.id=o.marco_id WHERE c.destino_id=? ORDER BY m.id,o.codigo""",a['id'])
    a['brechas']=q("SELECT titulo,descripcion,severidad,accion,estado FROM brecha WHERE nodo_id=?",a['id'])
    a['indicadores']=q("SELECT i.codigo,i.nombre FROM indicador_nodo x JOIN indicador i ON i.id=x.indicador_id WHERE x.nodo_id=?",a['id'])
cna=q("SELECT n.codigo,n.nombre,n.tipo,p.codigo padre FROM nodo n LEFT JOIN nodo p ON p.id=n.padre_id WHERE n.marco_id=1 ORDER BY n.orden")
ev=q("SELECT id,codigo,titulo,tipo,texto,fuente,archivo,pagina FROM evidencia ORDER BY codigo")
tags={}
for r in q("SELECT en.evidencia_id,n.codigo,m.codigo marco,en.rol,en.origen FROM evidencia_nodo en JOIN nodo n ON n.id=en.nodo_id JOIN marco m ON m.id=n.marco_id"):
    tags.setdefault(r['evidencia_id'],[]).append([r['marco'],r['codigo'],r['rol'],r['origen']])
for e in ev:
    e['tags']=tags.get(e.pop('id'),[]); e['texto']=(e['texto'] or '')[:2200]
ind=q("SELECT id,codigo,nombre,unidad FROM indicador")
for i in ind: i['m']=q("SELECT periodo,sede,valor,desagregacion d,nota FROM medicion WHERE indicador_id=? ORDER BY id",i.pop('id'))
data=dict(abet=abet,cna=cna,evidencias=ev,indicadores=ind,
 cursos=q("SELECT nombre,componente_cma,creditos,categoria_abet,confianza,nota FROM curso ORDER BY id"),
 inconsistencias=q("SELECT * FROM v_inconsistencias"),
 normativa=q("""SELECT n.tipo,n.numero,n.anio,n.organo,GROUP_CONCAT(e.codigo) evs FROM normativa n JOIN normativa_mencion m ON m.normativa_id=n.id JOIN evidencia e ON e.id=m.evidencia_id GROUP BY n.id ORDER BY n.anio DESC,n.numero"""),
 brechas=q("SELECT n.codigo nodo,b.titulo,b.descripcion,b.severidad,b.accion,b.estado FROM brecha b JOIN nodo n ON n.id=b.nodo_id ORDER BY CASE b.severidad WHEN 'alta' THEN 0 WHEN 'media' THEN 1 ELSE 2 END"),
 rea=q("SELECT codigo,descripcion FROM nodo WHERE marco_id=3 ORDER BY orden"))
json.dump(data,open('data.json','w'),ensure_ascii=False,separators=(',',':'))
print(os.path.getsize('data.json'))
# CSV por tabla
os.makedirs('csv',exist_ok=True)
for t in ['marco','nodo','correspondencia','evidencia','evidencia_nodo','indicador','medicion','indicador_nodo','curso','curso_outcome','normativa','normativa_mencion','brecha']:
    cur=c.execute(f"SELECT * FROM {t}")
    with open(f'csv/{t}.csv','w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f); w.writerow([d[0] for d in cur.description]); w.writerows(cur.fetchall())
with zipfile.ZipFile('tablas_csv.zip','w',zipfile.ZIP_DEFLATED) as z:
    for fn in sorted(os.listdir('csv')): z.write('csv/'+fn,fn)
