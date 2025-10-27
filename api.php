<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

// Handle preflight requests
if ($_SERVER['REQUEST_METHOD'] == 'OPTIONS') {
    http_response_code(200);
    exit();
}

// Backend server configuration
$backend_host = '.........136';
$backend_port = '5000';
$backend_url = "http://{$backend_host}:{$backend_port}";

// Get the requested path
$path = $_GET['path'] ?? '';
if (empty($path)) {
    http_response_code(400);
    echo json_encode(['error' => 'No path specified']);
    exit();
}

// Build the backend URL
$full_url = $backend_url . '/' . ltrim($path, '/');

// Get request method and body
$method = $_SERVER['REQUEST_METHOD'];
$headers = [];

// Forward relevant headers
foreach (getallheaders() as $name => $value) {
    if (in_array(strtolower($name), ['content-type', 'authorization'])) {
        $headers[] = "$name: $value";
    }
}

// Setup cURL
$ch = curl_init();
curl_setopt_array($ch, [
    CURLOPT_URL => $full_url,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_FOLLOWLOCATION => true,
    CURLOPT_TIMEOUT => 30,
    CURLOPT_CUSTOMREQUEST => $method,
    CURLOPT_HTTPHEADER => $headers,
    CURLOPT_SSL_VERIFYPEER => false,
    CURLOPT_SSL_VERIFYHOST => false
]);

// Handle request body for POST/PUT requests
if (in_array($method, ['POST', 'PUT', 'PATCH'])) {
    $body = file_get_contents('php://input');
    curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
}

// Execute request
$response = curl_exec($ch);
$http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$error = curl_error($ch);
curl_close($ch);

// Handle cURL errors
if ($error) {
    http_response_code(502);
    echo json_encode(['error' => 'Backend connection failed: ' . $error]);
    exit();
}

// Forward the response
http_response_code($http_code);
echo $response;
?>