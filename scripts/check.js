// Frontend tooling: syntax-checks the client script and confirms required files exist.
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const root = path.join(__dirname, "..");
const files = ["static/index.html", "static/css/style.css", "static/js/app.js"];

let ok = true;
for (const f of files) {
  if (fs.existsSync(path.join(root, f))) console.log("found  ", f);
  else { console.error("missing", f); ok = false; }
}
try {
  execFileSync(process.execPath, ["--check", path.join(root, "static/js/app.js")]);
  console.log("syntax  static/js/app.js OK");
} catch (e) {
  console.error(e.stderr ? e.stderr.toString() : e.message);
  ok = false;
}
process.exit(ok ? 0 : 1);
