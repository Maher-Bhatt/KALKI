const fs = require('fs');
const jsdom = require('jsdom');
const { JSDOM } = jsdom;

const html = fs.readFileSync('c:/Jarvis/index.html', 'utf-8');
const dom = new JSDOM(html, { runScripts: "dangerously", url: "http://localhost:8888/" });

dom.window.requestAnimationFrame = function(cb) { }; // mock it

dom.window.onerror = function(message, source, lineno, colno, error) {
  console.log('JSDOM ERROR:', message, 'at line', lineno);
  process.exit(1);
};
dom.window.addEventListener('error', (event) => {
  console.log('JSDOM WINDOW ERROR:', event.message);
  process.exit(1);
});

console.log("JSDOM initialized.");
setTimeout(() => {
  try {
    console.log("Running resizeOrb...");
    dom.window.resizeOrb();
    console.log("Running drawOrb...");
    dom.window.drawOrb();
    console.log("drawOrb succeeded!");
  } catch(e) {
    console.log("CAUGHT EXCEPTION IN DRAWORB:", e);
  }
  process.exit(0);
}, 2000);
