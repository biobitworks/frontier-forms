#!/usr/bin/env python3
"""Render Synthea synthetic encounter forms as reproducible image fixtures.
Never write gold answers to public input records; private artifacts remain local.
"""
import csv,hashlib,io,json
from zipfile import ZipFile
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

def sh(b):return hashlib.sha256(b).hexdigest()
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def csvrows(z,path):
    text=z.read(path).decode('utf-8-sig')
    return list(csv.DictReader(io.StringIO(text)))

def build_forms(zipfile,out,limit=12):
    zipfile=Path(zipfile);out=Path(out)
    if out.exists() and any(out.iterdir()):raise RuntimeError('REFUSE_OVERWRITE_OUTPUT')
    out.mkdir(parents=True,exist_ok=True)
    source_hash=sh(zipfile.read_bytes())
    with ZipFile(zipfile) as z:
        assert z.testzip() is None,'ZIP_INTEGRITY_FAIL'
        patients=sorted(csvrows(z,'patients.csv'),key=lambda r:r['Id'])
        encounters=sorted(csvrows(z,'encounters.csv'),key=lambda r:r['START'])
    first={}
    for e in encounters:
        first.setdefault(e['PATIENT'],e)
    pub=[];priv=[]
    imgs=out/'forms'; imgs.mkdir(exist_ok=True)
    for p in patients:
        if p['Id'] not in first:continue
        e=first[p['Id']]
        case='fco-form-'+sh((p['Id']+e['Id']+'frontier_forms_v1').encode())[:20]
        fields=[('Synthetic case',case),('Patient first',p['FIRST']),
            ('Patient last',p['LAST']),('Birth date',p['BIRTHDATE']),
            ('Gender',p['GENDER']),('Encounter date',e['START'][:10]),
            ('Visit class',e['ENCOUNTERCLASS'])]
        im=Image.new('RGB',(900,580),'white');draw=ImageDraw.Draw(im)
        font=ImageFont.load_default()
        draw.rectangle((30,24,870,548),outline='black',width=2)
        draw.text((55,48),'SYNTHETIC ENCOUNTER INTAKE — NOT CLINICAL',font=font,fill='black')
        for i,(label,value) in enumerate(fields):
            y=110+i*58
            draw.text((60,y),label+':',font=font,fill='black')
            draw.text((290,y),value,font=font,fill='black')
            draw.line((290,y+22,840,y+22),fill='#999999',width=1)
        buf=io.BytesIO();im.save(buf,format='PNG')
        raw=buf.getvalue();(imgs/(case+'.png')).write_bytes(raw)
        pub.append({'case_id':case,'input_fco_id':'fco:'+sh(raw),
            'occurrence_id':sh(canon({'case':case,'source':source_hash,'template':'intake-v1'})),
            'png_relative_path':'forms/'+case+'.png','png_sha256':sh(raw),
            'model_access':'IMAGE_ONLY','oracle_visibility':'PRIVATE'})
        priv.append({'case_id':case,'gold_fields':dict(fields),
            'synthetic_source_record_hash':sh(canon({'patient':p['Id'],'encounter':e['Id']}))})
        if len(pub)>=limit:break
    if len(pub)<limit:raise ValueError('INSUFFICIENT_SYNTHETIC_PATIENTS')
    (out/'inputs.jsonl').write_bytes(b''.join(canon(r)+b'\n' for r in pub))
    private=out/'.private';private.mkdir(exist_ok=True)
    (private/'oracle.jsonl').write_bytes(b''.join(canon(r)+b'\n' for r in priv))
    receipt={'schema':'fco.forms.fixture.v1','source_sha256':source_hash,'case_count':len(pub),
       'public_inputs_sha256':sh((out/'inputs.jsonl').read_bytes()),
       'private_oracle_sha256':sh((private/'oracle.jsonl').read_bytes()),
       'render_recipe':'Pillow '+__import__('PIL').__version__,
       'clinical_ehr_write':'PROHIBITED','ocr_evaluation':'NOT_TESTED',
       'is_synthetic':True}
    (out/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    return receipt
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--source',required=True)
    p.add_argument('--out',required=True);p.add_argument('--limit',type=int,default=12)
    a=p.parse_args();print(json.dumps(build_forms(a.source,a.out,a.limit),sort_keys=True))
