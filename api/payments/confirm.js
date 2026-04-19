import { put } from '@vercel/blob';

const ALLOWED_ORIGINS = [
  'https://vetti.kr',
  'https://www.vetti.kr',
  'https://jk87-1.github.io',
];

// Toss 공식 문서 테스트 시크릿 키 (실계좌 결제되지 않음)
const DEFAULT_TEST_SECRET = 'test_sk_docs_OEP59LybZ8B0zvwXkLWPZlbR';

function setCors(req, res) {
  const origin = req.headers.origin || '';
  const allow = ALLOWED_ORIGINS.includes(origin) ? origin : 'https://vetti.kr';
  res.setHeader('Access-Control-Allow-Origin', allow);
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Vary', 'Origin');
}

export default async function handler(req, res) {
  setCors(req, res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  let body;
  try {
    body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body;
  } catch (e) { return res.status(400).json({ error: 'Invalid JSON' }); }

  const { paymentKey, orderId, amount, blobUrl } = body || {};
  if (!paymentKey || !orderId || typeof amount !== 'number') {
    return res.status(400).json({ error: 'Missing paymentKey, orderId, or amount' });
  }

  const secret = process.env.TOSS_SECRET_KEY || DEFAULT_TEST_SECRET;
  const auth = 'Basic ' + Buffer.from(secret + ':').toString('base64');

  // 1) Toss에 결제 승인 요청 (여기서 실제 charge가 발생)
  let payment;
  try {
    const r = await fetch('https://api.tosspayments.com/v1/payments/confirm', {
      method: 'POST',
      headers: { 'Authorization': auth, 'Content-Type': 'application/json' },
      body: JSON.stringify({ paymentKey, orderId, amount }),
    });
    const text = await r.text();
    let data;
    try { data = JSON.parse(text); } catch(e) { data = { raw: text }; }
    if (!r.ok) {
      return res.status(r.status).json({ error: 'Toss confirm failed', toss: data });
    }
    payment = data;
  } catch (e) {
    return res.status(502).json({ error: 'Toss network error: ' + String(e.message || e) });
  }

  // 2) 주문 blob 패치 — status=received + payment 기록
  let patchResult = null;
  if (blobUrl) {
    try {
      const u = new URL(blobUrl);
      if (!/\.public\.blob\.vercel-storage\.com$/.test(u.host) ||
          !u.pathname.replace(/^\//, '').startsWith('orders/')) {
        patchResult = { patched: false, reason: 'blobUrl not in orders/ on Vercel Blob' };
      } else {
        const pathname = u.pathname.replace(/^\//, '');
        const r = await fetch(blobUrl);
        if (!r.ok) {
          patchResult = { patched: false, reason: 'fetch original blob failed: ' + r.status };
        } else {
          const data = await r.json();
          const now = new Date().toISOString();
          data.status = 'received';
          data.statusUpdatedAt = now;
          data.statusHistory = data.statusHistory || [];
          data.statusHistory.push({ status: 'received', at: now, trigger: 'payment_confirmed' });
          data.payment = {
            provider: 'toss',
            paymentKey: payment.paymentKey,
            orderId: payment.orderId,
            approvedAt: payment.approvedAt,
            totalAmount: payment.totalAmount,
            method: payment.method,
            status: payment.status,
            receiptUrl: payment.receipt && payment.receipt.url,
            cardCompany: payment.card && payment.card.company,
            cardNumberMasked: payment.card && payment.card.number,
            isTestMode: !process.env.TOSS_SECRET_KEY,
            confirmedAt: now,
          };
          await put(pathname, JSON.stringify(data, null, 2), {
            access: 'public',
            contentType: 'application/json',
            allowOverwrite: true,
            addRandomSuffix: false,
          });
          patchResult = { patched: true };
        }
      }
    } catch (e) {
      patchResult = { patched: false, reason: String(e.message || e) };
    }
  } else {
    patchResult = { patched: false, reason: 'no blobUrl provided' };
  }

  return res.status(200).json({
    ok: true,
    payment: {
      paymentKey: payment.paymentKey,
      orderId: payment.orderId,
      approvedAt: payment.approvedAt,
      totalAmount: payment.totalAmount,
      method: payment.method,
      status: payment.status,
      receiptUrl: payment.receipt && payment.receipt.url,
    },
    order: patchResult,
  });
}
