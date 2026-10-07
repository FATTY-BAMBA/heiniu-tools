import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {tripSchema,budgetSummary,planSchema,validatePlan,collectSearchUrls,makePrompt} from '../lib/planner.js';
import handler from '../api/travel.js';
import {example} from '../travel/example.js';

test('sample obeys four friends, two dates, late starts, complete costs',()=>{assert.ok(tripSchema.safeParse(example.trip).success);assert.ok(planSchema.safeParse(example.plan).success);validatePlan(example.plan,example.trip);});
test('missing hotel quote never becomes an in-budget total',()=>{assert.deepEqual(budgetSummary(example.plan.costs,6500),{knownTotal:4730,hasUnknown:true,overBy:0,remaining:1770});});
test('actual higher hotel price is reported over budget',()=>{const costs=example.plan.costs.map(c=>c.category==='accommodation'?{...c,amount:2235}:c);assert.equal(budgetSummary(costs,6500).overBy,465);});
test('reject invalid dates, excessive duration, mismatched adults',()=>{for(const patch of [{startDate:'2026-02-30'},{endDate:'2026-10-09'},{endDate:'2026-10-20'},{people:3},{budget:-1}])assert.equal(tripSchema.safeParse({...example.trip,...patch}).success,false);});
test('reject model changing dates or scheduling before earliest time',()=>{let p=structuredClone(example.plan);p.days[0].date='2026-10-24';assert.throws(()=>validatePlan(p,example.trip));p=structuredClone(example.plan);p.days[1].stops[0].time='08:00';assert.throws(()=>validatePlan(p,example.trip));});
test('reject duplicate budget categories and omitted friend',()=>{let p=structuredClone(example.plan);p.costs[0].category='food';assert.throws(()=>validatePlan(p,example.trip));p=structuredClone(example.plan);p.matches.pop();assert.throws(()=>validatePlan(p,example.trip));});
test('sources can only be HTTPS URLs collected from actual search results',()=>{assert.deepEqual([...collectSearchUrls([{results:[{url:'https://example.com/travel'},{url:'javascript:alert(1)'}]}])],['https://example.com/travel']);});
test('prompt preserves full conditions and requires uncertain accommodation to remain null',()=>{const p=makePrompt(example.trip);for(const bit of ['2026-10-10','6500','11:00','住宿 amount 必須為 null','只輸出']){if(bit!=='只輸出')assert.ok(p.includes(bit));}});
test('API disabled mode and malformed inputs never call a model',async t=>{
 const old=process.env.TRAVEL_AI_ENABLED;delete process.env.TRAVEL_AI_ENABLED;
 const server=createServer(handler);await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));t.after(()=>{server.close();if(old===undefined)delete process.env.TRAVEL_AI_ENABLED;else process.env.TRAVEL_AI_ENABLED=old;});
 const address=server.address();const base=`http://127.0.0.1:${address.port}`;
 assert.equal((await(await fetch(base)).json()).enabled,false);
 const request=body=>fetch(base,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 assert.equal((await request(example.trip)).status,503);
 assert.equal((await request({...example.trip,people:7})).status,400);
 assert.equal((await fetch(base,{method:'POST',headers:{'Content-Type':'application/json','Origin':'https://evil.example'},body:JSON.stringify(example.trip)})).status,403);
 assert.equal((await fetch(base,{method:'PUT'})).status,405);
});
