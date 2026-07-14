/* Auth helpers — replaces Supabase Auth (signInWithPassword, signUp,
 * getSession, signOut, resetPasswordForEmail). Sessions are a signed JWT in
 * an httpOnly cookie; no server-side session table (stateless, matches how
 * serverless functions work best — no shared memory between invocations).
 */
const crypto = require('crypto');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

const COOKIE_NAME = 'imprint_session';
const SESSION_DAYS = 30;

function requireEnv(name) {
  const v = process.env[name];
  if (!v) throw new Error(`${name} is not set`);
  return v;
}

async function hashPassword(password) {
  return bcrypt.hash(password, 10);
}

async function verifyPassword(password, hash) {
  return bcrypt.compare(password, hash);
}

function signSession(userId) {
  return jwt.sign({ sub: userId }, requireEnv('JWT_SECRET'), { expiresIn: `${SESSION_DAYS}d` });
}

function verifySessionToken(token) {
  try {
    const payload = jwt.verify(token, requireEnv('JWT_SECRET'));
    return payload.sub;
  } catch (e) {
    return null;
  }
}

function parseCookies(req) {
  const header = req.headers.cookie;
  const out = {};
  if (!header) return out;
  header.split(';').forEach((pair) => {
    const idx = pair.indexOf('=');
    if (idx === -1) return;
    out[pair.slice(0, idx).trim()] = decodeURIComponent(pair.slice(idx + 1).trim());
  });
  return out;
}

/* SameSite=None + Secure is required for a cross-origin static site (V3) to
 * send this cookie to a different-origin API (this backend). */
function setSessionCookie(res, token) {
  const maxAge = SESSION_DAYS * 24 * 60 * 60;
  res.setHeader('Set-Cookie',
    `${COOKIE_NAME}=${token}; Max-Age=${maxAge}; Path=/; HttpOnly; Secure; SameSite=None`);
}

function clearSessionCookie(res) {
  res.setHeader('Set-Cookie', `${COOKIE_NAME}=; Max-Age=0; Path=/; HttpOnly; Secure; SameSite=None`);
}

/** Returns the authenticated user's id (uuid), or null if not logged in. */
function getUserId(req) {
  const cookies = parseCookies(req);
  const token = cookies[COOKIE_NAME];
  if (!token) return null;
  return verifySessionToken(token);
}

function generateResetToken() {
  return crypto.randomBytes(32).toString('hex');
}

/** Returns true if the given user id is in staff_admins. */
async function isAdmin(sql, userId) {
  if (!userId) return false;
  const [row] = await sql`select user_id from staff_admins where user_id = ${userId}`;
  return !!row;
}

/** Auth+admin gate for admin/*.js endpoints. On failure, writes the response
 * and returns null; caller should `return` immediately when this happens. */
async function requireAdmin(req, res, sql) {
  const userId = getUserId(req);
  if (!userId) {
    res.status(401).json({ error: 'not signed in' });
    return null;
  }
  if (!(await isAdmin(sql, userId))) {
    res.status(403).json({ error: 'admin access required' });
    return null;
  }
  return userId;
}

module.exports = {
  COOKIE_NAME,
  hashPassword,
  verifyPassword,
  signSession,
  getUserId,
  setSessionCookie,
  clearSessionCookie,
  generateResetToken,
  isAdmin,
  requireAdmin,
};
