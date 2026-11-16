import test from 'node:test';
import assert from 'node:assert/strict';
import {benefitHelp,helpButton,helpContent} from '../src/benefit-help.mjs';
import fs from 'node:fs';
test('every benefit input has a unit, default example and explanation',()=>{
 for(const k of ['investment','annualOpex','days','years','discount','realization','cleanCost','energyValue']){
 const h=benefitHelp['input-'+k];assert.ok(h?.title);assert.ok(h.sections.length>=2);assert.ok(helpContent('input-'+k).includes('默认'));
 }
});
test('help triggers are keyboard-accessible buttons that cannot submit finance form',()=>{const b=helpButton('input-investment');assert.match(b,/type="button"/);assert.match(b,/aria-label="/);assert.match(b,/aria-haspopup="dialog"/);assert.match(b,/data-help="input-investment"/);assert.equal(helpButton('missing'), '');});
test('all benefit explanation targets resolve, including charts, targets and actions',()=>{
 for(const id of ['page','daily-saving','annual-cash','npv','threshold','daily-chart','cash-chart','sensitivity','cleaning','efficiency','advantages','cooperation','export-report','recalculate','model-details','value-uncertainty','value-soiling','value-edge','target-nmae','target-coverage','target-f1','target-profit','target-safety',...Array.from({length:6},(_,i)=>'stage-'+(i+1))])assert.ok(helpContent(id).length>100,id);
});
test('explanations preserve implemented accounting and scenario boundaries',()=>{assert.match(helpContent('threshold'),/70%/);assert.match(helpContent('sensitivity'),/固定/);assert.match(helpContent('efficiency'),/154/);assert.match(helpContent('export-report'),/JSON/);assert.match(helpContent('cleaning'),/1146/);});
