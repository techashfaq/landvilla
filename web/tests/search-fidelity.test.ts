import test from 'node:test';
import assert from 'node:assert/strict';
import {renderToStaticMarkup} from 'react-dom/server';
import {loadComponent,nodes} from './phase21-harness.ts';
import {propertyQuery} from '../src/lib/property-query.ts';
const SearchForm=loadComponent('components/properties/search-form.tsx','SearchForm');
const meta={localities:[{id:'loc_1',slug:'freeganj',name_en:'Freeganj'},{id:'loc_2',slug:'nagziri',name_en:'Nagziri'}],zones:[],categories:[],property_types:[]};
function form(query:string){return SearchForm({meta,query:new URLSearchParams(query)});}
function submit(query:string){const tree=form(query);assert.match(renderToStaticMarkup(tree),/<form/);const values=new URLSearchParams();for(const node of nodes(tree)){if(!['input','select'].includes(String(node.type))||!node.props.name)continue;const value=String(node.props.defaultValue??node.props.value??'');if(node.type==='select')assert.ok(nodes(node).some(option=>option.type==='option'&&option.props.value===value),'selected value exists');values.append(String(node.props.name),value);}return propertyQuery(values);}
for(const query of ['purpose=buy&q=home&min_price=100&max_price=1000&sort=price_asc&page=2&limit=5','locality=loc_1,loc_2','bhk=2,5,20,4%2B','locality=freeganj','locality=freeganj,loc_2&zone=unknown_zone&type=other_type&segment=other_segment',''])test('S17 form round trip '+(query||'empty'),()=>assert.equal(submit(query).toString(),propertyQuery(new URLSearchParams(query)).toString()));
test('S17 invalid and duplicate filters rejected before render',()=>{for(const q of ['city=ujjain','bhk=21','locality=a&locality=b','page=0','token=fixture'])assert.throws(()=>form(q));});
test('S17 clear filters targets clean discovery and empty form submits no filters',()=>{const reset=nodes(form('locality=freeganj&bhk=5&page=3')).find(n=>n.type==='a');assert.equal(reset?.props.href,'/properties');assert.equal(submit('').toString(),'');});
