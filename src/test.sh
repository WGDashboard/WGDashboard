BASE_URL=http://wg.local:10086/
API_KEY=twkl03ZfNz3WMMjsxs1xGXDZ1ruMaN8_0YKmGcDXvFI

response=$(curl -s -X POST "${BASE_URL}api/addPeers/demo3" \
  -H "Content-Type: application/json" \
  -H "wg-dashboard-apikey: ${API_KEY}" \
  -d "$REQUEST_BODY")

echo "Response from POST:"
echo "$response"

id=$(echo "$response" | jq -r '.data.[0].id')
echo "Extracted ID: $id"

# GET request to download the peer using the extracted id
response=$(curl -s -X GET "${BASE_URL}api/downloadPeer/wt-ipv6?id=${id}" \
  -H "wg-dashboard-apikey: ${API_KEY}")

echo $response
config_file=$(echo "$response" | jq -r '.data.file')

echo $config_file