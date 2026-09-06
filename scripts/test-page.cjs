const fs=require('node:fs'), vm=require('node:vm'), assert=require('node:assert/strict');
const html=fs.readFileSync('us-research-radar-3.html','utf8');
const source=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const data=JSON.parse(fs.readFileSync('data/research.json','utf8'));
async function run(){
  const nodes=new Map();
  const document={hidden:false,addEventListener(){},querySelector(selector){
    if(!nodes.has(selector))nodes.set(selector,{textContent:'',innerHTML:'',addEventListener(){}});
    return nodes.get(selector);
  }};
  const context=vm.createContext({document,window:{addEventListener(){}},Date,AbortController,setTimeout,clearTimeout,setInterval(){},fetch:async()=>({ok:true,json:async()=>data})});
  vm.runInContext(source,context);
  await new Promise(resolve=>setImmediate(resolve));
  assert.match(nodes.get('#syncStatus').textContent,/最近采集检查/);
  assert.ok(Number(nodes.get('#totalStat').textContent)>100);
  assert.ok(nodes.get('#groups').innerHTML.includes('2026-09-04'));
  assert.ok(!nodes.get('#groups').innerHTML.includes('2026-02-20'));
  vm.runInContext("state.q='___no_match___';render()",context);
  assert.match(nodes.get('#groups').innerHTML,/没有找到匹配内容/);
  vm.runInContext("state.q='';state.type='播客';render()",context);
  const before=nodes.get('#groups').innerHTML;
  context.fetch=async()=>{throw new Error('offline')};
  await vm.runInContext('syncData()',context);
  assert.match(nodes.get('#syncStatus').textContent,/同步失败/);
  assert.equal(nodes.get('#groups').innerHTML,before);
  assert.equal(nodes.get('#refreshData').disabled,false);
  context.fetch=async()=>({ok:true,json:async()=>({...data,reports:[{url:'javascript:alert(1)'}]})});
  await vm.runInContext('syncData()',context);
  assert.equal(nodes.get('#groups').innerHTML,before);
  console.log('PASS: live load, rolling window, search, filters, offline and invalid data fallback');
}
run().catch(error=>{console.error(error);process.exitCode=1});
