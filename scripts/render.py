#!/usr/bin/env python3
"""Render an AI-authored, source-grounded graph model. Does not parse/run source."""
import argparse
import html
import json
import math
from pathlib import Path
import unicodedata
import xml.etree.ElementTree as ET

KINDS = {'start', 'end', 'process', 'decision', 'call', 'io', 'unknown', 'fork', 'join'}
COLORS = {'decision': '#fff2ca', 'unknown': '#fde5e5', 'call': '#e9e6ff', 'start': '#d9f3eb', 'end': '#d9f3eb', 'fork': '#dcecff', 'join': '#dcecff'}

def require(ok, message):
    if not ok:
        raise ValueError(message)

def validate(model):
    require(isinstance(model, dict) and model.get('version') == 1, 'version must be 1')
    require(isinstance(model.get('title'), str), 'title required')
    diagrams = model.get('diagrams', [])
    require(isinstance(diagrams, list) and bool(diagrams), 'at least one diagram required')
    require(isinstance(model.get('coverage'), dict) and all(k in model['coverage'] for k in ('read','unread','unknown','status')), 'coverage needs read/unread/unknown/status')
    require(all(isinstance(model['coverage'][k], list) for k in ('read','unread','unknown')) and isinstance(model['coverage']['status'], str), 'coverage lists/status have invalid types')
    ids = [d['id'] for d in diagrams]
    require(len(ids) == len(set(ids)), 'duplicate diagram id')
    for d in diagrams:
        require(isinstance(d['id'], str) and d['id'] and isinstance(d.get('title'), str), 'diagram id/title required')
        nodes = d.get('nodes', [])
        require(bool(nodes), 'diagram needs nodes')
        nids = [n['id'] for n in nodes]
        require(len(nids) == len(set(nids)), 'duplicate node id')
        positions = set()
        for n in nodes:
            require(isinstance(n['id'], str) and n['id'] and isinstance(n.get('label'), str), 'node id/label required')
            require(n.get('kind', 'process') in KINDS, 'unknown node kind')
            pos = (n.get('row'), n.get('col'))
            require(all(type(p) is int and p >= 0 for p in pos), 'row/col must be nonnegative integers')
            require(pos not in positions, 'nodes share row/col')
            positions.add(pos)
            require(n.get('detail') is None or n['detail'] in ids, 'missing detail diagram')
            require(bool(n.get('source')) or bool(n.get('synthetic')), 'node needs source or synthetic explanation')
            for s in n.get('source', []):
                require(isinstance(s.get('file'), str) and bool(s['file']) and '\\' not in s['file'] and not s['file'].startswith('/') and ':' not in s['file'] and '..' not in Path(s['file']).parts, 'source file must be portable relative path')
                require(type(s.get('start')) is int and type(s.get('end')) is int and 1 <= s['start'] <= s['end'], 'invalid source line range')
        for g in d.get('groups', []):
            require(isinstance(g.get('label'), str) and bool(g.get('nodes')) and all(n in nids for n in g['nodes']), 'invalid group')
        eids = set()
        for e in d.get('edges', []):
            require(e['source'] in nids and e['target'] in nids, 'dangling edge')
            require(isinstance(e['id'], str) and e['id'] and e['id'] not in eids, 'invalid or duplicate edge id')
            eids.add(e['id'])
            require(isinstance(e.get('label', ''), str), 'edge label must be text')
            require(e.get('route', 'direct') in {'direct', 'left', 'right'}, 'invalid route')
        for n in nodes:
            outgoing = [e for e in d.get('edges', []) if e['source'] == n['id']]
            if n.get('kind') == 'decision':
                require(len(outgoing) >= 2 and all(e.get('label') for e in outgoing), 'decision needs at least two labeled branches')
    return model

def text_units(char):
    # Conservative widths for system sans-serif; still verify the chosen font.
    if unicodedata.east_asian_width(char) in 'WF' or char in 'MWmw':
        return 2
    return 1.5 if char.isupper() or char in '@%#&' else 1

def wrap(text, limit=29):
    result = []
    for paragraph in text.split('\n'):
        line, width = '', 0
        for char in paragraph:
            step = text_units(char)
            if width + step > limit:
                result.append(line)
                line, width = '', 0
            line += char
            width += step
        result.append(line)
    return result

def layout(d):
    nodes = {}
    heights = {}
    for n in d['nodes']:
        lines = wrap(n['label'], 20 if n.get('kind') == 'decision' else 27)
        h = max(90, len(lines) * 19 + 40)
        if n.get('kind') == 'decision':
            h = max(140, len(lines) * 36 + 44)
        nodes[n['id']] = dict(n, lines=lines, w=300 if n.get('kind') == 'decision' else 270, h=h)
        heights[n['row']] = max(heights.get(n['row'], 0), h)
    gap = max([115] + [len(wrap(e.get('label',''), 26))*17+35 for e in d.get('edges',[])])
    lanes = {'left': 0, 'right': 0}
    for e in d.get('edges', []):
        if e.get('route') in lanes: lanes[e['route']] += 1
    left_margin = 230 + lanes['left']*32
    ys, cursor = {}, 80
    for row in sorted(heights):
        ys[row] = cursor
        cursor += heights[row] + gap
    for n in nodes.values():
        n['x'] = left_margin + n['col'] * 440 + (300 - n['w']) / 2
        n['y'] = ys[n['row']] + (heights[n['row']] - n['h']) / 2
    width = max(n['x'] + n['w'] for n in nodes.values()) + 230 + lanes['right']*32
    edges = []
    used = {'left': 0, 'right': 0}
    occupied_labels = []
    for i, edge in enumerate(d.get('edges', [])):
        a, b = nodes[edge['source']], nodes[edge['target']]
        ax, ay, bx, by = a['x'] + a['w']/2, a['y'] + a['h'], b['x'] + b['w']/2, b['y']
        route = edge.get('route', 'direct')
        if route in ('left', 'right'):
            left = route == 'left'
            ax = a['x'] if left else a['x'] + a['w']
            bx = b['x'] if left else b['x'] + b['w']
            ay, by = a['y'] + a['h']/2, b['y'] + b['h']/2
            channel = 35 + used[route]*32 if left else width - 35 - used[route]*32
            used[route] += 1
            points = [(ax, ay), (channel, ay), (channel, by), (bx, by)]
        elif a['row'] == b['row']:
            ax, bx = (a['x'] + a['w'], b['x']) if a['col'] < b['col'] else (a['x'], b['x'] + b['w'])
            ay, by = a['y'] + a['h']/2, b['y'] + b['h']/2
            points = [(ax, ay), (bx, by)]
        else:
            if b['row'] < a['row']:
                raise ValueError('back edges need explicit left/right route')
            middle = (ay + by)/2
            points = [(ax, ay), (ax, middle), (bx, middle), (bx, by)]
        lines = wrap(edge.get('label', ''), 26)
        mid_a, mid_b = points[(len(points)-1)//2], points[len(points)//2]
        lx, ly = (mid_a[0]+mid_b[0])/2, (mid_a[1]+mid_b[1])/2
        anchor = 'middle'
        if mid_a[0] == mid_b[0]:
            anchor = 'end' if route == 'right' else 'start'
            lx += -9 if anchor == 'end' else 9
        ly -= 9 + (len(lines)-1)*17/2
        def label_box(y):
            tw = max((sum(text_units(c) for c in line)*7.5 for line in lines), default=0)
            tx = lx if anchor == 'start' else lx-tw if anchor == 'end' else lx-tw/2
            return (tx-4, y-14, tx+tw+4, y+17*(len(lines)-1)+5)
        def intersects(a,b):
            return a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]
        if edge.get('label'):
            obstacles = occupied_labels + [(n['x'],n['y'],n['x']+n['w'],n['y']+n['h']) for n in nodes.values()]
            candidates = [mid_a[1]+(mid_b[1]-mid_a[1])*f-9-(len(lines)-1)*17/2 for f in (.5,.25,.75,.15,.85,.35,.65)] if route in ('left','right') else [ly, ly-35, ly+35, ly-55, ly+55]
            for candidate in candidates:
                box=label_box(candidate)
                if box[1]>=0 and box[3]<=cursor and not any(intersects(box,o) for o in obstacles):
                    ly=candidate
                    break
        if edge.get('label'): occupied_labels.append(label_box(ly))
        edges.append(dict(edge, points=points, lines=lines, lx=lx, ly=ly, anchor=anchor))
    return nodes, edges, width, cursor

def xml_text(el):
    return ET.tostring(el, encoding='unicode')

def svg(d, nodes, edges, width, height):
    esc = html.escape
    marker = 'arrow-' + d['id'].encode('utf-8').hex()
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{esc(d["title"], quote=True)}" viewBox="0 0 {width} {height}" width="{width}" height="{height}">', f'<defs><marker id="{marker}" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L9,3 z" fill="#53647b"/></marker></defs>']
    for group in d.get('groups', []):
        members = [nodes[n] for n in group['nodes']]
        x, y = min(n['x'] for n in members)-22, min(n['y'] for n in members)-42
        w, h = max(n['x']+n['w'] for n in members)-x+22, max(n['y']+n['h'] for n in members)-y+22
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="#f2f6fa" stroke="#ccd8e5"/><text x="{x+10}" y="{y+22}" font-size="13" fill="#52657d">{esc(group["label"])}</text>')
    for e in edges:
        p = e['points']
        out.append(f'<polyline data-edge="{esc(e["id"], quote=True)}" points="{" ".join(f"{x},{y}" for x,y in p)}" fill="none" stroke="#53647b" stroke-width="1.8" marker-end="url(#{marker})"/>')
        out.append(f'<text data-edge-label="{esc(e["id"], quote=True)}" text-anchor="{e["anchor"]}" font-size="13" paint-order="stroke" stroke="white" stroke-width="5" fill="#34445a">')
        for j, line in enumerate(e['lines']):
            out.append(f'<tspan x="{e["lx"]}" y="{e["ly"]+j*17}">{esc(line)}</tspan>')
        out.append('</text>')
    for n in nodes.values():
        x,y,w,h = n['x'],n['y'],n['w'],n['h']
        color = COLORS.get(n.get('kind'), '#ffffff')
        out.append(f'<g data-node="{esc(n["id"], quote=True)}">')
        if n.get('kind') == 'decision':
            out.append(f'<polygon points="{x+w/2},{y} {x+w},{y+h/2} {x+w/2},{y+h} {x},{y+h/2}" fill="{color}" stroke="#7b8ba2"/>')
        else:
            radius = 35 if n.get('kind') in ('start','end') else 8
            out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{color}" stroke="#7b8ba2"/>')
            if n.get('kind') == 'call':
                out.append(f'<path d="M{x+10},{y} V{y+h} M{x+w-10},{y} V{y+h}" stroke="#7b8ba2"/>')
        for j,line in enumerate(n['lines']):
            out.append(f'<text x="{x+w/2}" y="{y+h/2-(len(n["lines"])-1)*9.5+j*19+5}" text-anchor="middle" font-size="15">{esc(line)}</text>')
        out.append('</g>')
    out.append('</svg>')
    return ''.join(out)

def drawio(model, layouts):
    root = ET.Element('mxfile', host='code-to-flowchart', version='1.0')
    for d, (nodes, edges, width, height) in zip(model['diagrams'], layouts):
        diagram = ET.SubElement(root, 'diagram', id=d['id'], name=d['title'])
        graph = ET.SubElement(diagram, 'mxGraphModel', page='1', pageWidth=str(math.ceil(width)), pageHeight=str(math.ceil(height)))
        cells = ET.SubElement(graph, 'root')
        ET.SubElement(cells,'mxCell',id='0')
        ET.SubElement(cells,'mxCell',id='1',parent='0')
        for index, group in enumerate(d.get('groups', [])):
            members = [nodes[n] for n in group['nodes']]
            x, y = min(n['x'] for n in members)-22, min(n['y'] for n in members)-42
            w, h = max(n['x']+n['w'] for n in members)-x+22, max(n['y']+n['h'] for n in members)-y+22
            c=ET.SubElement(cells,'mxCell',id=f'g{index}',value=group['label'],style='rounded=1;fillColor=#f2f6fa;strokeColor=#ccd8e5;verticalAlign=top;align=left;spacing=10;html=0;',vertex='1',parent='1')
            ET.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'})
        for n in nodes.values():
            kind=n.get('kind','process')
            shape = 'rhombus' if kind=='decision' else 'rectangle'
            style=f'shape={shape};rounded=1;whiteSpace=wrap;html=0;fontSize=15;fillColor={COLORS.get(kind,"#ffffff")};strokeColor=#7b8ba2;'
            if kind=='call': style+='shape=process;'
            if kind in ('start','end'): style+='arcSize=50;'
            obj=ET.SubElement(cells,'object',id='n:'+n['id'],label=n['label'],source=json.dumps(n.get('source',[]),ensure_ascii=False))
            if n.get('detail'): obj.set('link','data:page/id,'+n['detail'])
            c=ET.SubElement(obj,'mxCell',style=style,vertex='1',parent='1')
            ET.SubElement(c,'mxGeometry',x=str(n['x']),y=str(n['y']),width=str(n['w']),height=str(n['h']),attrib={'as':'geometry'})
        for e in edges:
            a,b=nodes[e['source']],nodes[e['target']]
            p=e['points']
            ex,ey=(p[0][0]-a['x'])/a['w'],(p[0][1]-a['y'])/a['h']
            ix,iy=(p[-1][0]-b['x'])/b['w'],(p[-1][1]-b['y'])/b['h']
            style=f'edgeStyle=none;html=0;endArrow=block;exitX={ex};exitY={ey};entryX={ix};entryY={iy};exitPerimeter=0;entryPerimeter=0;fontSize=13;labelBackgroundColor=#ffffff;whiteSpace=wrap;labelWidth=190;'
            c=ET.SubElement(cells,'mxCell',id='e:'+e['id'],value=e.get('label',''),style=style,edge='1',parent='1',source='n:'+e['source'],target='n:'+e['target'])
            geo=ET.SubElement(c,'mxGeometry',x='0',y='0',relative='1',attrib={'as':'geometry'})
            lengths=[math.dist(u,v) for u,v in zip(p,p[1:])]
            remaining=sum(lengths)/2
            mx,my=p[0]
            for u,v,length in zip(p,p[1:],lengths):
                if remaining<=length and length:
                    t=remaining/length
                    mx,my=u[0]+(v[0]-u[0])*t,u[1]+(v[1]-u[1])*t
                    break
                remaining-=length
            tw=max((sum(text_units(c) for c in line)*7.5 for line in e['lines']), default=0)
            cx=e['lx'] + (tw/2 if e['anchor']=='start' else -tw/2 if e['anchor']=='end' else 0)
            cy=e['ly']+(len(e['lines'])-1)*17/2-4
            ET.SubElement(geo,'mxPoint',x=str(cx-mx),y=str(cy-my),attrib={'as':'offset'})
            arr=ET.SubElement(geo,'Array',attrib={'as':'points'})
            for x,y in p[1:-1]: ET.SubElement(arr,'mxPoint',x=str(x),y=str(y))
    return '<?xml version="1.0" encoding="UTF-8"?>\n'+xml_text(root)

def render(model, output):
    validate(model)
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    layouts=[layout(d) for d in model['diagrams']]
    esc=html.escape
    sections=[]
    options=[]
    for index,(d,lay) in enumerate(zip(model['diagrams'],layouts)):
        options.append(f'<option value="{index}">{esc(d["title"])}</option>')
        evidence=[]
        for n in d['nodes']:
            refs='; '.join(f'{s["file"]}:{s["start"]}–{s["end"]}' for s in n.get('source',[])) or n.get('synthetic','')
            link=''
            if n.get('detail'):
                target=next(i for i,g in enumerate(model['diagrams']) if g['id']==n['detail'])
                link=f' <button class="detail" data-target="{target}">Open detail ↗</button>'
            evidence.append(f'<li><strong>{esc(n["label"])}</strong>{link}<br><code>{esc(refs)}</code></li>')
        sections.append(f'<section data-diagram="{index}" {"hidden" if index else ""}><h2>{esc(d["title"])}</h2><p>{esc(d.get("notes",""))}</p><div class="viewport"><div class="canvas">{svg(d,*lay)}</div></div><details><summary>Source map · {len(d["nodes"])} nodes</summary><ul>{"".join(evidence)}</ul></details></section>')
    payload=json.dumps(model,ensure_ascii=False).replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>'''+esc(model['title'])+'''</title><style>
*{box-sizing:border-box}body{margin:0;background:#f7f9fc;color:#203048;font:15px system-ui,sans-serif}header,main{padding:24px 32px}header{background:#fff;border-bottom:1px solid #dce3eb;position:sticky;top:0;z-index:2}h1{font-size:24px;margin:0 0 16px}h2{font-size:19px}nav{display:flex;gap:10px;align-items:center;flex-wrap:wrap}button,select{font:inherit;padding:8px 12px;border:1px solid #aebdce;background:white;border-radius:6px;color:#203048}button{cursor:pointer}button:focus-visible,select:focus-visible{outline:3px solid #518adb}.viewport{overflow:auto;max-height:72vh;background:white;border:1px solid #dce3eb;border-radius:10px}.canvas{transform-origin:0 0}svg{display:block;font-family:system-ui,sans-serif}details{margin-top:16px}li{margin:12px 0}code{overflow-wrap:anywhere}p{max-width:1000px;line-height:1.6}footer{padding:20px 32px;color:#52657d}.detail{font-size:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere}
</style><header><h1>'''+esc(model['title'])+'''</h1><nav><label for="diagram">Diagram</label><select id="diagram">'''+''.join(options)+'''</select><button id="minus" aria-label="Zoom out">−</button><output id="zoom">100%</output><button id="plus" aria-label="Zoom in">+</button><button id="fit">Fit width</button><button id="reset">100%</button></nav></header><main>'''+''.join(sections)+'''<details><summary>Coverage and limits</summary><pre>'''+esc(json.dumps(model.get('coverage',{}),ensure_ascii=False,indent=2))+'''</pre></details></main><footer>Static source analysis · Editable companion: diagram.drawio · Source evidence is listed beneath each diagram.</footer><script type="application/json" id="graph-model">'''+payload+'''</script><script>
let scale=1;const sections=[...document.querySelectorAll('section')], select=document.querySelector('#diagram');
function zoom(value){scale=Math.max(.2,Math.min(2,value));document.querySelector('#zoom').textContent=Math.round(scale*100)+'%';for(const s of sections){const svg=s.querySelector('svg'),c=s.querySelector('.canvas');const vb=svg.viewBox.baseVal;svg.style.width=vb.width*scale+'px';svg.style.height=vb.height*scale+'px';c.style.width=vb.width*scale+'px';c.style.height=vb.height*scale+'px';}}
function show(index){select.value=String(index);sections.forEach((s,i)=>s.hidden=i!==Number(index));zoom(scale);}
select.addEventListener('change',()=>show(select.value));document.querySelectorAll('.detail').forEach(b=>b.addEventListener('click',()=>{show(b.dataset.target);window.scrollTo(0,0);}));document.querySelector('#plus').onclick=()=>zoom(scale+.1);document.querySelector('#minus').onclick=()=>zoom(scale-.1);document.querySelector('#reset').onclick=()=>zoom(1);document.querySelector('#fit').onclick=()=>{let s=sections[Number(select.value)];zoom((s.querySelector('.viewport').clientWidth-4)/s.querySelector('svg').viewBox.baseVal.width);};zoom(1);
</script></html>'''
    (output/'index.html').write_text(page,encoding='utf-8')
    (output/'diagram.drawio').write_text(drawio(model,layouts),encoding='utf-8')
    (output/'model.json').write_text(json.dumps(model,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return output

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model',type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    try:
        render(json.loads(args.model.read_text(encoding='utf-8')),args.out)
    except (ValueError,KeyError,TypeError) as exc:
        parser.exit(2,f'Invalid graph model: {exc}\n')
    print(f'Created {args.out}/index.html and diagram.drawio')
