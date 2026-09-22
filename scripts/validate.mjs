import {readdirSync,readFileSync,existsSync,lstatSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {join} from 'node:path';
import {validateManifest,validateResponse} from '../lib/contract.mjs';
const root=fileURLToPath(new URL('../',import.meta.url));
const read=p=>JSON.parse(readFileSync(p,'utf8'));
const taxonomy=read(join(root,'taxonomy.json'));
let count=0;
for(const base of ['examples','providers']) {
 const dir=join(root,base);if(!existsSync(dir))continue;
 for(const entry of readdirSync(dir,{withFileTypes:true})) {
  if(!entry.isDirectory())throw new Error('Only provider directories accepted');
  const folder=join(dir,entry.name); const manifestPath=join(folder,'provider.json');
  if(lstatSync(manifestPath).isSymbolicLink())throw new Error('Symlinks are not accepted');
  const raw=read(manifestPath),schemas={};
  for(const p of raw.products){if(!/^input-schemas\/[a-z0-9-]+\.schema\.json$/.test(p.providerDataSchema))throw new Error('Invalid schema path');const sp=join(folder,p.providerDataSchema);if(lstatSync(sp).isSymbolicLink())throw new Error('Symlink schema rejected');schemas[p.providerDataSchema]=read(sp);}
  const m=validateManifest(raw,taxonomy,schemas),seen=new Set(),statuses=new Set();
  if(base === 'providers' && (m.id !== entry.name || m.website.includes('.example')))throw new Error('Replace example identity in real submissions');
  for(const f of readdirSync(join(folder,'fixtures'))) {
   if(!f.endsWith('.json'))throw new Error('Only JSON fixtures accepted');
   const path=join(folder,'fixtures',f);if(lstatSync(path).isSymbolicLink())throw new Error('Symlinks not accepted');
   const {request,response}=read(path);
   // Fixed fixture clock is explicit; use actual current time for production validation.
   validateResponse(response,request,m,{now:Date.parse('2026-09-22T10:05:00Z'),mode:'sandbox'});
   if(response.status === 'quoted')seen.add(request.productId); statuses.add(response.status);count++;
  }
  for(const p of m.products)if(!seen.has(p.id))throw new Error(`Missing success fixture: ${p.id}`);
  for(const s of ['no_quote','unavailable'])if(!statuses.has(s))throw new Error(`Missing outcome: ${s}`);
 }
}
console.log(`PASS: ${count} offline fixtures; no live prices fetched or providers activated.`);
