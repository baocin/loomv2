#!/bin/bash
# Monitor and report Kafka consumer lag

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-loom-dev}"
KAFKA_POD=$(kubectl get pods -n $NAMESPACE -l app=kafka -o jsonpath='{.items[0].metadata.name}')
CONSUMER_GROUP="${CONSUMER_GROUP:-kafka-to-db-consumer}"

echo "=== Kafka Consumer Lag Monitor ==="
echo "Namespace: $NAMESPACE"
echo "Consumer Group: $CONSUMER_GROUP"
echo ""

# Check consumer lag
echo "Checking consumer lag..."
kubectl exec -n $NAMESPACE $KAFKA_POD -- \
    kafka-consumer-groups.sh \
    --bootstrap-server localhost:9092 \
    --group $CONSUMER_GROUP \
    --describe

echo ""
echo "=== Database Connection Pool Status ==="
kubectl exec -n $NAMESPACE deployment/timescaledb -- psql -U loom -d loom -c "
SELECT
    pid,
    usename,
    application_name,
    client_addr,
    state,
    state_change,
    query_start,
    now() - query_start as query_duration
FROM pg_stat_activity
WHERE datname = 'loom'
    AND pid != pg_backend_pid()
ORDER BY query_start DESC
LIMIT 20;
"

echo ""
echo "=== Consumer Performance Monitor ==="
kubectl exec -n $NAMESPACE deployment/timescaledb -- psql -U loom -d loom -c "
SELECT * FROM v_consumer_performance_monitor
WHERE service_name = 'kafka-to-db-consumer'
ORDER BY last_message_time DESC
LIMIT 10;
"

echo ""
echo "=== Consumer Alerts ==="
kubectl exec -n $NAMESPACE deployment/timescaledb -- psql -U loom -d loom -c "
SELECT * FROM v_consumer_alerts
WHERE service_name = 'kafka-to-db-consumer'
    OR consumer_group = 'kafka-to-db-consumer'
ORDER BY alert_timestamp DESC
LIMIT 10;
"

echo ""
echo "=== Pod Resources ==="
kubectl top pods -n $NAMESPACE | grep kafka-to-db-consumer || echo "No consumer pods found"

echo ""
echo "=== Recommendations ==="
echo "1. If lag is high, scale the consumer:"
echo "   kubectl scale deployment kafka-to-db-consumer -n $NAMESPACE --replicas=5"
echo ""
echo "2. Check consumer logs:"
echo "   kubectl logs -n $NAMESPACE deployment/kafka-to-db-consumer --tail=100"
echo ""
echo "3. Restart consumer if needed:"
echo "   kubectl rollout restart deployment/kafka-to-db-consumer -n $NAMESPACE"
echo ""
echo "4. Update Helm values and redeploy:"
echo "   helm upgrade kafka-to-db-consumer deploy/helm/kafka-to-db-consumer/ -n $NAMESPACE"
