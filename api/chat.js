const ALLOWED_ORIGINS = [
  'https://vetti.kr',
  'https://www.vetti.kr',
  'https://jk87-1.github.io',
];

// 서버 키로 부르는 모델·길이를 서버가 정한다 (2026-10-20 보안감시)
// 예전에는 요청 본문을 그대로 OpenAI 에 넘겨, 누구나 아무 모델·아무 길이로 서버 키를 쓸 수 있었다.
const MODEL = 'gpt-4o-mini';
const MAX_TOKENS = 1000;
const MAX_MESSAGES = 40;      // 시스템 1 + 최근 대화
const MAX_TEXT = 6000;        // 메시지 하나의 글자 수 상한 (시스템 프롬프트 약 2,000자)
const MAX_IMAGE_URL = 3_000_000; // 첨부 사진(data URL) 하나 상한
const ROLES = new Set(['system', 'user', 'assistant']);

function setCors(req, res) {
  const origin = req.headers.origin || '';
  const allow = ALLOWED_ORIGINS.includes(origin) ? origin : 'https://vetti.kr';
  res.setHeader('Access-Control-Allow-Origin', allow);
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Vary', 'Origin');
}

function cleanPart(p) {
  if (!p || typeof p !== 'object') return null;
  if (p.type === 'text' && typeof p.text === 'string') {
    return { type: 'text', text: p.text.slice(0, MAX_TEXT) };
  }
  if (p.type === 'image_url' && p.image_url && typeof p.image_url.url === 'string') {
    const url = p.image_url.url;
    if (!/^data:image\/(png|jpe?g|webp|gif);base64,/.test(url) || url.length > MAX_IMAGE_URL) return null;
    return { type: 'image_url', image_url: { url, detail: 'low' } };
  }
  return null;
}

function cleanMessages(raw) {
  if (!Array.isArray(raw)) return null;
  const out = [];
  for (const m of raw) {
    if (!m || !ROLES.has(m.role)) continue;
    if (typeof m.content === 'string') {
      out.push({ role: m.role, content: m.content.slice(0, MAX_TEXT) });
    } else if (Array.isArray(m.content) && m.role === 'user') {
      const parts = m.content.slice(0, 4).map(cleanPart).filter(Boolean);
      if (parts.length) out.push({ role: m.role, content: parts });
    }
  }
  if (!out.length) return null;
  // 시스템 메시지는 맨 앞 하나만 두고, 나머지는 최근 대화만 남긴다
  const system = out[0].role === 'system' ? [out[0]] : [];
  const rest = out.filter((m, i) => !(i === 0 && m.role === 'system') && m.role !== 'system');
  return [...system, ...rest.slice(-(MAX_MESSAGES - system.length))];
}

export default async function handler(req, res) {
  setCors(req, res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });
  if (!process.env.OPENAI_KEY) return res.status(500).json({ error: 'Server key not configured' });

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) { return res.status(400).json({ error: 'Invalid JSON' }); }
  }
  const messages = cleanMessages(body && body.messages);
  if (!messages) return res.status(400).json({ error: 'messages required' });
  const t = Number(body.temperature);
  const temperature = Number.isFinite(t) ? Math.min(Math.max(t, 0), 1) : 0.7;

  try {
    const r = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': 'Bearer ' + process.env.OPENAI_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ model: MODEL, messages, temperature, max_tokens: MAX_TOKENS }),
    });
    const text = await r.text();
    res.status(r.status).setHeader('Content-Type', 'application/json').send(text);
  } catch (e) {
    res.status(500).json({ error: 'Upstream error' });
  }
}
