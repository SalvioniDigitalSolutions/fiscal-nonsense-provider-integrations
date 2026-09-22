import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import { readFileSync } from 'node:fs';
const ajv=new Ajv2020({strict:true,allErrors:true});addFormats(ajv);
const schema=JSON.parse(readFileSync(new URL('../schemas/contract.schema.json',import.meta.url)));
ajv.addSchema(schema);
const requestSchema=ajv.getSchema(schema.$id+'#/$defs/request'),responseSchema=ajv.getSchema(schema.$id+'#/$defs/response');
const compiled=new WeakMap();
const need=(ok,message)=>{if(!ok)throw new Error(message);};
const text=(v,k)=>need(typeof v==='string'&&v.trim().length>0,`${k} required`);
const currencies={CH:'CHF',US:'USD',GB:'GBP',DE:'EUR',IT:'EUR'};
const cents=v=>Math.round(Number(v)*100);
const valid=(fn,v)=>{need(fn(v),ajv.errorsText(fn.errors,{separator:'; '}));};
export function httpsURL(value,hosts){const u=new URL(value);need(u.protocol==='https:'&&!u.username&&!u.password&&!u.port&&!u.search&&!u.hash,'Expected HTTPS URL without credentials, query or fragment');if(hosts)need(hosts.includes(u.hostname),'Host not allowlisted');return u;}
export function validateManifest(m,taxonomy,providerSchemas){
 need(m.schemaVersion==='0.1'&&m.status==='proposed','Only proposed v0.1 manifests accepted');need(/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(m.id),'Invalid provider ID');
 for(const k of ['displayName','legalName','contactEmail'])text(m[k],k);
 need(/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(m.contactEmail),'Invalid public email');
 for(const k of ['website','documentationUrl','sandboxUrl'])httpsURL(m[k]);
 need(Array.isArray(m.quoteHosts)&&m.quoteHosts.length>0,'Quote hosts required');
 m.quoteHosts.forEach(h=>need(typeof h==='string'&&/^[a-z0-9.-]+\.[a-z]{2,}$/.test(h),'Invalid hostname'));
 need(Array.isArray(m.products)&&m.products.length>0,'Products required');const ids=new Set(),validators=new Map();
 for(const p of m.products){
  need(/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(p.id)&&!ids.has(p.id),'Invalid/duplicate product ID');ids.add(p.id);
  need(taxonomy.some(t=>t.id===p.category&&t.family===p.family),'Unknown category/family');
  need(p.implementationStatus==='fixture_only','PR cannot activate a product');
  need(p.pricingModel==={insurance:'insurance_premium',credit:'credit_terms',retirement:'retirement_terms'}[p.family],'Wrong pricing model');
  need(p.inputSchema===`schemas/contract.schema.json#/$defs/${p.family}Input`,'Unknown core schema');
  need(Array.isArray(p.markets)&&p.markets.length>0,'Markets required');p.markets.forEach(x=>need(currencies[x.country]===x.currency&&!!x.currency,'Unsupported market'));
  text(p.name,'product name');text(p.contractingEntity?.legalName,'contracting entity');text(p.contractingEntity?.role,'contracting role');httpsURL(p.contractingEntity.registerUrl);
  need(/^input-schemas\/[a-z0-9-]+\.schema\.json$/.test(p.providerDataSchema),'Invalid local schema path');
  const s=providerSchemas?.[p.providerDataSchema];need(s&&s.type==='object'&&s.additionalProperties===false&&Array.isArray(s.required),'Strict product-specific input schema required');
  // Schemas are reviewed artifacts, never downloaded from contributor URLs at runtime.
  const isolated=new Ajv2020({strict:true,allErrors:true});addFormats(isolated);validators.set(p.id,isolated.compile(s));
 }
 compiled.set(m,validators);return m;
}
export function validateRequest(r,m){
 valid(requestSchema,r);need(r.providerId===m.id,'Wrong provider');need(currencies[r.country]===r.currency,'Wrong market currency');
 const p=m.products.find(p=>p.id===r.productId);need(p,'Unsupported product');need(p.markets.some(x=>x.country===r.country&&x.currency===r.currency),'Product unavailable in market');need(r.input.family===p.family,'Wrong input family');
 const validator=compiled.get(m)?.get(p.id);need(validator,'Validate manifest and load provider schema first');valid(validator,r.input.providerData);
 if(p.family==='insurance'){
  need(r.input.risk.kind===p.riskKind,'Wrong insurance risk object');
  const risk=r.input.risk;
  if(risk.kind==='travel')need(risk.departure<=risk.return,'Return before departure');
  if(risk.kind==='vehicle')risk.drivers.forEach(d=>need(d.licenceYears<=d.ageYears-16,'Impossible licence history'));
 }else if(p.family==='credit'){
  need(cents(r.input.amount)>0,'Credit amount must be positive');
  if(r.input.facilityType==='installment')need(Number.isInteger(r.input.termMonths)&&r.input.repaymentModel!=='revolving','Installment term/model required');
  else need(r.input.repaymentModel==='revolving'&&r.input.assumedDrawnBalance!==undefined,'Revolving assumptions required');
 }else{
  need(Number.isInteger(r.applicant.ageYears)&&r.input.retirementAgeYears>=r.applicant.ageYears,'Invalid retirement age');
 }
 return p;
}
export function validateResponse(response,request,m,{now=Date.now(),mode='live'}={}){
 const p=validateRequest(request,m);valid(responseSchema,response);
 need(Number.isFinite(now)&&['live','sandbox'].includes(mode),'Invalid validation context');
 need(response.providerId===m.id&&response.requestId===request.requestId,'Response identity mismatch');need(response.mode===mode,'Sandbox/live mode mismatch');
 if(response.status!=='quoted'){need(response.quotes.length===0,'Error response contains quotes');text(response.message,'error message');return response;}
 need(response.quotes.length>0,'Quoted result must contain quotes');const seen=new Set();
 for(const q of response.quotes){
  need(!seen.has(q.quoteId),'Duplicate quote');seen.add(q.quoteId);
  need(q.productId===p.id&&q.country===request.country&&q.currency===request.currency,'Quote product/market mismatch');
  need(Date.parse(q.issuedAt)<=now&&now<Date.parse(q.expiresAt),'Future or expired quote');httpsURL(q.quoteUrl,m.quoteHosts);httpsURL(q.termsUrl,m.quoteHosts);
  for(const family of ['insurance','credit','retirement'])need((q[family]!==undefined)===(p.family===family),'Wrong/mixed output family');
  if(p.family==='insurance'){
   const v=q.insurance,pr=v.premium;need(cents(pr.total)>0,'Premium must be positive');need(cents(pr.base)+cents(pr.taxes)+cents(pr.mandatoryFees)===cents(pr.total),'Premium components do not total');
   need(pr.period===request.input.paymentPeriod&&v.startDate===request.input.startDate,'Policy input mismatch');need(v.endDate>=v.startDate,'Invalid coverage dates');
   const requested=request.input.requestedCoverages;need(v.coverages.length===requested.length,'Coverage count mismatch');
   for(const c of requested)need(v.coverages.some(x=>JSON.stringify(x)===JSON.stringify(c)),'Coverage differs from requested terms; counteroffers require a reviewed extension');
  }else if(p.family==='credit'){
   const v=q.credit;need(v.amount===request.input.amount&&v.facilityType===request.input.facilityType&&v.repaymentModel===request.input.repaymentModel,'Credit input mismatch');
   if(v.apr===null)text(v.aprUnavailableReason,'APR absence reason');
   if(v.facilityType==='installment'){
    need(v.termMonths===request.input.termMonths&&v.repaymentSchedule?.length===v.termMonths,'Complete repayment schedule required');
    let balance=cents(v.amount),paid=0,interest=0,previousDate='';
    for(const [i,s] of v.repaymentSchedule.entries()){
     need(s.number===i+1&&s.date>previousDate,'Invalid payment order');previousDate=s.date;
     need(cents(s.payment)===cents(s.principal)+cents(s.interest)+cents(s.fees),'Payment components mismatch');balance-=cents(s.principal);need(balance>=0&&balance===cents(s.balance),'Balance mismatch');paid+=cents(s.payment);interest+=cents(s.interest);
    }
    need(paid===cents(v.totalPayable)&&interest===cents(v.totalInterest)&&balance===cents(v.finalBalance),'Credit totals mismatch');
    if(v.repaymentModel==='fully_amortizing'||v.repaymentModel==='bnpl')need(balance===0,'Amortizing credit has residual balance');
   }else need(v.minimumPayment&&v.illustration,'Revolving credit requires minimum-payment rules and an illustration');
  }else{
   const v=q.retirement;need(v.initialCapital===request.input.initialCapital&&JSON.stringify(v.contribution)===JSON.stringify(request.input.contribution),'Retirement contribution mismatch');
   for(const s of v.projections)need(Number(s.assumedNetAnnualReturnPercent)>-100,'Return must exceed total loss');
  }
 }
 return response;
}
