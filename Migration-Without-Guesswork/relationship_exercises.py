"""Original synthetic order-line and attachment checks. No network or live permissions."""
from pathlib import Path
import csv,hashlib,json
from reconcile import fixture

def line_example():
 c=fixture()
 c.execute('DELETE FROM target_orders WHERE row_id=4')
 c.execute("INSERT INTO target_orders(tenant_id,order_id,customer_id,status,currency,amount_minor) VALUES('T1','O-104','C4','SETTLED','GBP',5000)")
 c.execute("UPDATE target_orders SET customer_id='C2' WHERE order_id='O-102'")
 c.executescript('CREATE TABLE source_lines(tenant_id TEXT,order_id TEXT,line_id INTEGER,amount_minor INTEGER); CREATE TABLE target_lines(tenant_id TEXT,order_id TEXT,line_id INTEGER,amount_minor INTEGER);')
 rows=[('T1','O-101',1,2000),('T1','O-101',2,2000),
       ('T1','O-102',1,3000),('T1','O-102',2,3000),
       ('T1','O-104',1,5000),('T1','O-105',1,5000)]
 for side in ['source','target']:
  c.executemany(f'INSERT INTO {side}_lines VALUES(?,?,?,?)',rows)
 header=c.execute('SELECT SUM(amount_minor) FROM source_orders').fetchone()[0]
 multiplied=c.execute('SELECT SUM(h.amount_minor) FROM source_orders h JOIN source_lines l ON l.tenant_id=h.tenant_id AND l.order_id=h.order_id').fetchone()[0]
 line_total=c.execute('SELECT SUM(amount_minor) FROM source_lines').fetchone()[0]
 c.execute("UPDATE target_lines SET order_id='O-999' WHERE order_id='O-105'")
 orphans=[list(row) for row in c.execute('SELECT l.tenant_id,l.order_id,l.line_id FROM target_lines l WHERE NOT EXISTS (SELECT 1 FROM target_orders h WHERE h.tenant_id=l.tenant_id AND h.order_id=l.order_id)')]
 return {'source_line_rows':len(rows),'header_total_minor':header,
         'joined_header_total_minor':multiplied,'line_total_minor':line_total,
         'target_orphan_lines':orphans,
         'target_line_total_minor':c.execute('SELECT SUM(amount_minor) FROM target_lines').fetchone()[0]}

def attachment_example():
 here=Path(__file__).resolve().parent
 findings=[]
 with (here/'attachments/manifest.csv').open(newline='') as f:
  for row in csv.DictReader(f):
   name=row['name'];source=(here/'attachments/source'/name).read_bytes()
   target=(here/'attachments/target'/name).read_bytes()
   source_hash=hashlib.sha256(source).hexdigest()
   if source_hash!=row['sha256']:raise ValueError('source manifest disagreement')
   if hashlib.sha256(target).hexdigest()!=row['sha256']:
    findings.append({'name':name,'category':'CONTENT_HASH'})
   if row['owner_customer_id']!=row['target_owner_customer_id']:
    findings.append({'name':name,'category':'OWNER_RELATIONSHIP'})
 return findings

def run():
 return {'lines':line_example(),'attachments':attachment_example(),
         'scope':'fictional data/bytes only; no live attachment-access claim'}

if __name__=='__main__':print(json.dumps(run(),indent=2))
