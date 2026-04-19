import { put } from '@vercel/blob';

const ALLOWED_ORIGINS = [
  'https://vetti.kr',
  'https://www.vetti.kr',
  'https://jk87-1.github.io',
];

const VALID_STATUSES = ['pending_payment', 'received', 'crafting', 'qc', 'shipping', 'delivered', 'cancelled'];

function setCors(req, res) {
  const origin = req.headers.origin || '';
  const allow = ALLOWED_ORIGINS.includes(origin) ? origin : 'https://vetti.kr';
  res.setHeader('Access-Control-Allow-Origin', allow);
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-Admin-Token');
  res.setHeader('Vary', 'Origin');
}

export default async function handler(req, res) {
  setCors(req, res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const providedToken = req.headers['x-admin-token'] || '';
  const expected = process.env.ADMIN_TOKEN || '';
  if (!expected) return res.status(500).json({ error: 'ADMIN_TOKEN not configured' });
  if (providedToken !== expected) return res.status(401).json({ error: 'Unauthorized' });

  let body;
  try {
    body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body;
  } catch (e) { return res.status(400).json({ error: 'Invalid JSON' }); }

  const { blobUrl, status, internalNote } = body || {};
  if (!blobUrl) return res.status(400).json({ error: 'Missing blobUrl' });
  if (status && !VALID_STATUSES.includes(status)) {
    return res.status(400).json({ error: 'Invalid status. Allowed: ' + VALID_STATUSES.join(', ') });
  }

  // Only allow our own blob host
  let pathname;
  try {
    const u = new URL(blobUrl);
    if (!/\.public\.blob\.vercel-storage\.com$/.test(u.host)) {
      return res.status(400).json({ error: 'blobUrl not on Vercel Blob host' });
    }
    pathname = u.pathname.replace(/^\//, '');
    if (!pathname.startsWith('orders/')) {
      return res.status(400).json({ error: 'blobUrl not in orders/ prefix' });
    }
  } catch (e) { return res.status(400).json({ error: 'Invalid blobUrl' }); }

  try {
    const r = await fetch(blobUrl);
    if (!r.ok) return res.status(502).json({ error: 'Failed to fetch original blob' });
    const data = await r.json();

    const now = new Date().toISOString();
    if (status) {
      data.status = status;
      data.statusUpdatedAt = now;
      data.statusHistory = data.statusHistory || [];
      data.statusHistory.push({ status, at: now });
    }
    if (typeof internalNote === 'string') {
      data.internalNote = internalNote;
      data.internalNoteUpdatedAt = now;
    }

    const blob = await put(pathname, JSON.stringify(data, null, 2), {
      access: 'public',
      contentType: 'application/json',
      allowOverwrite: true,
      addRandomSuffix: false,
    });

    return res.status(200).json({
      ok: true, url: blob.url,
      status: data.status, statusUpdatedAt: data.statusUpdatedAt,
    });
  } catch (e) {
    return res.status(500).json({ error: String(e.message || e) });
  }
}
