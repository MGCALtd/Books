"""Original book teaching example. Local synthetic headers only; no services."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

HERE=Path(__file__).resolve().parent
def fixture():
 c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
 c.executescript((HERE/'fixture.sql').read_text())
 return c

def reconcile(c):
 findings=[]
 def add(category,side,tenant,order,field='',source='',target='',row_id=None):
  findings.append(dict(category=category,side=side,tenant_id=tenant,order_id=order,
                       field=field,source_value=source,target_value=target,row_id=row_id))
 valid="typeof(tenant_id)='text' AND trim(tenant_id,char(9,10,11,12,13,32))<>'' AND typeof(order_id)='text' AND trim(order_id,char(9,10,11,12,13,32))<>''"
 counts={}
 for side in ['source','target']:
  tab=side+'_orders'
  counts[side+'_rows']=c.execute('SELECT COUNT(*) FROM '+tab).fetchone()[0]
  counts[side+'_distinct_valid_keys']=c.execute('SELECT COUNT(*) FROM (SELECT tenant_id,order_id FROM '+tab+' WHERE '+valid+' GROUP BY tenant_id,order_id)').fetchone()[0]
  for r in c.execute('SELECT * FROM '+tab+' WHERE NOT ('+valid+')'):
   add('INVALID_KEY',side,r['tenant_id'],r['order_id'],row_id=r['row_id'])
  for r in c.execute('SELECT tenant_id,order_id,COUNT(*) AS n FROM '+tab+' WHERE '+valid+' GROUP BY tenant_id,order_id HAVING COUNT(*)>1'):
   add('DUPLICATE_'+side.upper(),side,r['tenant_id'],r['order_id'],target=str(r['n']) if side=='target' else '',source=str(r['n']) if side=='source' else '')
  for r in c.execute('SELECT * FROM '+tab):
   for field in ['customer_id','currency','amount_minor']:
    v=r[field]
    if v is None or (isinstance(v,str) and not v.strip('\t\n\v\f\r ')):
     add('REQUIRED_VALUE',side,r['tenant_id'],r['order_id'],field,row_id=r['row_id'])
   if r['amount_minor'] is not None and c.execute('SELECT typeof(amount_minor) FROM '+tab+' WHERE row_id=?',(r['row_id'],)).fetchone()[0]!='integer':
    add('INVALID_AMOUNT_TYPE',side,r['tenant_id'],r['order_id'],'amount_minor',row_id=r['row_id'])
   if side=='source':
    mapped=c.execute('SELECT 1 FROM status_map WHERE source_status=?',(r['status'],)).fetchone()
   else:
    mapped=c.execute('SELECT 1 FROM status_map WHERE target_status=?',(r['status'],)).fetchone()
   if not mapped:add('UNMAPPED_STATUS',side,r['tenant_id'],r['order_id'],'status',row_id=r['row_id'])
 for side,other in [('source','target'),('target','source')]:
  sql=f"""SELECT DISTINCT s.tenant_id,s.order_id FROM {side}_orders s
   WHERE typeof(s.tenant_id)='text' AND trim(s.tenant_id,char(9,10,11,12,13,32))<>''
     AND typeof(s.order_id)='text' AND trim(s.order_id,char(9,10,11,12,13,32))<>''
     AND NOT EXISTS (SELECT 1 FROM {other}_orders t
       WHERE t.tenant_id=s.tenant_id AND t.order_id=s.order_id)"""
  for r in c.execute(sql):add(side.upper()+'_ONLY',side,r['tenant_id'],r['order_id'])
 base=""" FROM source_unique s JOIN target_unique t
          ON t.tenant_id=s.tenant_id AND t.order_id=s.order_id """
 counts['unique_matched_keys']=c.execute('SELECT COUNT(*)'+base).fetchone()[0]
 for field,category in [('customer_id','FIELD_CUSTOMER'),('currency','FIELD_CURRENCY'),('amount_minor','FIELD_AMOUNT')]:
  guard=''
  if field=='amount_minor':
   guard=" AND typeof(s.amount_minor)='integer' AND typeof(t.amount_minor)='integer' AND s.currency=t.currency AND s.currency IS NOT NULL AND trim(s.currency,char(9,10,11,12,13,32))<>''"
  sql=f"SELECT s.tenant_id,s.order_id,s.{field} AS a,t.{field} AS b"+base+f" WHERE s.{field} IS NOT t.{field}"+guard
  for r in c.execute(sql):add(category,'both',r['tenant_id'],r['order_id'],field,r['a'],r['b'])
 sql="""SELECT s.tenant_id,s.order_id,m.target_status AS a,t.status AS b"""+base+""" JOIN status_map m ON m.source_status=s.status WHERE m.target_status IS NOT t.status"""
 for r in c.execute(sql):add('FIELD_STATUS','both',r['tenant_id'],r['order_id'],'status',r['a'],r['b'])
 findings.sort(key=lambda r:tuple('' if r[k] is None else str(r[k]) for k in ['category','side','tenant_id','order_id','field','row_id']))
 controls={}
 for side in ['source','target']:
  controls[side]=[dict(r) for r in c.execute('SELECT tenant_id,currency,COUNT(*) AS rows,SUM(amount_minor) AS total_minor FROM '+side+"_orders WHERE typeof(amount_minor)='integer' GROUP BY tenant_id,currency ORDER BY tenant_id,currency")]
 return dict(contract='CC-03/header-exercise-1',counts=counts,controls=controls,
             findings=findings,scope='Static synthetic order headers only',
             not_examined=['live-state alignment','line items','attachments','permissions','workflow','recovery'])

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',default='order_reconciliation_run')
 a=ap.parse_args();out=Path(a.output)
 if out.exists():ap.error('Output directory already exists; choose a new directory.')
 c=fixture();result=reconcile(c);out.mkdir(parents=True)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 with (out/'exceptions.csv').open('w',newline='') as f:
  fields=['category','side','tenant_id','order_id','field','source_value','target_value','row_id']
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(result['findings'])
 manifest={'python':sys.version.split()[0],'sqlite':sqlite3.sqlite_version,
           'fixture_sha256':hashlib.sha256((HERE/'fixture.sql').read_bytes()).hexdigest(),
           'query_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 (out/'run_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(f"{len(result['findings'])} findings; {result['counts']['unique_matched_keys']} unique matched keys.")
if __name__=='__main__':main()
