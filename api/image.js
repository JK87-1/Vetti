import { head, put } from '@vercel/blob';

const ALLOWED_ORIGINS = [
  'https://vetti.kr',
  'https://www.vetti.kr',
  'https://jk87-1.github.io',
];

export const config = {
  api: { bodyParser: false },
};

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

export default async function handler(req, res) {
  setCors(req, res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });
  if (!process.env.OPENAI_KEY) return res.status(500).json({ error: 'Server key not configured' });

  const url = new URL(req.url, 'http://localhost');
  const cacheKey = safeKey(url.searchParams.get('key'));
  const blobPath = cacheKey ? `renders/${cacheKey}.png` : null;

  // 1) Check Vercel Blob cache first
  if (blobPath) {
    try {
      const info = await head(blobPath);
      if (info && info.url) {
        return res.status(200).json({ url: info.url, cached: true });
      }
    } catch (e) {
      // miss → fall through to OpenAI
    }
  }

  // 2) Forward to OpenAI
  try {
    const chunks = [];
    for await (const c of req) chunks.push(c);
    const body = Buffer.concat(chunks);

    const r = await fetch('https://api.openai.com/v1/images/edits', {
      method: 'POST',
      headers: {
        'Authorization': 'Bearer ' + process.env.OPENAI_KEY,
        'Content-Type': req.headers['content-type'],
      },
      body,
    });

    if (!r.ok) {
      const text = await r.text();
      return res.status(r.status).setHeader('Content-Type', 'application/json').send(text);
    }

    const data = await r.json();
    const b64 = data?.data?.[0]?.b64_json;
    if (!b64) return res.status(500).json({ error: 'No image in response' });

    // 3) Save to Blob + return URL (if we have a key)
    if (blobPath) {
      try {
        const pngBuffer = Buffer.from(b64, 'base64');
        const blob = await put(blobPath, pngBuffer, {
          access: 'public',
          contentType: 'image/png',
          allowOverwrite: true,
          addRandomSuffix: false,
        });
        return res.status(200).json({ url: blob.url, cached: false });
      } catch (e) {
        // Blob failed → fall back to returning base64 so UX continues
        console.warn('Blob put failed:', e.message);
      }
    }

    // Fallback: return data URL
    res.status(200).json({ dataUrl: 'data:image/png;base64,' + b64 });
  } catch (e) {
    res.status(500).json({ error: String(e) });
  }
}
