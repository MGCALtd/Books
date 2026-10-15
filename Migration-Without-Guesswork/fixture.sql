-- Disposable SQLite teaching fixture: never run against an existing business schema.
-- Amounts are GBP minor units (pence), not floating-point pounds.
-- row_id is staging identity; tenant_id + order_id is business identity.

CREATE TABLE source_orders (
  row_id INTEGER PRIMARY KEY,
  tenant_id TEXT,
  order_id TEXT,
  customer_id TEXT,
  status TEXT,
  currency TEXT,
  amount_minor INTEGER
);

CREATE TABLE target_orders (
  row_id INTEGER PRIMARY KEY,
  tenant_id TEXT,
  order_id TEXT,
  customer_id TEXT,
  status TEXT,
  currency TEXT,
  amount_minor INTEGER
);
INSERT INTO source_orders
(tenant_id,order_id,customer_id,status,currency,amount_minor)
VALUES
('T1','O-101','C1','Pending','GBP',4000),
('T1','O-102','C2','Paid','GBP',6000),
('T1','O-104','C4','Paid','GBP',5000),
('T1','O-105','C5','Paid','GBP',5000);

-- Intentional defects: wrong customer O-102, missing O-104, duplicate O-105.
-- Both sides still total 20000: matching totals do not establish correctness.
INSERT INTO target_orders
(tenant_id,order_id,customer_id,status,currency,amount_minor)
VALUES
('T1','O-101','C1','OPEN','GBP',4000),
('T1','O-102','C9','SETTLED','GBP',6000),
('T1','O-105','C5','SETTLED','GBP',5000),
('T1','O-105','C5','SETTLED','GBP',5000);
-- Exclude invalid or repeated keys before field joins to avoid ambiguous matches.
-- trim uses this contract ASCII whitespace set, not all Unicode whitespace.
CREATE VIEW source_unique AS
SELECT s.*
FROM source_orders AS s
WHERE typeof(s.tenant_id)='text'
  AND trim(s.tenant_id,char(9,10,11,12,13,32)) <> ''
  AND typeof(s.order_id)='text'
  AND trim(s.order_id,char(9,10,11,12,13,32)) <> ''
  AND 1 = (
    SELECT COUNT(*) FROM source_orders AS x
    WHERE x.tenant_id=s.tenant_id
      AND x.order_id=s.order_id
  );
CREATE VIEW target_unique AS
SELECT s.*
FROM target_orders AS s
WHERE typeof(s.tenant_id)='text'
  AND trim(s.tenant_id,char(9,10,11,12,13,32)) <> ''
  AND typeof(s.order_id)='text'
  AND trim(s.order_id,char(9,10,11,12,13,32)) <> ''
  AND 1 = (
    SELECT COUNT(*) FROM target_orders AS x
    WHERE x.tenant_id=s.tenant_id
      AND x.order_id=s.order_id
  );
-- Status equivalence is a declared contract, not a case-conversion rule.
CREATE TABLE status_map(source_status TEXT PRIMARY KEY,target_status TEXT);
INSERT INTO status_map VALUES('Pending','OPEN'),('Paid','SETTLED');
