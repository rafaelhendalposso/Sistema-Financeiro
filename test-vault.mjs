import test from 'node:test';
import assert from 'node:assert/strict';
import {blank} from './dist/core.mjs';
// Storage adapter double; encryption uses real Web Crypto. Browser UI is checked separately.
const rows=new Map();
globalThis.indexedDB={open(){const request={};queueMicrotask(()=>{request.result={createObjectStore(){},transaction(){const tx={objectStore(){return {get(id){const r={};queueMicrotask(()=>{r.result=structuredClone(rows.get(id));r.onsuccess()});return r},getAll(){const r={};queueMicrotask(()=>{r.result=structuredClone([...rows.values()]);r.onsuccess()});return r},put(record){rows.set(record.id,structuredClone(record));queueMicrotask(()=>tx.oncomplete())}}}};return tx}};request.onsuccess()});return request}};
const v=await import('./dist/vault.mjs');
test('encrypted user isolation, wrong password, backup restore and stale writes',async()=>{
 const a=await v.create('Synthetic A','only-a-test-123',blank());
 const b=await v.create('Synthetic B','only-b-test-123',blank());
 const data=structuredClone(a.data);data.accounts.push({id:'secret',name:'PRIVATE_ACCOUNT_TOKEN',kind:'checking',opening:10000,openingDate:'2026-01-01',color:'#147d64'});
 await v.save(a,data);
 assert.equal(JSON.stringify([...rows.values()]).includes('PRIVATE_ACCOUNT_TOKEN'),false);
 await assert.rejects(v.unlock(a.record.id,'wrong-password'));
 assert.equal((await v.unlock(b.record.id,'only-b-test-123')).data.accounts.length,0);
 assert.equal((await v.unlock(a.record.id,'only-a-test-123')).data.accounts[0].opening,10000);
 const exportText=v.backup(a);assert.equal(exportText.includes('PRIVATE_ACCOUNT_TOKEN'),false);
 assert.equal((await v.readBackup(exportText,'only-a-test-123')).accounts.length,1);
 await assert.rejects(v.readBackup(exportText,'only-b-test-123'));
 const stale=await v.unlock(a.record.id,'only-a-test-123');await v.save(a,data);
 await assert.rejects(v.save(stale,data),/outra aba/);
 const invalid=structuredClone(data);invalid.transactions=[{id:'x',accountId:'no-such-account'}];
 await assert.rejects(v.save(a,invalid));
 assert.equal((await v.unlock(a.record.id,'only-a-test-123')).data.transactions.length,0);
});

test('password rotation keeps the encrypted cofre intact',async()=>{
 const user=await v.create('Rotation','rotation-old-123',blank());
 const data=structuredClone(user.data);data.accounts.push({id:'rotation-account',name:'Conta preservada',kind:'checking',opening:4200,openingDate:'2026-01-01',color:'#147d64'});
 await v.save(user,data);
 const rotated=await v.changePassword(user,'rotation-old-123','rotation-new-456');
 await assert.rejects(v.unlock(user.record.id,'rotation-old-123'));
 const unlocked=await v.unlock(user.record.id,'rotation-new-456');
 assert.equal(unlocked.data.accounts[0].name,'Conta preservada');
 assert.equal(rotated.data.accounts[0].opening,4200);
});
