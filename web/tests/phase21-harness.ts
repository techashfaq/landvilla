/** Narrow hook/effect harness: executes the actual TSX in memory. Not a DOM/browser test. */
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import ts from 'typescript';
import * as React from 'react';
import { propertyQuery } from '../src/lib/property-query.ts';
const require=createRequire(import.meta.url);
export type Node = React.ReactElement<Record<string, unknown>>;
export function loadComponent(file:string, name:string, mocks:Record<string,unknown>={}) {
  const source=readFileSync(new URL('../src/'+file,import.meta.url),'utf8');
  const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText;
  const exports:Record<string,unknown>={};
  const imports:Record<string,unknown>={ 'next/link':{__esModule:true,default:'a'},'@/lib/contracts':{isRecord:(v:unknown)=>!!v&&typeof v==='object'&&!Array.isArray(v)},'@/lib/property-contracts':{},'@/lib/property-query':{propertyQuery},'@/components/properties/property-card':{PropertyCard:()=>null},...mocks };
  new Function('require','exports',code)((id:string)=>id in imports?imports[id]:require(id),exports);
  return exports[name] as (props:Record<string,unknown>)=>Node;
}
export function nodes(tree:unknown):Node[] {
  if(Array.isArray(tree))return tree.flatMap(nodes);
  if(!React.isValidElement<Record<string,unknown>>(tree))return [];
  return [tree,...nodes(tree.props.children)];
}
export function text(tree:unknown):string {
  if(Array.isArray(tree))return tree.map(text).join('');
  if(React.isValidElement<Record<string,unknown>>(tree))return text(tree.props.children);
  return typeof tree==='string'||typeof tree==='number'?String(tree):'';
}
export function harness(file:string,name:string,context:()=>unknown) {
  const states:unknown[]=[];const refs:unknown[]=[];
  const effects:{deps:unknown[];cleanup?:()=>void}[]=[];
  let si=0,ri=0,ei=0,alive=true;let queued:(()=>void)[]=[];
  const hooks={
    useState:(initial:unknown)=>{const i=si++;if(!(i in states))states[i]=initial;return [states[i],(value:unknown)=>{if(alive)states[i]=typeof value==='function'?value(states[i]):value;}];},
    useRef:(initial:unknown)=>{const i=ri++;return refs[i]??(refs[i]={current:initial});},
    useEffect:(effect:()=>void|(()=>void),deps:unknown[])=>{const i=ei++;if(!effects[i]||deps.some((v,j)=>!Object.is(v,effects[i]!.deps[j])))queued.push(()=>{effects[i]?.cleanup?.();const cleanup=effect();effects[i]={deps,cleanup:typeof cleanup==='function'?cleanup:undefined};});}
  };
  const component=loadComponent(file,name,{react:hooks,'@/components/session-provider':{useSession:context}});
  return {render:(props:Record<string,unknown>)=>{si=ri=ei=0;return component(props);},flush:()=>{const jobs=queued;queued=[];jobs.forEach(job=>job());},unmount:()=>{alive=false;effects.forEach(e=>e.cleanup?.());}};
}
export function deferred<T>() {let resolve!:(value:T)=>void;let reject!:(error:Error)=>void;const promise=new Promise<T>((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};}
export const tick=()=>new Promise(resolve=>setImmediate(resolve));
