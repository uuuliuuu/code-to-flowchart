"""Tool/export invariants. These tests never import or execute examples/source."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('render',ROOT/'scripts/render.py')
renderer=importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)

class ModelData(HTMLParser):
    def __init__(self): super().__init__(); self.active=False; self.text=''
    def handle_starttag(self,tag,attrs):
        if tag=='script' and dict(attrs).get('id')=='graph-model':self.active=True
    def handle_endtag(self,tag):
        if tag=='script':self.active=False
    def handle_data(self,data):
        if self.active:self.text+=data

class ExportTests(unittest.TestCase):
    def load(self,name='decision'):return json.loads((ROOT/'examples'/f'{name}.json').read_text())
    def test_examples_native_objects_and_cross_format_identity(self):
        for name in ('decision','retry','cross-file'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as td:
                m=self.load(name);renderer.render(m,td);out=Path(td)
                page=(out/'index.html').read_text();parser=ModelData();parser.feed(page)
                self.assertEqual(json.loads(parser.text),m)
                svgs=[ET.fromstring('<svg'+part.split('</svg>')[0]+'</svg>') for part in page.split('<svg')[1:]]
                diagrams=ET.parse(out/'diagram.drawio').getroot().findall('diagram')
                self.assertEqual(len(diagrams),len(m['diagrams']))
                marker_ids=[next(t for t in v.iter() if t.tag.endswith('marker')).get('id') for v in svgs]
                self.assertEqual(len(marker_ids),len(set(marker_ids)))
                for d,xml,svg in zip(m['diagrams'],diagrams,svgs):
                    marker=next(t for t in svg.iter() if t.tag.endswith('marker')).get('id')
                    for line in svg.iter():
                        if line.get('data-edge') is not None:self.assertEqual(line.get('marker-end'),'url(#'+marker+')')
                    cells=xml.find('mxGraphModel/root');objects=cells.findall('object');edges=[c for c in cells.findall('mxCell') if c.get('edge')=='1']
                    self.assertEqual({o.get('id'):o.get('label') for o in objects},{'n:'+n['id']:n['label'] for n in d['nodes']})
                    self.assertEqual({e.get('id'):e.get('value') for e in edges},{'e:'+e['id']:e.get('label','') for e in d['edges']})
                    ids={o.get('id') for o in objects}
                    for e in edges:
                        self.assertIn(e.get('source'),ids);self.assertIn(e.get('target'),ids)
                        self.assertNotIn('image',e.get('style'))
                    for o,n in zip(objects,d['nodes']):
                        self.assertEqual(o.find('mxCell').get('vertex'),'1')
                        if n.get('detail'):self.assertEqual(o.get('link'),'data:page/id,'+n['detail'])
                    texts={t.get('data-edge-label'):''.join(t.itertext()) for t in svg.iter() if t.get('data-edge-label') is not None}
                    self.assertEqual(texts,{e['id']:e.get('label','').replace('\n','') for e in d['edges']})
                    nodes={g.get('data-node'):''.join(g.itertext()) for g in svg.iter() if g.get('data-node') is not None}
                    self.assertEqual(nodes,{n['id']:n['label'].replace('\n','') for n in d['nodes']})
    def test_source_spans_exist_without_execution(self):
        for name in ('decision','retry','cross-file'):
            for d in self.load(name)['diagrams']:
                for n in d['nodes']:
                    for s in n['source']:
                        self.assertLessEqual(s['end'],len((ROOT/s['file']).read_text().splitlines()))
    def test_deterministic(self):
        with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
            renderer.render(self.load('retry'),a);renderer.render(self.load('retry'),b)
            for f in ('index.html','diagram.drawio','model.json'):self.assertEqual((Path(a)/f).read_bytes(),(Path(b)/f).read_bytes())
    def test_escape_and_long_unicode(self):
        m=self.load();payload='</script><script>alert("x")</script>& 中文 <tag> '\
          + 'a very long condition '*12
        m['title']=payload;m['diagrams'][0]['nodes'][0]['label']=payload;m['diagrams'][0]['edges'][0]['label']=payload
        with tempfile.TemporaryDirectory() as td:
            renderer.render(m,td);p=(Path(td)/'index.html').read_text()
            self.assertNotIn('<script>alert',p);self.assertIn('\\u003c/script',p)
            ET.parse(Path(td)/'diagram.drawio');q=ModelData();q.feed(p);self.assertEqual(json.loads(q.text),m)
            _,edges,_,_=renderer.layout(m['diagrams'][0]);self.assertGreater(len(edges[0]['lines']),10)
    def test_bad_references_and_coverage(self):
        for change in (lambda m:m.pop('coverage'),lambda m:m['diagrams'][0]['edges'][0].update(target='missing'),lambda m:m['diagrams'][0]['nodes'][0].update(detail='absent'),lambda m:m['diagrams'][0]['nodes'][0]['source'][0].update(file='/private/path'),lambda m:m['diagrams'][0].update(groups=[{'label':'bad','nodes':['missing']}])):
            m=self.load();change(m)
            with self.assertRaises(ValueError):renderer.validate(m)
    def test_back_edge_requires_side_route(self):
        m=self.load();m['diagrams'][0]['edges'].append({'id':'back','source':'eight','target':'entry'})
        with self.assertRaisesRegex(ValueError,'back edges'):renderer.layout(m['diagrams'][0])
    def test_decision_needs_labeled_exits(self):
        m=self.load();m['diagrams'][0]['edges'][1]['label']=''
        with self.assertRaisesRegex(ValueError,'labeled branches'):renderer.validate(m)

if __name__=='__main__':unittest.main()
