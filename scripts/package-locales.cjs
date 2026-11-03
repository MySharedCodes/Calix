const fs=require('node:fs'),vm=require('node:vm'),ts=require('typescript');
const context={exports:{}};
vm.runInNewContext(ts.transpileModule(fs.readFileSync('frontend/src/locales.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,context);
fs.mkdirSync('release/components',{recursive:true});
fs.writeFileSync('release/components/languages.json',JSON.stringify(context.exports.extraTranslations));
