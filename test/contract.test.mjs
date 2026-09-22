import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {validateManifest,validateRequest,validateResponse} from '../lib/contract.mjs';
const json=p=>JSON.parse(readFileSync(new URL(p,import.meta.url)));
const manifest=json('../examples/full-service-provider/provider.json'),taxonomy=json('../taxonomy.json');
const schemas=Object.fromEntries(manifest.products.map(p=>[p.providerDataSchema,json('../examples/full-service-provider/'+p.providerDataSchema)]));
validateManifest(manifest,taxonomy,schemas);
const fixture=id=>json(`../examples/full-service-provider/fixtures/${id}.json`);
const options={now:Date.parse('2026-09-22T10:05:00Z'),mode:'sandbox'};
const validate=f=>validateResponse(f.response,f.request,manifest,options);
test('one fictional group has valid structured input/output for all 41 categories',()=>{assert.equal(manifest.products.length,41);for(const p of manifest.products)validate(fixture(p.id));});
test('every required provider field, including nested fields, is enforced',()=>{
 let checked=0;
 function requiredPaths(s,path=[]){const result=[];for(const key of s.required||[]){result.push([...path,key]);const sub=s.properties[key];if(sub?.type==='object')result.push(...requiredPaths(sub,[...path,key]));}return result;}
 for(const p of manifest.products)for(const path of requiredPaths(schemas[p.providerDataSchema])){const f=fixture(p.id);let parent=f.request.input.providerData;for(const key of path.slice(0,-1))parent=parent[key];delete parent[path.at(-1)];assert.throws(()=>validate(f),`${p.id}: ${path.join('.')}`);checked++;}
 assert.ok(checked>800);
});
test('claims, business vehicle use, joint borrowers and refinancing activate follow-up requirements',()=>{
 const cases=[['car',d=>d.common.history.hasClaims=true],['car',d=>d.vehicle.use='business'],['mortgages',d=>d.application.joint=true],['mortgages',d=>d.mortgage.purpose='refinance'],['health-supplementary',d=>d.medical.hasConditions=true]];
 for(const [id,mutate]of cases){const f=fixture(id);mutate(f.request.input.providerData);assert.throws(()=>validate(f));}
 const f=fixture('car');f.request.input.providerData.common.history.hasClaims=true;f.request.input.providerData.common.history.claims=[{date:'2025-01-01',type:'SYNTHETIC',paidAmount:'1000.00',open:false}];validate(f);
});
test('no untyped bag of extra fields can bypass provider requirements',()=>{const f=fixture('car');f.request.input.providerData.unknownField=true;assert.throws(()=>validate(f));const m=structuredClone(manifest);assert.throws(()=>validateManifest(m,taxonomy,{}));});
test('sandbox results cannot become consumer prices',()=>{const f=fixture('car');assert.throws(()=>validateResponse(f.response,f.request,manifest,{now:options.now}));});
test('reject expired, future and malformed timestamps',()=>{for(const [key,value]of [['expiresAt','2026-09-22T10:04:00Z'],['issuedAt','2026-09-22T11:00:00Z'],['issuedAt','2026-02-30T10:00:00Z']]){const f=fixture('car');f.response.quotes[0][key]=value;assert.throws(()=>validate(f));}});
test('reject wrong product, request, currency, risk and redirect host',()=>{
 for(const mutate of [f=>f.response.requestId='other',f=>f.response.quotes[0].productId='life',f=>f.response.quotes[0].currency='USD',f=>f.response.quotes[0].quoteUrl='https://attacker.example/quote',f=>f.request.input.risk=fixture('home').request.input.risk]){const f=fixture('car');mutate(f);assert.throws(()=>validate(f));}
});
test('premiums must total and errors never carry quotes',()=>{validate(fixture('no_quote'));validate(fixture('unavailable'));for(const amount of ['0.00','-1.00','NaN','120,00',120,'121.00']){const f=fixture('car');f.response.quotes[0].insurance.premium.total=amount;assert.throws(()=>validate(f));}const f=fixture('car');f.response.status='unavailable';assert.throws(()=>validate(f));});
test('credit schedules reconcile principal, interest, payments and balances',()=>{for(const mutate of [v=>v.totalPayable='1.00',v=>v.repaymentSchedule[0].principal='0.00',v=>v.finalBalance='10.00',v=>v.repaymentSchedule.pop()]){const f=fixture('personal-loan');mutate(f.response.quotes[0].credit);assert.throws(()=>validate(f));}});
test('revolving credit needs minimum rules; pension projections must be illustrative',()=>{let f=fixture('credit-card');delete f.response.quotes[0].credit.minimumPayment;assert.throws(()=>validate(f));f=fixture('pillar-3a');f.response.quotes[0].retirement.projections[0].illustrative=false;assert.throws(()=>validate(f));});
test('real clock rejects the historic test fixture and PR cannot switch itself live',()=>{const m=structuredClone(manifest);m.status='active';assert.throws(()=>validateManifest(m,taxonomy,schemas));const f=fixture('car');assert.throws(()=>validateResponse(f.response,f.request,manifest,{now:Date.parse('2027-01-01T00:00:00Z'),mode:'sandbox'}));});
