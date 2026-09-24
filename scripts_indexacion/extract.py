import subprocess, re, json, glob, os
out=[]
for f in sorted(glob.glob('/mnt/user-data/uploads/Factor_*.pdf')):
    fac=int(re.search(r'Factor_(\d+)',f).group(1))
    n=int(re.search(r'Pages:\s+(\d+)',subprocess.run(['pdfinfo',f],capture_output=True,text=True).stdout).group(1))
    for p in range(1,n+1):
        t=subprocess.run(['pdftotext','-f',str(p),'-l',str(p),f,'-'],capture_output=True,text=True).stdout
        t=re.sub(r'www\.ucundinamarca\.edu\.co.*','',t)
        m=re.search(r'Caracter[ií]stica\s*(\d+)\.?\s*\n?\s*([^\n]+(?:\n[a-záéíóúñ][^\n]+)?)',t)
        car=int(m.group(1)) if m else None
        name=re.sub(r'\s+',' ',m.group(2)).strip() if m else None
        out.append(dict(factor=fac,archivo=os.path.basename(f),pagina=p,car=car,car_nombre=name,texto=re.sub(r'[ \t]+',' ',re.sub(r'\n\s*\n+','\n',t)).strip()))
json.dump(out,open('slides.json','w'),ensure_ascii=False)
print(len(out))
cars={}
for s in out:
    if s['car']: cars.setdefault(s['car'],set()).add((s['factor'],s['car_nombre']))
for k in sorted(cars): print(k,cars[k])
