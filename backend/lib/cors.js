/* CORS: the static site and this API are on different origins, and requests
 * carry a session cookie (`credentials: 'include'`), so the origin must be
 * echoed explicitly — `Access-Control-Allow-Origin: *` is not allowed
 * together with credentials by the CORS spec. Set ALLOWED_ORIGIN to the
 * site's real deployed origin (e.g. https://www.imprint-diamond.com).
 */
function applyCors(req, res) {
  const allowedOrigin = process.env.ALLOWED_ORIGIN || '';
  const origin = req.headers.origin;
  if (origin && (origin === allowedOrigin || allowedOrigin === '*')) {
    res.setHeader('Access-Control-Allow-Origin', origin);
  }
  res.setHeader('Access-Control-Allow-Credentials', 'true');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PATCH, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.status(204).end();
    return true; // caller should stop handling this request
  }
  return false;
}

module.exports = { applyCors };
