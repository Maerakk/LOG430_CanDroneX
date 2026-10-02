# Scénario de démonstration CanDroneX — Phase 1
# Prérequis : docker compose up --build (dans un autre terminal)

$BASE = "http://127.0.0.1:5000/api/v1"
$AUTH = "Authorization: Bearer demo_key_1"

Write-Host "`n1. Enregistrer DRN-0231 (attendu : 201)" -ForegroundColor Cyan
curl.exe -s -i -X POST "$BASE/drones" -H $AUTH -H "Content-Type: application/json" `
  -d '{\"droneId\": \"DRN-0231\", \"imsi\": \"999700000010231\", \"iccid\": \"8999970000000010231\"}'

Write-Host "`n2. Commander C2 + Imagerie (attendu : 201)" -ForegroundColor Cyan
curl.exe -s -i -X POST "$BASE/service-orders" -H $AUTH -H "Idempotency-Key: demo-order-0231" `
  -H "Content-Type: application/json" `
  -d '{\"items\": [{\"droneId\": \"DRN-0231\", \"serviceType\": \"C2\"}, {\"droneId\": \"DRN-0231\", \"serviceType\": \"IMAGERY\"}]}'

Write-Host "`n3. Rejouer la même commande (attendu : la même commande)" -ForegroundColor Cyan
curl.exe -s -i -X POST "$BASE/service-orders" -H $AUTH -H "Idempotency-Key: demo-order-0231" `
  -H "Content-Type: application/json" `
  -d '{\"items\": [{\"droneId\": \"DRN-0231\", \"serviceType\": \"C2\"}, {\"droneId\": \"DRN-0231\", \"serviceType\": \"IMAGERY\"}]}'

Write-Host "`n4. Requête sans clé d'API (attendu : 401)" -ForegroundColor Cyan
curl.exe -s -i -X POST "$BASE/drones" -H "Content-Type: application/json" `
  -d '{\"droneId\": \"DRN-0999\", \"imsi\": \"999700000099999\", \"iccid\": \"8999970000000099999\"}'