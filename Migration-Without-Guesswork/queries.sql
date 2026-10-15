-- Run after fixture.sql, in a new disposable database. One SELECT per named query.
-- Q01 invalid_source_keys
SELECT row_id,tenant_id,order_id FROM source_orders
WHERE typeof(tenant_id)<>'text'
 OR trim(tenant_id,char(9,10,11,12,13,32))=''
 OR typeof(order_id)<>'text'
 OR trim(order_id,char(9,10,11,12,13,32))='';
-- Q02 invalid_target_keys
SELECT row_id,tenant_id,order_id FROM target_orders
WHERE typeof(tenant_id)<>'text'
 OR trim(tenant_id,char(9,10,11,12,13,32))=''
 OR typeof(order_id)<>'text'
 OR trim(order_id,char(9,10,11,12,13,32))='';
-- Q03 duplicate_source
SELECT tenant_id,order_id,COUNT(*) FROM source_orders
WHERE typeof(tenant_id)='text'
 AND trim(tenant_id,char(9,10,11,12,13,32))<>''
 AND typeof(order_id)='text'
 AND trim(order_id,char(9,10,11,12,13,32))<>''
GROUP BY tenant_id,order_id HAVING COUNT(*)>1;
-- Q04 duplicate_target
SELECT tenant_id,order_id,COUNT(*) FROM target_orders
WHERE typeof(tenant_id)='text'
 AND trim(tenant_id,char(9,10,11,12,13,32))<>''
 AND typeof(order_id)='text'
 AND trim(order_id,char(9,10,11,12,13,32))<>''
GROUP BY tenant_id,order_id HAVING COUNT(*)>1;
-- Q05 missing_required_source
SELECT row_id FROM source_orders WHERE customer_id IS NULL
 OR trim(customer_id,char(9,10,11,12,13,32))=''
 OR currency IS NULL
 OR trim(currency,char(9,10,11,12,13,32))=''
 OR amount_minor IS NULL;
-- Q06 missing_required_target
SELECT row_id FROM target_orders WHERE customer_id IS NULL
 OR trim(customer_id,char(9,10,11,12,13,32))=''
 OR currency IS NULL
 OR trim(currency,char(9,10,11,12,13,32))=''
 OR amount_minor IS NULL;
-- Q07 invalid_amount_source
SELECT row_id,amount_minor,typeof(amount_minor) FROM source_orders
WHERE amount_minor IS NOT NULL AND typeof(amount_minor)<>'integer';
-- Q08 invalid_amount_target
SELECT row_id,amount_minor,typeof(amount_minor) FROM target_orders
WHERE amount_minor IS NOT NULL AND typeof(amount_minor)<>'integer';
-- Q09 unmapped_source_status
SELECT s.row_id,s.status FROM source_orders s WHERE NOT EXISTS
(SELECT 1 FROM status_map m WHERE m.source_status=s.status);
-- Q10 unmapped_target_status
SELECT t.row_id,t.status FROM target_orders t WHERE NOT EXISTS
(SELECT 1 FROM status_map m WHERE m.target_status=t.status);
-- Q11 source_only
SELECT DISTINCT s.tenant_id,s.order_id FROM source_orders s
WHERE typeof(s.tenant_id)='text'
 AND trim(s.tenant_id,char(9,10,11,12,13,32))<>''
 AND typeof(s.order_id)='text'
 AND trim(s.order_id,char(9,10,11,12,13,32))<>''
 AND NOT EXISTS (SELECT 1 FROM target_orders t
 WHERE t.tenant_id=s.tenant_id AND t.order_id=s.order_id);
-- Q12 target_only
SELECT DISTINCT t.tenant_id,t.order_id FROM target_orders t
WHERE typeof(t.tenant_id)='text'
 AND trim(t.tenant_id,char(9,10,11,12,13,32))<>''
 AND typeof(t.order_id)='text'
 AND trim(t.order_id,char(9,10,11,12,13,32))<>''
 AND NOT EXISTS (SELECT 1 FROM source_orders s
 WHERE s.tenant_id=t.tenant_id AND s.order_id=t.order_id);
-- Q13 customer_difference
SELECT s.tenant_id,s.order_id,s.customer_id,t.customer_id
FROM source_unique s JOIN target_unique t
 ON t.tenant_id=s.tenant_id AND t.order_id=s.order_id
WHERE s.customer_id IS NOT t.customer_id;
-- Q14 currency_difference
SELECT s.tenant_id,s.order_id,s.currency,t.currency
FROM source_unique s JOIN target_unique t
 ON t.tenant_id=s.tenant_id AND t.order_id=s.order_id
WHERE s.currency IS NOT t.currency;
-- Q15 amount_difference
SELECT s.tenant_id,s.order_id,s.amount_minor,t.amount_minor
FROM source_unique s JOIN target_unique t
 ON t.tenant_id=s.tenant_id AND t.order_id=s.order_id
WHERE typeof(s.amount_minor)='integer'
 AND typeof(t.amount_minor)='integer'
 AND s.currency=t.currency AND s.currency IS NOT NULL
 AND trim(s.currency,char(9,10,11,12,13,32))<>''
 AND s.amount_minor IS NOT t.amount_minor;
-- Q16 status_difference
SELECT s.tenant_id,s.order_id,m.target_status,t.status
FROM source_unique s JOIN target_unique t
 ON t.tenant_id=s.tenant_id AND t.order_id=s.order_id
JOIN status_map m ON m.source_status=s.status
WHERE m.target_status IS NOT t.status;
-- Q17 source_counts
SELECT (SELECT COUNT(*) FROM source_orders),COUNT(*) FROM
(SELECT tenant_id,order_id FROM source_orders
 WHERE typeof(tenant_id)='text'
 AND trim(tenant_id,char(9,10,11,12,13,32))<>''
 AND typeof(order_id)='text'
 AND trim(order_id,char(9,10,11,12,13,32))<>''
 GROUP BY tenant_id,order_id);
-- Q18 target_counts
SELECT (SELECT COUNT(*) FROM target_orders),COUNT(*) FROM
(SELECT tenant_id,order_id FROM target_orders
 WHERE typeof(tenant_id)='text'
 AND trim(tenant_id,char(9,10,11,12,13,32))<>''
 AND typeof(order_id)='text'
 AND trim(order_id,char(9,10,11,12,13,32))<>''
 GROUP BY tenant_id,order_id);
-- Q19 source_controls
SELECT tenant_id,currency,COUNT(*),SUM(amount_minor)
FROM source_orders WHERE typeof(amount_minor)='integer'
GROUP BY tenant_id,currency ORDER BY tenant_id,currency;
-- Q20 target_controls
SELECT tenant_id,currency,COUNT(*),SUM(amount_minor)
FROM target_orders WHERE typeof(amount_minor)='integer'
GROUP BY tenant_id,currency ORDER BY tenant_id,currency;
-- Q21 unique_matched_count
SELECT COUNT(*) FROM source_unique s JOIN target_unique t
ON t.tenant_id=s.tenant_id AND t.order_id=s.order_id;
