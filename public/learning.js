(() => {
 const view = document.getElementById('learningView');
 const sections = {
  lessons: ['Lessons', 'Small steps. Strong foundations.', 'Learn the fundamentals step by step in eight programming languages.'],
  examples: ['Code examples', 'Read it. Change it. Try it.', 'Complete source code, program input, and expected output in one place.'],
  reference: ['Reference', 'Find the syntax you need.', 'Quick explanations of functions, methods, and operators.'],
  algorithms: ['Algorithms and data structures', 'Understand the logic behind the code.', 'From searching to graphs: steps, complexity, and Python examples.']
 };
 let data = null, progress = {}, activeSection = '', selectedLanguage = 'python', search = '', category = '';
 const node = (tag, className, text) => { const n = document.createElement(tag); if (className) n.className = className; if (text !== undefined) n.textContent = text; return n; };
 const button = (text, action, cls='learn-button') => { const b=node('button',cls,text); b.type='button'; b.onclick=action; return b; };
 const link = (text, hash, cls='learn-link') => { const a=node('a',cls,text); a.href='#'+hash; return a; };
 const route = () => location.hash.slice(1).split('/');
 const completed = id => progress[id] === true;
 function codeBlock(code, label='Source code') { const box=node('div','learn-code-box'); box.append(node('div','code-label',label)); const pre=node('pre','learn-code'); pre.textContent=code; box.append(pre); return box; }
 function openCode(item) { return button('Open in editor ↗', async () => { try { await window.campusEditor.openExample(item); } catch { window.alert('Could not open the editor. Reload the page and try again.'); } },'learn-button primary'); }
 function meta(item) { const bar=node('div','learn-meta'); if(item.language) bar.append(node('span','language-pill '+item.language, data.languages[item.language])); if(item.minutes) bar.append(node('span','',`${item.minutes} min`)); if(item.level) bar.append(node('span','',item.level)); return bar; }
 function showOutput(item) { const label='Expected output · provided example'; const output=node('div','expected-result'); output.append(node('h3','',label),codeBlock(item.output,'Output')); output.append(node('p','learn-muted','This is the expected output for the provided example. Running your current code requires the secure runner.')); return output; }
 function setSection(section) {
  document.getElementById('compilerView').hidden=section!=='compiler'; view.hidden=section==='compiler';
  document.querySelectorAll('[data-section]').forEach(a => { a.classList.toggle('active',a.dataset.section===section); if(a.dataset.section===section) a.setAttribute('aria-current','page'); else a.removeAttribute('aria-current'); });
 }
 function render() {
  const [section='compiler', id] = route();
  const current = sections[section] ? section : 'compiler'; setSection(current);
  if(current==='compiler') return;
  if(!data) { view.replaceChildren(node('p','learn-muted','Loading the learning centre…')); return; }
  if(activeSection!==current) { activeSection=current; search=''; category=''; if(current==='algorithms') selectedLanguage='all'; else if(selectedLanguage==='all' && current==='lessons') selectedLanguage='python'; }
  if(id && (current==='lessons'||current==='examples')) {
   const selected=data[current].find(item=>item.id===id);
   if(selected && selectedLanguage!=='all') selectedLanguage=selected.language;
  }
  view.replaceChildren();
  const heading=node('div','learn-heading'); heading.append(node('div','eyebrow','CAMPUS CODE / LEARNING CENTRE'),node('h1','',sections[current][1]),node('p','learn-muted',sections[current][2]));
  const stats=node('div','learn-stats'); for(const [count,label] of [[data.lessons.length,'lessons'],[data.examples.length,'examples'],[data.references.length,'references'],[data.algorithms.length,'algorithms']]) { const n=node('span'); n.append(node('strong','',count),document.createTextNode(' '+label)); stats.append(n); } heading.append(stats); view.append(heading);
  if(current==='lessons') renderLessons(id); else if(current==='examples') renderExamples(id); else if(current==='reference') renderReference(); else renderAlgorithms(id);
 }
 function filtered(items) { const term=search.toLocaleLowerCase(); return items.filter(item => (selectedLanguage==='all'||item.language===selectedLanguage) && (!category||item.category===category) && [item.title,item.summary,item.syntax,item.note,data.languages[item.language]||''].join(' ').toLocaleLowerCase().includes(term)); }
 function filters(items, withLanguage=true) {
  const row=node('div','learn-filters');
  if(withLanguage) {
   const label=node('label','filter-label','Programming language'); const select=node('select'); select.setAttribute('aria-label','Learning language');
   for(const [value,text] of [['all','All languages'],...Object.entries(data.languages)]) { const option=node('option','',text); option.value=value; select.append(option); }
   select.value=selectedLanguage; select.onchange=()=>{selectedLanguage=select.value; location.hash=activeSection; render();}; label.append(select); row.append(label);
  }
  const label=node('label','filter-label search-filter','Search'); const input=node('input'); input.type='search'; input.placeholder='Topic or function name…'; input.setAttribute('aria-label','Search learning materials'); input.value=search;
  input.oninput=()=>{ const pos=input.selectionStart; search=input.value; render(); const next=view.querySelector('input[type=search]'); next.focus(); try { next.setSelectionRange(pos,pos); } catch {} }; label.append(input); row.append(label);
  const categories=[...new Set(items.map(item=>item.category).filter(Boolean))];
  if(categories.length) { const label=node('label','filter-label','Topic'); const select=node('select'); select.setAttribute('aria-label','Topic category'); for(const value of ['',...categories]) { const option=node('option','',value||'All topics'); option.value=value; select.append(option); } select.value=category; select.onchange=()=>{category=select.value;location.hash=activeSection;render();}; label.append(select); row.append(label); }
  view.append(row);
 }
 function empty() { const box=node('div','learn-empty'); box.append(node('h2','','No results found'),node('p','learn-muted','Try another search term or language.'),button('Clear filters',()=>{search='';category='';selectedLanguage=activeSection==='algorithms'?'all':'python';render();})); return box; }
 function renderLessons(id) {
  filters(data.lessons); const items=filtered(data.lessons); const layout=node('div','lesson-layout'); const sidebar=node('aside','lesson-sidebar'); sidebar.setAttribute('aria-label','Lesson list');
  const total=data.lessons.filter(l=>selectedLanguage==='all'||l.language===selectedLanguage); const count=total.filter(l=>completed(l.id)).length;
  sidebar.append(node('h2','','Your learning path'),node('p','learn-muted',`${count} / ${total.length} lessons read`)); const bar=node('progress'); bar.max=total.length||1;bar.value=count;bar.setAttribute('aria-label','Lessons read');sidebar.append(bar);
  for(const item of items) { const a=link(`${completed(item.id)?'✓':String(item.order).padStart(2,'0')}  ${item.title}`,`lessons/${item.id}`,'lesson-item'+(id===item.id||(!id&&items[0]?.id===item.id)?' current':'')); a.append(node('small','',data.languages[item.language])); sidebar.append(a); }
  if(!items.length) sidebar.append(empty()); layout.append(sidebar);
  const item=id?data.lessons.find(l=>l.id===id):items[0];
  const article=node('article','learn-article'); article.setAttribute('aria-label','Lesson content');
  if(!item) { article.append(empty()); layout.append(article);view.append(layout);return; }
  article.append(meta(item),node('h2','article-title',item.title)); for(const text of item.paragraphs) article.append(node('p','article-paragraph',text)); article.append(node('aside','learn-note',item.note),codeBlock(item.code));
  const actions=node('div','article-actions');actions.append(openCode(item));article.append(actions,showOutput(item));
  const exercise=node('section','exercise-box');exercise.append(node('span','eyebrow','PRACTICE EXERCISE'),node('h3','','Now try it yourself'),node('p','',item.exercise));article.append(exercise);
  renderQuiz(article,item);
  const complete=button(completed(item.id)?'✓ Marked as read':'Mark as read',async()=>{
   complete.disabled=true;
   try { await window.workspaceReady; const value=!completed(item.id); await window.api(`/api/progress/${item.id}`,{method:'PUT',body:{completed:value}});progress[item.id]=value;render(); }
   catch(error) { complete.disabled=false; const message=node('p','learn-error',error.message); complete.after(message); }
  },'learn-button '+(completed(item.id)?'complete':'primary'));
  const footer=node('div','lesson-next');footer.append(complete);const course=data.lessons.filter(l=>l.language===item.language);const index=course.findIndex(l=>l.id===item.id);if(course[index+1]) footer.append(link('Next lesson →',`lessons/${course[index+1].id}`));article.append(footer,node('p','learn-muted','Reading marks help you track your own learning. They are not assessed grades or certificates.'));
  layout.append(article);view.append(layout);
 }
 function renderQuiz(article,item) {
  const box=node('section','quiz-box');box.append(node('span','eyebrow','CHECK YOUR UNDERSTANDING'),node('h3','',item.quiz.question));const feedback=node('p','quiz-feedback');feedback.setAttribute('aria-live','polite');
  item.quiz.choices.forEach((choice,index)=>{const b=button(choice,()=>{box.querySelectorAll('button').forEach(other=>other.setAttribute('aria-pressed','false'));b.setAttribute('aria-pressed','true');const correct=index===item.quiz.answer;feedback.textContent=correct?'Correct! '+item.quiz.explanation:'Not quite. Review the lesson example and try again.'; feedback.className='quiz-feedback '+(correct?'correct':'incorrect');},'quiz-choice');b.setAttribute('aria-pressed','false');box.append(b);});box.append(feedback);article.append(box);
 }
 function renderExamples(id) {
  filters(data.examples); const items=filtered(data.examples); const selected=data.examples.find(x=>x.id===id);
  if(selected) { const article=node('article','learn-article standalone');article.append(link('← Back to examples','examples'),meta(selected),node('h2','article-title',selected.title),node('p','article-paragraph',selected.summary),codeBlock(selected.code)); if(selected.stdin) article.append(codeBlock(selected.stdin,'Program input (stdin)'));article.append(openCode(selected),showOutput(selected));view.append(article);return; }
  view.append(node('p','result-count',`${items.length} examples`)); const grid=node('div','learn-grid');for(const item of items) {const card=node('article','learn-card');card.append(meta(item),node('h2','',item.title),node('p','learn-muted',item.summary),node('small','category-label',item.category),link('View code and output →',`examples/${item.id}`));grid.append(card);}view.append(items.length?grid:empty());
 }
 function renderReference() {
  filters(data.references);const items=filtered(data.references);view.append(node('p','result-count',`${items.length} entries`));const grid=node('div','reference-grid');for(const item of items) {const card=node('article','learn-card reference-card');card.append(meta(item),node('h2','',item.title),node('p','learn-muted',item.summary),codeBlock(item.syntax,'Syntax'),codeBlock(item.example,'Short example'),node('aside','learn-note',item.note));grid.append(card);}view.append(items.length?grid:empty());
 }
 function renderAlgorithms(id) {
  filters(data.algorithms,false);const item=data.algorithms.find(a=>a.id===id);
  if(item) {const article=node('article','learn-article standalone');article.append(link('← All algorithms','algorithms'),meta(item),node('h2','article-title',item.title),node('p','article-paragraph',item.summary));const complexities=node('div','complexity-row');complexities.append(node('span','',`Time: ${item.complexity}`),node('span','',`Space: ${item.space}`));article.append(complexities);const steps=node('ol','algorithm-steps');for(const step of item.steps)steps.append(node('li','',step));article.append(steps,node('aside','learn-note',item.note));if(['binary-search','bubble-sort'].includes(item.id)) renderTrace(article,item.id);article.append(codeBlock(item.code),openCode(item),showOutput(item));view.append(article);return;}
  const items=filtered(data.algorithms);const grid=node('div','learn-grid');for(const item of items){const card=node('article','learn-card');card.append(node('small','category-label',item.category),node('h2','',item.title),node('p','learn-muted',item.summary),node('div','complexity-row',`Time: ${item.complexity}`),link('Explore the steps →',`algorithms/${item.id}`));grid.append(card);}view.append(items.length?grid:empty());
 }
 function renderTrace(article,id) {
  const frames=[];
  if(id==='binary-search') {const values=[1,3,5,7,9];let left=0,right=4;while(left<=right){const mid=Math.floor((left+right)/2);frames.push({values:[...values],active:[mid],note:`Left: ${left}, right: ${right}, middle: ${mid}. ${values[mid]===7?'Found 7!':`${values[mid]} < 7, move the left boundary to ${mid+1}.`}`});if(values[mid]===7)break;left=mid+1;}}
  else {const values=[5,2,4,1];frames.push({values:[...values],active:[],note:'Start with the initial array. Compare neighboring elements.'});for(let end=values.length-1;end>0;end--){let changed=false;for(let i=0;i<end;i++){const swap=values[i]>values[i+1];const before=[values[i],values[i+1]];if(swap){[values[i],values[i+1]]=[values[i+1],values[i]];changed=true;}frames.push({values:[...values],active:[i,i+1],note:`${before[0]} and ${before[1]}: ${swap?'values swapped.':'already in order; no swap needed.'}`});}if(!changed)break;}frames.push({values:[...values],active:[],note:'Sorting complete: [1, 2, 4, 5].'});}
  const box=node('section','trace-box');box.append(node('h3','','Step-by-step walkthrough'),node('p','learn-muted','This walkthrough illustrates a fixed example; it does not execute code from the editor.'));const values=node('div','trace-values');const note=node('p','trace-note');note.setAttribute('aria-live','polite');const controls=node('div','trace-controls');let index=0;const back=button('← Previous',()=>{index--;paint();});const next=button('Next →',()=>{index++;paint();});const reset=button('Restart',()=>{index=0;paint();});const count=node('span','learn-muted');controls.append(back,count,next,reset);box.append(values,note,controls);article.append(box);
  function paint(){const frame=frames[index];values.replaceChildren();frame.values.forEach((value,i)=>{const cell=node('div','trace-cell'+(frame.active.includes(i)?' highlighted':''));cell.append(node('small','',i),node('strong','',value));values.append(cell);});note.textContent=frame.note;count.textContent=`${index+1} / ${frames.length}`;back.disabled=index===0;next.disabled=index===frames.length-1;}paint();
 }
 window.addEventListener('hashchange',()=>{render(); window.scrollTo({top:0,behavior:'instant'});});
 window.workspaceReady.then(async()=>{try{progress=(await window.api('/api/progress')).progress;render();}catch{render();view.prepend(node('p','learn-error','Could not load your reading progress. Reload the page and try again.'));}});
 fetch('/learning-data.json').then(response=>{if(!response.ok)throw Error();return response.json();}).then(content=>{data=content;render();}).catch(()=>{setSection('lessons');view.replaceChildren(node('p','learn-error','Could not load the learning materials. Please reload the page.'));});
 render();
})();
