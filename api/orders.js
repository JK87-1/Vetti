import { put } from '@vercel/blob';

const ALLOWED_ORIGINS = [
  'https://vetti.kr',
  'https://www.vetti.kr',
  'https://jk87-1.github.io',
];

function setCors(req, res) {
  const origin = req.headers.origin || '';
  const allow = ALLOWED_ORIGINS.includes(origin) ? origin : 'https://vetti.kr';
  res.setHeader('Access-Control-Allow-Origin', allow);
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Vary', 'Origin');
}

function safeKey(k) {
  return (k || '').replace(/[^a-zA-Z0-9_\-]/g, '_').slice(0, 80);
}

function pad2(n) { return String(n).padStart(2, '0'); }

function tsKey(d) {
  return d.getUTCFullYear() + pad2(d.getUTCMonth() + 1) + pad2(d.getUTCDate())
    + '-' + pad2(d.getUTCHours()) + pad2(d.getUTCMinutes()) + pad2(d.getUTCSeconds());
}

export default async function handler(req, res) {
  setCors(req, res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  let order;
  try {
    order = typeof req.body === 'string' ? JSON.parse(req.body) : req.body;
  } catch (e) {
    return res.status(400).json({ error: 'Invalid JSON' });
  }
  if (!order || typeof order !== 'object') {
    return res.status(400).json({ error: 'Invalid payload' });
  }

  const cust = order.customer || {};
  if (!order.woNum || !cust.name || !cust.email || !cust.phone) {
    return res.status(400).json({ error: 'Missing required fields' });
  }

  const now = new Date();
  const receivedAt = now.toISOString();
  const record = { ...order, receivedAt, userAgent: (req.headers['user-agent'] || '').slice(0, 200) };

  const path = `orders/${tsKey(now)}-${safeKey(order.woNum)}.json`;

  try {
    const blob = await put(path, JSON.stringify(record, null, 2), {
      access: 'public',
      contentType: 'application/json',
      allowOverwrite: false,
      addRandomSuffix: true,
    });
    return res.status(200).json({ ok: true, url: blob.url, path });
  } catch (e) {
    return res.status(500).json({ ok: false, error: String(e.message || e) });
  }
}
