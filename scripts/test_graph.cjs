// Exercise the actual TypeScript graph builder without adding a test runtime.
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const assert = require('node:assert/strict')
const ts = require('typescript')
const source = fs.readFileSync(path.join(__dirname, '../src/lib/paperGraph.ts'), 'utf8')
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText
const exportsObject = {}
vm.runInNewContext(compiled, { exports: exportsObject })
const { buildPaperGraph, initialPositions } = exportsObject
const papers = [
  { id: 'a', title: 'A', tags: ['shared', 'shared', ''], venue: 'ICSE', year: 2025 },
  { id: 'b', title: 'B', tags: ['shared'], venue: 'ICSE', year: 2026 },
  { id: 'c', title: '', tags: [], venue: '', year: null },
]
const graph = buildPaperGraph(papers, ['tag', 'venue', 'year'])
assert.equal(graph.nodes.length, 7)
assert.equal(graph.edges.length, 6)
assert.equal(graph.nodes.find(n => n.id === 'tag:shared').degree, 2)
assert.equal(graph.nodes.find(n => n.id === 'venue:ICSE').degree, 2)
assert.equal(graph.nodes.find(n => n.id === 'paper:c').degree, 0)
assert.equal(buildPaperGraph(papers, []).edges.length, 0)
assert.equal(buildPaperGraph(papers, ['tag'], 1).omitted, 2)
assert.equal(buildPaperGraph([], ['tag']).nodes.length, 0)
const ids = new Set(graph.nodes.map(n => n.id))
assert.ok(graph.edges.every(e => ids.has(e.source) && ids.has(e.target)))
const positions = initialPositions(graph.nodes)
assert.ok(Object.values(positions).every(p => Number.isFinite(p.x) && Number.isFinite(p.y)))
console.log('Graph checks passed: shared relationships, deduplication, filters, limits, and layout seeds.')
