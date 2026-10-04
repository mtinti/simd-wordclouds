import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Workbook } from '@oai/artifact-tool';

const here = path.dirname(fileURLToPath(import.meta.url));
const rows = JSON.parse(await fs.readFile(path.join(here, 'corpus.json'), 'utf8'));
const headers = Object.keys(rows[0]);
const wb = Workbook.create();
for (const [name, filename, selected] of [
  ['All papers', 'simd_263_papers_year_pmid_abstract.csv', rows],
  ['Missing PDFs', 'simd_missing_fulltext_abstracts.csv', rows.filter(r => r.PDF_Status === 'missing')],
]) {
  const sheet = wb.worksheets.add(name);
  const matrix = [headers, ...selected.map(r => headers.map(k => r[k]))];
  const range = sheet.getRangeByIndexes(0, 0, matrix.length, headers.length);
  range.values = matrix;
  wb.recalculate();
  const actual = range.values;
  if (JSON.stringify(actual) !== JSON.stringify(matrix)) throw Error('Round-trip mismatch');
  // CSV has no styles or formula engine; export the checked literal cell values.
  const quote = s => '"' + String(s).replaceAll('"', '""') + '"';
  await fs.writeFile(path.join(here, '..', filename), actual.map(row => row.map(quote).join(',')).join('\n') + '\n');
  console.log(`${filename}: ${selected.length} records`);
}
