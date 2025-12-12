import { parsePatch, applyPatch } from 'diff';
const fs = require('fs');
const path = require('path');

export function applyUnifiedDiff(
  diff: string,
  fileContent: string
): string {
  const parsedDiff = parsePatch(diff);
  let str = fileContent;

  for (const patch of parsedDiff) {
    const result = applyPatch(fileContent, patch);
    if (result === false) {
      // console.log('could NOT apply a patch', patch), patch.hunks;
      throw new Error('Failed to apply patch');
    }
    str = result;
  }
  return str;
}

// load all .java .diff pairs from unittest/

const testDir = path.join(__dirname, 'unittest');
const files = fs.readdirSync(testDir);

for (const file of files) {
  if (file.endsWith('.java')) {
    const diffFile = file.replace('.java', '') + '.diff';
    const diffPath = path.join(testDir, diffFile);
    const javaPath = path.join(testDir, file);

    let diff = fs.readFileSync(diffPath, 'utf8');
    const java = fs.readFileSync(javaPath, 'utf8');

    diff = diff.replace(
      /Path:(.*)/g,
      (match: any, group: string) => `--- ${group}
+++ ${group}`
    );

    let diff_buffer: string[] = [];

    for (let line in diff.split('\n')) {
      if (line.startsWith('@@')) {
        // diff = diff.replace(line, '+++ ' + javaPath);
        let matches = line.match(/@@/);
        if (matches && matches.length < 2) {
          diff_buffer.push('@@ @@');
          diff_buffer.push(line.replace('@@', ''));
          continue;
        }
      }
      diff_buffer.push(line);
    }

    console.log('diff', diff);

    try {
      const result = applyUnifiedDiff(diff, java);
      console.log('patched', javaPath);
      fs.writeFileSync(javaPath, result, 'utf8');
    } catch (e) {
      console.error('failed to patch', javaPath);
    }
  }
}
