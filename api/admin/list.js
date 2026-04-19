import { list } from '@vercel/blob';

const ALLOWED_ORIGINS = [
  'https://vetti.kr',
  'https://www.vetti.kr',
  'https://jk87-1.github.io',
];

function setCors(req, res) {
  const origin = req.headers.origin || '';
  const allow = ALLOWED_ORIGINS.includes(origin) ? origin : 'https://vetti.kr';
  res.setHeader('Access-Control-Allow-Origin', allow);
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-Admin-Token');
  res.setHeader('Vary', 'Origin');
}

export default async function handler(req, res) {
  setCors(req, res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'GET') return res.status(405).json({ error: 'Method not allowed' });

  // Auth: X-Admin-Token header or ?token= query param
  const url = new URL(req.url, 'http://localhost');
  const providedToken = req.headers['x-admin-token'] || url.searchParams.get('token') || '';
  const expected = process.env.ADMIN_TOKEN || '';
  if (!expected) return res.status(500).json({ error: 'ADMIN_TOKEN not configured on server' });
  if (providedToken !== expected) return res.status(401).json({ error: 'Unauthorized' });

  const limit = Math.min(parseInt(url.searchParams.get('limit') || '50', 10), 200);

  try {
    const { blobs } = await list({ prefix: 'orders/', limit });
    blobs.sort((a, b) => new Date(b.uploadedAt || 0) - new Date(a.uploadedAt || 0));

    const orders = await Promise.all(blobs.map(async (b) => {
      try {
        const r = await fetch(b.url);
        if (!r.ok) return null;
        const data = await r.json();
        return {
          woNum: data.woNum,
          createdAt: data.createdAt,
          customer: {
            name: data.customer?.name,
            phone: data.customer?.phone,
            email: data.customer?.email,
            addr: data.customer?.addr,
            note: data.customer?.note,
          },
          spec: data.spec,
          total: data.total,
          leadTime: data.leadTime,
          consent: data.consent,
          craft: data.craft,
          blobUrl: b.url,
          uploadedAt: b.uploadedAt,
        };
      } catch (e) {
        return { _error: String(e.message || e), blobUrl: b.url };
      }
    }));

    return res.status(200).json({
      count: orders.length,
      orders: orders.filter(Boolean),
    });
  } catch (e) {
    return res.status(500).json({ error: String(e.message || e) });
  }
}
