"""Synthetic chapter5-8 exercises. No external actions or services."""
from copy import deepcopy
import hashlib,json,math,sqlite3,tempfile
from pathlib import Path

BASE={
 'T1/O-101':dict(customer='C1',amount_minor=4000,currency='GBP'),
 'T1/O-102':dict(customer='C2',amount_minor=6000,currency='GBP'),
 'T1/O-104':dict(customer='C4',amount_minor=5000,currency='GBP'),
 'T1/O-105':dict(customer='C5',amount_minor=5000,currency='GBP')}
EVENTS=[
 dict(position=101,op='upsert',key='T1/O-106',value=dict(customer='C6',amount_minor=2500,currency='GBP')),
 dict(position=102,op='upsert',key='T1/O-102',value=dict(customer='C2',amount_minor=6500,currency='GBP')),
 dict(position=103,op='delete',key='T1/O-104')]
class ChangeState:
 def __init__(self):self.state=deepcopy(BASE);self.applied=100;self.seen={}
 def apply(self,e):
  pos=e['position'];fingerprint=json.dumps(e,sort_keys=True)
  if pos in self.seen:
   if self.seen[pos]!=fingerprint:raise ValueError('Position content conflicts with retained event')
   return 'repeat'
  if pos!=self.applied+1:raise ValueError('Gap in this consecutive teaching log')
  if e['op']=='upsert':self.state[e['key']]=deepcopy(e['value'])
  elif e['op']=='delete':self.state.pop(e['key'],None)
  else:raise ValueError('Unsupported event')
  self.seen[pos]=fingerprint;self.applied=pos;return 'applied'
 def control(self):return dict(position=self.applied,rows=len(self.state),total_minor=sum(x['amount_minor'] for x in self.state.values()))
def boundary_example():
 s=ChangeState();observed=[s.control()]
 for e in EVENTS:s.apply(e);observed.append(s.control())
 return observed
def snapshot_example():
 with tempfile.TemporaryDirectory(prefix='book-snapshot-') as td:
  path=str(Path(td)/'example.sqlite')
  setup=sqlite3.connect(path);setup.execute('PRAGMA journal_mode=WAL')
  setup.execute('CREATE TABLE example(amount_minor INTEGER)')
  setup.execute('INSERT INTO example VALUES(6000)');setup.commit();setup.close()
  reader=sqlite3.connect(path);writer=sqlite3.connect(path)
  try:
   reader.execute('BEGIN')
   a=reader.execute('SELECT amount_minor FROM example').fetchone()[0]
   writer.execute('UPDATE example SET amount_minor=6500');writer.commit()
   b=reader.execute('SELECT amount_minor FROM example').fetchone()[0]
   reader.commit()
   c=reader.execute('SELECT amount_minor FROM example').fetchone()[0]
   return [a,b,c]
  finally:reader.close();writer.close()

def intent_database():
 c=sqlite3.connect(':memory:')
 c.executescript("""CREATE TABLE ledger(
 tenant TEXT,intent TEXT,fingerprint TEXT,result TEXT,
 PRIMARY KEY(tenant,intent));
 CREATE TABLE effects(
 tenant TEXT,intent TEXT,order_id TEXT,customer TEXT,
 currency TEXT,amount_minor INTEGER,UNIQUE(tenant,intent));""")
 return c
INTENT=dict(tenant='T1',intent='INV-102',order_id='O-102',customer='C2',currency='GBP',amount_minor=6000)
def handle_intent(c,payload,fail_after_effect=False):
 required=['tenant','intent','order_id','customer','currency','amount_minor']
 if set(payload)!=set(required):raise ValueError('Unexpected or missing payload field')
 if any(not isinstance(payload[x],str) or not payload[x].strip() for x in required[:-1]):raise ValueError('Required identifier missing')
 if type(payload['amount_minor']) is not int or payload['amount_minor']<=0:raise ValueError('Positive integer minor amount required')
 fingerprint=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 try:
  c.execute('BEGIN')
  old=c.execute('SELECT fingerprint,result FROM ledger WHERE tenant=? AND intent=?',(payload['tenant'],payload['intent'])).fetchone()
  if old:
   if old[0]!=fingerprint:raise ValueError('Conflicting payload for retained intent')
   c.commit();return dict(state='repeat',result=old[1])
  c.execute('INSERT INTO effects VALUES(?,?,?,?,?,?)',tuple(payload[x] for x in required))
  if fail_after_effect:raise RuntimeError('Injected local failure')
  retained='SIMULATED-'+payload['intent']
  c.execute('INSERT INTO ledger VALUES(?,?,?,?)',(payload['tenant'],payload['intent'],fingerprint,retained));c.commit()
  return dict(state='completed',result=retained)
 except Exception:
  c.rollback();raise

def nearest_rank(values,p):
 if not values or not 0<p<=1:raise ValueError('Nonempty values and0<p<=1 required')
 return sorted(values)[math.ceil(p*len(values))-1]
def metric_fixture():
 return ([dict(id=i,correct=True,duration_ms=100,timeout=False) for i in range(1,99)]
 +[dict(id=99,correct=True,duration_ms=900,timeout=False),
   dict(id=100,correct=False,duration_ms=2000,timeout=True)])
def measure(records,limit_ms=500):
 if not records:raise ValueError('No attempts')
 ids=[r['id'] for r in records]
 if len(ids)!=len(set(ids)):raise ValueError('Duplicate attempt ID')
 if any(type(r['correct']) is not bool or type(r['timeout']) is not bool for r in records):raise ValueError('Boolean outcome flags required')
 if any(type(r['duration_ms']) not in [int,float] or not math.isfinite(r['duration_ms']) or r['duration_ms']<0 for r in records):raise ValueError('Invalid duration')
 if any(r['correct'] and r['timeout'] for r in records):raise ValueError('Timeout cannot be a correct completion')
 success=[r['duration_ms'] for r in records if r['correct'] and not r['timeout']]
 timely=sum(r['correct'] and not r['timeout'] and r['duration_ms']<=limit_ms for r in records)
 n=len(records)
 return dict(attempts=n,successes=len(success),timeouts=sum(r['timeout'] for r in records),
  timely_correct=timely,timely_correct_proportion=timely/n,
  success_proportion=len(success)/n,
  successful_mean_ms=sum(success)/len(success) if success else None,
  successful_p95_ms=nearest_rank(success,.95) if success else None,
  successful_p99_ms=nearest_rank(success,.99) if success else None,
  scope='Synthetic client attempts, successful-latency population separate')

def closure_gate(item):
 """Teaching decision gate, not an automated risk acceptance authority."""
 if not item.get('original_evidence'):return 'evidence incomplete'
 if item.get('accepted_exception'):
  required=['decision_owner','population','consequence','mitigation','operating_owner','review_condition','decision_reference']
  return 'accepted exception' if all(item.get(x) for x in required) else 'evidence incomplete'
 if not item.get('correction_reference'):return 'investigating'
 if item.get('retest_passed') is False:return 'retest failed'
 if item.get('retest_passed') is not True:return 'awaiting retest'
 if not all(item.get(x) for x in ['retest_reference','affected_population_reference','reviewer']):return 'evidence incomplete'
 return 'closed by verified correction'

def main():
 c=intent_database();first=handle_intent(c,deepcopy(INTENT));second=handle_intent(c,deepcopy(INTENT))
 result=dict(boundary=boundary_example(),snapshot=snapshot_example(),
  idempotency=dict(first=first,second=second,effects=c.execute('SELECT COUNT(*) FROM effects').fetchone()[0]),
  metrics=measure(metric_fixture()),recovery_minutes=sum([2,3,8,4,6]),
  sqlite_version=sqlite3.sqlite_version,scope='Synthetic local exercises only')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
