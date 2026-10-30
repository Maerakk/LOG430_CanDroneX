// 1 min de montée puis 5 min à RATE ops/s, par la passerelle. Mélange 60 % lectures, 30 % commandes, 10 % drones.
import http from 'k6/http';
import exec from 'k6/execution';
import { check } from 'k6';

const GW = __ENV.GW || 'http://api-gateway:8080';
const KC = __ENV.KC || 'http://keycloak:8080';
const RATE = Number(__ENV.RATE || 600);
const RAMP = __ENV.RAMP || '1m';
const STEADY = __ENV.STEADY || '5m';
const CLIENT_ID = 'inspectra-demo';
// chaque commande prend un drone LOAD-n neuf (seed_load_drones.sql)
const STEADY_OFFSET = 100000;

export const options = {
  discardResponseBodies: false,
  scenarios: {
    ramp: { executor: 'ramping-arrival-rate', startRate: 0, timeUnit: '1s', stages: [{ target: RATE, duration: RAMP }],
            preAllocatedVUs: 200, maxVUs: Number(__ENV.MAX_VUS || 1500) },
    steady: { executor: 'constant-arrival-rate', rate: RATE, timeUnit: '1s', duration: STEADY, startTime: RAMP,
              preAllocatedVUs: 400, maxVUs: Number(__ENV.MAX_VUS || 1500) },
  },
  thresholds: {
    dropped_iterations: ['count==0'],
    http_req_failed: ['rate<0.01'],
  },
  summaryTrendStats: ['avg', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

// un jeton par VU, renouvelé avant son expiration (5 min)
let token = null;
let tokenExpiresAt = 0;
function auth() {
  if (!token || Date.now() > tokenExpiresAt) {
    const r = http.post(`${KC}/realms/candronex/protocol/openid-connect/token`,
      { grant_type: 'client_credentials', client_id: CLIENT_ID, client_secret: __ENV.CLIENT_SECRET },
      { tags: { op: 'token' } });
    if (r.status !== 200) throw new Error(`jeton refuse : ${r.status}`);
    token = r.json('access_token');
    tokenExpiresAt = Date.now() + (r.json('expires_in') - 60) * 1000;
  }
  return token;
}

const lastOrders = [];

function headers(extra = {}) {
  return { headers: { Authorization: `Bearer ${auth()}`, 'Content-Type': 'application/json', ...extra } };
}

function uniqueIndex() {
  const s = exec.scenario;
  return (s.name === 'steady' ? STEADY_OFFSET : 0) + s.iterationInTest + 1;
}

function placeOrder() {
  const n = uniqueIndex();
  const drone = `LOAD-${n}`;
  const body = JSON.stringify({ orderItem: [
    { action: 'add', droneId: drone, service: { serviceSpecification: { id: 'SPEC-C2-URLLC' } } },
    { action: 'add', droneId: drone, service: { serviceSpecification: { id: 'SPEC-IMAGERY-EMBB' } } }] });
  const r = http.post(`${GW}/api/service-ordering/v1/serviceOrder`, body,
    { ...headers({ 'Idempotency-Key': `load-${n}` }), tags: { op: 'order' } });
  const ok = check(r, { 'commande 201': (x) => x.status === 201 });
  if (ok) {
    const o = r.json();
    lastOrders.push({ id: o.id, services: o.orderItem.map((i) => i.service.id).filter((s) => s) });
    if (lastOrders.length > 20) lastOrders.shift();
  }
}

function registerDrone() {
  const n = uniqueIndex();
  const digits = String(n).padStart(10, '0');
  const r = http.post(`${GW}/api/drone-management/v1/drone`,
    JSON.stringify({ droneId: `REG-${n}`, imsi: `30298${digits}`, iccid: `893029800${digits}` }),
    { ...headers(), tags: { op: 'register' } });
  check(r, { 'drone 201': (x) => x.status === 201 });
}

function read(i) {
  const o = lastOrders.length ? lastOrders[i % lastOrders.length] : null;
  let r;
  if (o && i % 3 === 1) {
    r = http.get(`${GW}/api/service-ordering/v1/serviceOrder/${o.id}`, { ...headers(), tags: { op: 'read-order' } });
  } else if (o && o.services.length && i % 3 === 2) {
    r = http.get(`${GW}/api/slice-activation/v1/service/${o.services[i % o.services.length]}`,
      { ...headers(), tags: { op: 'read-service' } });
  } else {
    r = http.get(`${GW}/api/drone-management/v1/drone/LOAD-${1 + (i % 1000)}`, { ...headers(), tags: { op: 'read-drone' } });
  }
  check(r, { 'consultation 200': (x) => x.status === 200 });
}

export default function () {
  const i = exec.scenario.iterationInTest;
  const slot = i % 10;
  if (slot < 6) read(i);
  else if (slot < 9) placeOrder();
  else registerDrone();
}

export function handleSummary(data) {
  return {
    '/results/k6-summary.json': JSON.stringify(data, null, 2),
    stdout: `\nk6 termine : ${data.metrics.iterations.values.count} iterations, ` +
            `${(data.metrics.iterations.values.rate).toFixed(1)} it/s, ` +
            `abandonnees ${data.metrics.dropped_iterations ? data.metrics.dropped_iterations.values.count : 0}, ` +
            `erreurs ${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)} %, ` +
            `p95 HTTP ${data.metrics.http_req_duration.values['p(95)'].toFixed(0)} ms\n`,
  };
}
