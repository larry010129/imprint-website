<?php
/**
 * GET /api/bot-gold.php
 * Server-side fetch of BOT gold page (works on PHP hosting — no Vercel required).
 * Returns HTML for the browser parser in js/parse-bot-gold.js.
 */
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    http_response_code(405);
    echo json_encode(['error' => 'method not allowed']);
    exit;
}

$urls = [
    'https://rate.bot.com.tw/gold/quote/recent',
    'https://rate.bot.com.tw/gold?Lang=zh-TW',
];

$headers = [
    'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language: zh-TW,zh;q=0.9,en;q=0.8',
    'Accept: text/html,application/xhtml+xml',
];

function fetch_bot_html($url, $headers) {
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_TIMEOUT => 20,
            CURLOPT_HTTPHEADER => $headers,
        ]);
        $body = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($body === false || $code < 200 || $code >= 400) {
            return null;
        }
        return $body;
    }

    $ctx = stream_context_create([
        'http' => [
            'method' => 'GET',
            'header' => implode("\r\n", $headers) . "\r\n",
            'timeout' => 20,
            'ignore_errors' => true,
        ],
    ]);
    $body = @file_get_contents($url, false, $ctx);
    return ($body !== false && strlen($body) > 1000) ? $body : null;
}

$html = null;
$sourceUrl = null;
foreach ($urls as $url) {
    $html = fetch_bot_html($url, $headers);
    if ($html !== null) {
        $sourceUrl = $url;
        break;
    }
}

if ($html === null) {
    http_response_code(502);
    echo json_encode(['error' => 'BOT fetch failed']);
    exit;
}

echo json_encode([
    'html' => $html,
    'source_url' => $sourceUrl,
], JSON_UNESCAPED_UNICODE);
